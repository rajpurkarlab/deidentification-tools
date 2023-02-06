# Standard library
import ast
import logging
from typing import Tuple, Union

# Third-party
import numpy as np
import pandas as pd
import pydicom
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.dicomdir import DicomDir
from pydicom.uid import UID

# First-party/Local
from .helpers import dicom_helper
from .classes import PatientIdentifiers

MINIMAL_TAGS_CSV_PATH = "dicom_extraction/dicom_tags/minimal_tags.csv"
ADDITIONAL_TAGS_CSV_PATH = "dicom_extraction/dicom_tags/additional_tags.csv"
TAGS_TO_MODIFY_CSV_PATH = "dicom_extraction/dicom_tags/tags_to_modify.csv"
FILEMETA_KEYWORDS = [
    "FileMetaInformationGroupLength",
    "FileMetaInformationVersion",
    "TransferSyntaxUID",
]
MONOCHROME1 = "MONOCHROME1"


def get_dicom_pixel(dicom_path: str) -> np.ndarray:

    dicom = pydicom.dcmread(dicom_path)
    pixel_array = dicom.pixel_array

    # if the # bit/pixel is not a multiple of 8, we need to scale the pixel
    bits_stored = dicom["BitsStored"].value
    bits_allocated = dicom["BitsAllocated"].value
    if bits_stored != bits_allocated:
        pixel_array = pixel_array << (bits_allocated - bits_stored)

    # x-ray images are grayscale with two types of Photometric Interpretation
    # values MONOCHROME1 and MONOCHROME2, we invert the pixel values in
    # MONOCHROME1 when creating PNG, and will invert it back when recovering
    # the DICOM
    if dicom["PhotometricInterpretation"].value.upper() == MONOCHROME1:
        pixel_array = np.invert(pixel_array)

    return pixel_array


def extract_anonymized_metadata(
    dicom_path: str, anonymized_identifiers: PatientIdentifiers
) -> dict:

    # Read dicom file
    dicom = pydicom.dcmread(dicom_path)

    anon_metadata = {}

    # Step 1: Extract file header metadata (different from the main dicom tags)
    filemeta, is_implicit_VR, is_little_endian = extract_dicom_header_metadata(
        dicom
    )
    anon_metadata["header"] = {
        **filemeta,
        "is_implicit_VR": is_implicit_VR,
        "is_little_endian": is_little_endian,
    }

    # Step 2: Extract all relevant non-PHI dicom metadata

    # Minimal metedata required by a dicom file,
    # without which a dicom file can not be open
    anon_metadata["minimal"] = extract_metadata_from_dicom(
        dicom, MINIMAL_TAGS_CSV_PATH
    )

    # Non-PHI metadata beyond minimal metadata
    anon_metadata["additional"] = extract_metadata_from_dicom(
        dicom, ADDITIONAL_TAGS_CSV_PATH
    )

    # Note: extract metadata that needs modification
    anon_metadata["special"] = extract_special_metadata(
        dicom, TAGS_TO_MODIFY_CSV_PATH
    )

    # Step 3: Add dummy identifiers for things like StudyID, PatientName
    anon_metadata["minimal"].update(anonymized_identifiers.__dict__)

    anon_metadata["all"] = {
        **anon_metadata["minimal"],
        **anon_metadata["additional"],
        **anon_metadata["special"],
        **anon_metadata["header"],
    }

    return anon_metadata


def get_anonymized_dicom_from_dicom(
    dicom_path: str, anonymized_identifiers: PatientIdentifiers
) -> FileDataset:

    # Read dicom file
    dicom = pydicom.dcmread(dicom_path)

    # Step 1: Extract image
    pixel_data = dicom.PixelData

    # Step 2: Extract dicom header metadata
    filemeta, is_implicit_VR, is_little_endian = extract_dicom_header_metadata(
        dicom
    )

    # Step 3: Extract minimal metedata required by a dicom file,
    # without which the dicom file can not be open
    minimal_metadata = extract_metadata_from_dicom(
        dicom, MINIMAL_TAGS_CSV_PATH
    )
    minimal_metadata.update(anonymized_identifiers.__dict__)

    # Step 4: Generate dicom using minimal metadata
    anonymized_dicom = create_new_dicom(
        pixel_data=pixel_data,
        dicom_entries=minimal_metadata,
        file_meta=filemeta,
        is_implicit_VR=is_implicit_VR,
        is_little_endian=is_little_endian,
    )
    return anonymized_dicom


def get_anonymized_dicom_from_metadata_png(
    metadata: dict, pixel_array: np.ndarray
) -> FileDataset:

    # We shift and invert the pixel array for certain DICOMs when
    # generating the PNGs, so when we recover the DICOMs back, we
    # will need to undo the inverting and shifting
    if metadata["PhotometricInterpretation"] == MONOCHROME1:
        pixel_array = np.invert(pixel_array)

    bit_unshift = metadata["BitsAllocated"] - metadata["BitsStored"]
    pixel_array = pixel_array >> bit_unshift
    pixel_data = pixel_array.tobytes()

    is_implicit_VR = metadata["is_implicit_VR"]
    is_little_endian = metadata["is_little_endian"]

    minimal_metadata = extract_metadata_from_dict(
        metadata, MINIMAL_TAGS_CSV_PATH
    )

    anonymized_identifiers = PatientIdentifiers(
        PatientID=metadata["PatientID"],
        PatientName=metadata["PatientName"],
        StudyInstanceUID=metadata["StudyInstanceUID"],
        StudyID=metadata["StudyID"],
        SOPInstanceUID=metadata["SOPInstanceUID"],
    )
    minimal_metadata.update(anonymized_identifiers.__dict__)

    filemeta = dict(
        [(keyword, metadata[keyword]) for keyword in FILEMETA_KEYWORDS]
    )
    filemeta["FileMetaInformationVersion"] = ast.literal_eval(
        filemeta["FileMetaInformationVersion"]
    )

    anonymized_dicom = create_new_dicom(
        pixel_data=pixel_data,
        dicom_entries=minimal_metadata,
        file_meta=filemeta,
        is_implicit_VR=is_implicit_VR,
        is_little_endian=is_little_endian,
    )
    return anonymized_dicom


def create_new_dicom(
    pixel_data: bytes,
    dicom_entries: dict,
    file_meta: dict,
    is_implicit_VR: bool,
    is_little_endian: bool,
    preamble=None,
) -> FileDataset:

    # Step 1: Create filemeta and preamble
    if preamble is None:
        preamble = b"\0" * 128

    file_meta.update(create_basic_filemeta())
    final_file_meta = FileMetaDataset()
    for keyword, value in file_meta.items():
        final_file_meta.setdefault(keyword, value)

    # Step 2: Create dicom object
    ds = FileDataset(
        filename_or_obj=dicom_entries["StudyID"],
        dataset={},
        file_meta=final_file_meta,
        preamble=preamble,
        is_implicit_VR=is_implicit_VR,
        is_little_endian=is_little_endian,
    )

    # Step 3: Set all dicom metadata entries
    for keyword, value in dicom_entries.items():
        if keyword in [
            "PixelSpacing",
            "PixelAspectRatio",
            "ImagerPixelSpacing",
            "WindowCenter",
            "WindowWidth",
        ]:
            if type(value) == str:
                value = ast.literal_eval(value)
        if keyword in [
            "CollimatorRightVerticalEdge",
            "CollimatorUpperHorizontalEdge",
            "CollimatorLowerHorizontalEdge",
            "LargestImagePixelValue",
            "SmallestImagePixelValue",
        ]:
            value = int(value)
        if keyword in ["LossyImageCompression"]:
            value = str(value)
        ds.setdefault(keyword, value)

    # Step 4: Set the pixel data
    ds.PixelData = pixel_data

    return ds


def get_anonymized_identifiers(
    anon_patient_id: str, anon_study_id: str, anon_file_id: str
) -> PatientIdentifiers:
    """
    Create a series of patient identifiers with dummy values

    Note: The Dicom ID Heirarchy is:
    Patient ID
        - Study Instance UID
            - Series Instance UID
                - SOP Instance UI
    """
    anonymized_identifiers = PatientIdentifiers(
        PatientID=f"{anon_patient_id}",
        PatientName=f"{anon_patient_id}",
        StudyInstanceUID=f"{anon_patient_id}-{anon_study_id}",
        StudyID=f"{anon_patient_id}-{anon_study_id}",
        SOPInstanceUID=f"{anon_patient_id}-"
        + f"{anon_study_id}-"
        + f"{anon_file_id}",
    )

    return anonymized_identifiers


def extract_dicom_header_metadata(
    dicom: Union[FileDataset, DicomDir]
) -> Tuple[dict, bool, bool]:
    """
    Extracts the dicom file header metadata. This is different from the
    main dicom entries.

    We are excluding:
        'ImplementationVersionName', 'MediaStorageSOPClassUID', 'preamble'.
    """
    filemeta = {}
    for keyword in FILEMETA_KEYWORDS:
        filemeta[keyword] = dicom.file_meta[keyword].value

    return filemeta, dicom.is_implicit_VR, dicom.is_little_endian


def validate_keywords(keywords):
    invalid_keywords = []
    for keyword in keywords:
        tag = pydicom.datadict.tag_for_keyword(keyword)
        if pydicom.datadict.dictionary_has_tag(tag) is False:
            invalid_keywords.append(keyword)

    assert len(invalid_keywords) == 0, f"Invalid keywords {invalid_keywords}"


def extract_metadata_from_dicom(
    dicom: Union[FileDataset, DicomDir], tags_csv_path: str
) -> dict:
    """
    Extracts all dicom tags that are listed in a csv specified
    by the user
    """

    elements_to_extract = pd.read_csv(tags_csv_path)["Keyword"].tolist()
    validate_keywords(elements_to_extract)

    extracted_metadata = {}

    for keyword in elements_to_extract:
        if keyword == "PixelData":
            # Do not extract the actual image data
            continue

        # Check that the element to extract exists in the dicom
        if keyword in dicom.dir():
            current_value = dicom[keyword].value
            if type(current_value) == pydicom.multival.MultiValue:
                current_value = list(current_value)
            extracted_metadata[keyword] = current_value

    return extracted_metadata


def extract_metadata_from_dict(meta_data: dict, tags_csv_path: str) -> dict:

    elements_to_extract = pd.read_csv(tags_csv_path)["Keyword"].tolist()
    validate_keywords(elements_to_extract)

    extracted_metadata = {}

    for keyword in elements_to_extract:
        if keyword in meta_data:
            extracted_metadata[keyword] = meta_data[keyword]

    return extracted_metadata


def extract_special_metadata(
    dicom: Union[FileDataset, DicomDir], tags_csv_path: str
) -> dict:
    """Extract metadata that needs modification to not be PHI"""

    elements_to_modify = pd.read_csv(tags_csv_path)["Keyword"].tolist()
    validate_keywords(elements_to_modify)

    private_keywords_in_dicom = [
        "PatientAge",
        "PatientBirthDate",
        "StudyDate",
        "StudyTime",
    ]
    extracted_special_metadata = {}

    # Go through the list of valid DICOM keywords we want to modify
    for keyword in elements_to_modify:
        try:
            current_value = dicom[keyword].value
        except Exception:
            logging.info(
                f"This dicom does not contain keyword {keyword}. Skip."
            )
            continue

        if keyword in private_keywords_in_dicom:
            if keyword == "PatientAge":
                extracted_special_metadata[
                    "age"
                ] = dicom_helper.extract_modified_age(current_value)
            elif keyword == "StudyDate":
                extracted_special_metadata[
                    "day_of_week"
                ] = dicom_helper.extract_weekday_from_date(current_value)
                extracted_special_metadata[
                    "year"
                ] = dicom_helper.extract_year_from_date(current_value)
            elif keyword == "StudyTime":
                extracted_special_metadata[
                    "hour_of_the_day"
                ] = dicom_helper.extract_hour_of_day_from_time(current_value)

    return extracted_special_metadata


def create_basic_filemeta():
    filemeta = {
        "MediaStorageSOPClassUID": UID("1.2.3"),
        "MediaStorageSOPInstanceUID": UID("1.2.3"),
        "ImplementationClassUID": UID("1.2.3.4"),
    }
    return filemeta
