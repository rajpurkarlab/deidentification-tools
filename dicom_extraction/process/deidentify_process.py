# Standard library
import glob
import logging
import os
from pathlib import Path
from typing import List
import magic
import re

# Third-party
import cv2
import pandas as pd
from tqdm import tqdm

# First-party/Local
from . import deidentify_helper
from .classes import DicomFileInfo
from .helpers import utils
from .helpers import (
    ConsoleColoredTag,
    ConsoleTextColor,
)
from .constants import (
    MAX_PATIENT_INDEX,
    MAX_STUDY_INDEX 
)

def deidentify_dicoms(input_data_dir: Path) -> None:
    output_image_dir = utils.get_output_image_directory(input_data_dir)

    # Create the image output folder
    os.makedirs(output_image_dir, exist_ok=True)
    
    # Create a CSV file to record all the extracted metadata from the dicom
    output_metadata_filename = utils.get_output_metadata_path(input_data_dir)
    generate_anonymized_metadata(input_data_dir, output_metadata_filename)

    # Convert DICOM files to PNG files
    generate_png(input_data_dir, output_image_dir)

    print("\n\n------------")
    print(ConsoleColoredTag.SUCCESS)
    print(f"{ConsoleColoredTag.INFO} Saved metadata to {output_metadata_filename}")
    print(f"{ConsoleColoredTag.INFO} Saved images to {output_image_dir}")
    print(
        f"{ConsoleTextColor.YELLOW}Remember to look over all images "
        + "and all CSVs manually to ensure that there is not personal "
        + f"health information (PHI) {ConsoleTextColor.END}"
    )


def generate_anonymized_metadata(input_data_dir: Path, output_metadata_filename: str) -> None:

    print(
        f"{ConsoleTextColor.PURPLE}"
        + "Start extracting anonymized metadata"
        + f"{ConsoleTextColor.END}"
    )

    dicom_files = get_list_of_all_dicom_files(input_data_dir)

    anon_metadata_all = []

    # Do not show progress bar when logging level is low
    tqdm_disabled = logging.getLogger().level < logging.WARNING
    for dicom_file in tqdm(dicom_files, disable=tqdm_disabled):
        anonymized_identifiers = deidentify_helper.get_anonymized_identifiers(
            dicom_file.patient_folder,
            dicom_file.study_folder,
            dicom_file.anon_dicom_id,
        )
        anon_metadata = deidentify_helper.extract_anonymized_metadata(
            dicom_file.path, anonymized_identifiers
        )

        anon_metadata["all"]["filename"] = utils.get_dicom_filename(dicom_file)
        anon_metadata_all.append(anon_metadata["all"])

    anon_metadata_df = pd.DataFrame.from_records(anon_metadata_all)
    anon_metadata_df.to_csv(output_metadata_filename, index=False)


def generate_png(input_data_dir: Path, new_image_dir: Path) -> None:

    print(
        f"{ConsoleTextColor.PURPLE}"
        + "Start converting DICOM to PNG"
        + f"{ConsoleTextColor.END}"
    )

    dicom_files = get_list_of_all_dicom_files(input_data_dir)

    # Do not show progress bar when logging level is low
    tqdm_disabled = logging.getLogger().level < logging.WARNING
    for dicom_file in tqdm(dicom_files, disable=tqdm_disabled):
        pixel_array = deidentify_helper.get_dicom_pixel(dicom_file.path)
        png_path = utils.get_png_path(new_image_dir, dicom_file)
        utils.save_png(pixel_array, png_path)


def generate_anonymized_dicom_from_dicom(
    input_data_dir: Path, new_image_dir: Path
) -> None:

    print(
        f"{ConsoleTextColor.PURPLE}"
        + "Start generating anonymized DICOM from DICOM"
        + f"{ConsoleTextColor.END}"
    )

    dicom_files = get_list_of_all_dicom_files(input_data_dir)

    # Do not show progress bar when logging level is low
    tqdm_disabled = logging.getLogger().level < logging.WARNING
    for dicom_file in tqdm(dicom_files, disable=tqdm_disabled):
        anonymized_identifiers = deidentify_helper.get_anonymized_identifiers(
            dicom_file.patient_folder,
            dicom_file.study_folder,
            dicom_file.anon_dicom_id,
        )
        anon_dicom = deidentify_helper.get_anonymized_dicom_from_dicom(
            dicom_file.path, anonymized_identifiers
        )

        dicom_path = utils.get_dicom_path(new_image_dir, dicom_file)
        utils.save_dicom(anon_dicom, dicom_path)


def generate_anonymized_dicom_from_metadata_png(
    metadata_path: Path, png_dir: Path
) -> None:

    print(
        f"{ConsoleTextColor.BLUE}"
        + "Start generating anonymized DICOM from metadata and png"
        + f"{ConsoleTextColor.END}"
    )

    generated_metadata_df = pd.read_csv(metadata_path)

    # Do not show progress bar when logging level is low
    tqdm_disabled = logging.getLogger().level < logging.WARNING
    for i in tqdm(range(len(generated_metadata_df)), disable=tqdm_disabled):
        meta_data = generated_metadata_df.iloc[i].dropna().to_dict()

        file_name = meta_data["filename"]

        generated_png_path = glob.glob(f"{png_dir}/*{file_name}.png")
        if len(generated_png_path) == 0:
            logging.warn(f"Corresponding PNG for {file_name} not found. Skip.")
            continue
        if len(generated_png_path) > 1:
            logging.warn(f"More than one PNG found for {file_name}. Skip.")
            continue
        png_path = generated_png_path[0]
        generated_png = cv2.imread(png_path, cv2.IMREAD_UNCHANGED)

        anon_dicom = deidentify_helper.get_anonymized_dicom_from_metadata_png(
            meta_data, generated_png
        )

        dicom_path = utils.get_dicom_path_from_png(png_path)
        utils.save_dicom(anon_dicom, dicom_path)


def get_list_of_all_dicom_files(data_dir: Path) -> List[DicomFileInfo]:
    """
    Args:
        data_dir: path to data directory with the following structure

                patient_1/[study_k]/[*.dcm]
                patient_2/[study_k]/[*.dcm]
                patient_3/[study_k]/[*.dcm]
                ....
    """
    all_dicom_files = []

    # Iterate patient folders
    patient_folders = os.listdir(data_dir)
    for patient_folder in patient_folders:
        patient_dir = Path(data_dir) / patient_folder
        if not patient_dir.is_dir():
            continue

        # check naming
        patient_folder_pattern = re.compile(r'^patient_[1-9][0-9]*$')
        if not patient_folder_pattern.match(patient_folder) \
            or (int(re.findall(r"\d+", patient_folder)[0]) > MAX_PATIENT_INDEX):
            logging.warning(
                f"SKIPPING unknown patient folder {patient_folder}"
            )
            continue
        
        # Iterate study folders within a patient folder
        study_folders = os.listdir(patient_dir)
        for study_folder in study_folders:
            study_dir = Path(data_dir) / patient_folder / study_folder
            if not study_dir.is_dir():
                continue

            # check naming
            study_folder_pattern = re.compile(r'^study_[1-9][0-9]*$') 
            if not study_folder_pattern.match(study_folder) \
                or (int(re.findall(r"\d+", study_folder)[0]) > MAX_STUDY_INDEX):
                logging.warning(
                    f"SKIPPING unknown study folder {study_folder}"
                )
                continue

            # Iterate dicom files within a study folder
            dicom_filenames = os.listdir(study_dir)
            for anon_dicom_id, dicom_filename in enumerate(dicom_filenames):
                dicom_path = (
                    Path(data_dir) / patient_folder / study_folder / dicom_filename
                )

                # Check the file type is DICOM
                # Please do not remove this file type check because pydicom doesn't
                # check file type before reading it as DICOM, which will likely throw an
                # error about empty pixel data
                file_type = magic.from_file(str(dicom_path))
                if ("DICOM" in file_type) is False:
                    logging.warning(
                        f"SKIPPING {dicom_filename} because it is a "
                        + f"{file_type} file"
                    )
                    continue

                dicom_file_info = DicomFileInfo(
                    path=dicom_path,
                    patient_folder=patient_folder,
                    study_folder=study_folder,
                    anon_dicom_id=anon_dicom_id,
                    filename=dicom_filename,
                )

                all_dicom_files.append(dicom_file_info)

    print(
        f"{ConsoleColoredTag.INFO} Number of dicom files found: "
        + f"{ConsoleTextColor.YELLOW}{len(all_dicom_files)}{ConsoleTextColor.END}"  # noqa: E501
    )

    return all_dicom_files
