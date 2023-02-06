# Standard library
import glob
import os
import shutil
import unittest
from pathlib import Path

# Third-party
import cv2
import numpy as np
import pydicom

# First-party/Local
from ..process import deidentify_dicoms
from ..process import deidentify_process
from ..process.helpers import utils
from ..process.constants import GENERATED_DICOM_POSTFIX


TEST_DATA_PATH = "dicom_extraction/test/example_data_package"

class TestDicomDeidentification(unittest.TestCase):
    def setUp(self):
        self.test_data_path = Path(TEST_DATA_PATH)

    def test_deidentified_image_quality(self):
        # Clean up test output
        expected_output_path = utils.get_output_root_directory(
            self.test_data_path)
        if os.path.exists(expected_output_path):
            shutil.rmtree(expected_output_path)

        # De-identify DICOM
        deidentify_dicoms(self.test_data_path)

        # Check output has been generated
        self.assertTrue(os.path.exists(expected_output_path))

        expected_image_output_path = utils.get_output_image_directory(
            self.test_data_path
        )
        self.assertTrue(os.path.exists(expected_image_output_path))

        generated_metadata_path = utils.get_output_metadata_path(
            self.test_data_path
        )
        self.assertTrue(os.path.exists(generated_metadata_path))

        # Construct DICOM(s) from the generated PNGs and metadata
        deidentify_process.generate_anonymized_dicom_from_metadata_png(
            generated_metadata_path, expected_image_output_path
        )
        generated_dicoms = self.get_generated_dicoms(
            expected_image_output_path
        )

        # Get the original DICOM(s)
        input_path = self.test_data_path
        original_dicoms = self.get_original_dicoms(input_path)

        try:
            # Compare the pixels of the generated dicom and the original dicom
            assert np.all(
                [
                    np.all(
                        generated_dicoms[
                            utils.generate_png_name(study)
                        ].pixel_array
                        == original_dicoms[study].pixel_array
                    )
                    for study in original_dicoms.keys()
                ]
            )
        finally:
            shutil.rmtree(expected_output_path)

    def get_generated_dicoms(self, expected_image_output_path):
        generated_dicoms = {}
        generated_dicom_paths = glob.glob(
            f"{expected_image_output_path}/*.dcm"
        )
        for path in generated_dicom_paths:
            # Extract filename
            study = "-".join(path.split("-")[2:])
            study = study[: study.find(GENERATED_DICOM_POSTFIX)]
            generated_dicoms[study] = pydicom.dcmread(path)
        return generated_dicoms

    def get_generated_pngs(self, expected_image_output_path):
        generated_png_paths = glob.glob(f"{expected_image_output_path}/*.png")
        generated_pngs = {}
        for path in generated_png_paths:
            # Extract filename
            study = "-".join(path.split("-")[2:])
            study = study[: study.find(".png")]
            generated_pngs[study] = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        return generated_pngs

    def get_original_dicoms(self, input_path):
        original_dicom_paths = glob.glob(f"{input_path}/*/*/*.dcm")
        original_dicoms = {}
        for path in original_dicom_paths:
            study = path[: path.find(".dcm")]
            study = os.path.split(study)[1]
            original_dicoms[study] = pydicom.dcmread(path)
        return original_dicoms


if __name__ == "__main__":
    unittest.main()
