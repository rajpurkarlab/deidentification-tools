# Standard library
from pathlib import Path
import numpy as np
import hashlib

# Third-party
from PIL import Image
from pydicom.dataset import FileDataset

# First-party/Local
from ..constants import (
    GENERATED_DICOM_POSTFIX,
    NEW_DATA_DIR_NAME,
    NEW_IMAGE_DIR_NAME,
    OUTPUT_CSV_FILE_NAME,
)
from ..classes import DicomFileInfo


def get_output_root_directory(data_dir: Path):
    new_data_dir = data_dir.parent / f"{NEW_DATA_DIR_NAME}"
    return new_data_dir


def get_output_image_directory(data_dir):
    new_image_dir = get_output_root_directory(data_dir) / NEW_IMAGE_DIR_NAME
    return new_image_dir


def get_output_metadata_path(data_dir):
    metadata_filename = get_output_root_directory(data_dir) / OUTPUT_CSV_FILE_NAME
    return metadata_filename


def generate_png_name(filename: str) -> str:
    hash = hashlib.sha256(filename.encode("utf-8")).hexdigest()
    filename = f"generated_id_{hash[:8]}"
    return filename


def get_dicom_filename(dicom_file: DicomFileInfo) -> str:
    filename = dicom_file.filename
    filename = filename[: filename.find(".dcm")]
    filename = generate_png_name(filename)
    return filename


def get_png_path(new_image_dir: Path, dicom_file: DicomFileInfo) -> Path:
    filename = get_dicom_filename(dicom_file)
    patient_folder = dicom_file.patient_folder
    study_folder = dicom_file.study_folder

    png_filename = f"{patient_folder}-{study_folder}-{filename}.png"
    png_path = new_image_dir / png_filename

    return png_path


def get_dicom_path(new_image_dir: Path, dicom_file: DicomFileInfo) -> Path:
    filename = get_dicom_filename(dicom_file)
    patient_folder = dicom_file.patient_folder
    study_folder = dicom_file.study_folder

    dicom_filename = (
        f"{patient_folder}-{study_folder}-" + f"{filename}{GENERATED_DICOM_POSTFIX}"
    )
    dicom_path = new_image_dir / dicom_filename

    return dicom_path


def get_dicom_path_from_png(png_path: str) -> str:
    dicom_path = png_path.replace(".png", GENERATED_DICOM_POSTFIX)

    return dicom_path


def save_png(pixel_array: np.ndarray, save_path: Path) -> None:
    im = Image.fromarray(pixel_array)
    im.save(save_path, format="png")  # Do not use JPG!


def save_dicom(dicom_img: FileDataset, save_path: Path) -> None:
    dicom_img.save_as(save_path, write_like_original=False)


class ConsoleTextColor:
    PURPLE = "\033[1;35;48m"
    CYAN = "\033[1;36;48m"
    BOLD = "\033[1;37;48m"
    BLUE = "\033[1;34;48m"
    GREEN = "\033[1;32;48m"
    YELLOW = "\033[1;33;48m"
    RED = "\033[1;31;48m"
    BLACK = "\033[1;30;48m"
    UNDERLINE = "\033[4;37;48m"
    END = "\033[1;37;0m"


class ConsoleColoredTag:
    INFO = f"{ConsoleTextColor.CYAN}[INFO]{ConsoleTextColor.END}"
    SUCCESS = f"{ConsoleTextColor.GREEN}[SUCCESS]{ConsoleTextColor.END}"
