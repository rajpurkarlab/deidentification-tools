from dataclasses import dataclass


@dataclass
class DicomFileInfo:
    """Class for keeping track of the basic information of a dicom file"""

    path: str
    patient_folder: str
    study_folder: str
    anon_dicom_id: str
    filename: str
