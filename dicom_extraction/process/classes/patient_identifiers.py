from dataclasses import dataclass


@dataclass
class PatientIdentifiers:
    """
    Note: The Dicom ID Heirarchy is:
    Patient ID
        - Study Instance UID
            - Series Instance UID
                - SOP Instance UI
    """

    PatientID: str
    PatientName: str
    StudyInstanceUID: str
    StudyID: str
    SOPInstanceUID: str
