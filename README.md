# Deidentification Tools
This repo provides or links to deidentification tools for DICOM images, free-form text reports and burned-in PHI in DICOM images.

## DICOM Metadata and Pixel Extraction
Our DICOM metadata tool was designed and tested to extract pixel data and non-identifiable metadata from single-frame x-rays, but it should work with other single-frame DICOM images too. The tool separately stores the pixel data of a DICOM into a PNG and the extracted non-identifiable metadata into a CSV file. The list of non-identifiable metadata is specified in `dicom_extraction/dicom_tags`. 

### How to use this tool
**Install required packages**

Go to `dicom_extraction` and pip install the required packages:
`pip install -r requirements.txt`

**Expected folder structure**

The tool expects a list of patient folders, and within each folder, there is a list of study folders where the DICOM images are placed directly. Here, the patient folder names can only be in the format of patient_k, where k is an integer from 1 to MAX_PATIENT_INDEX (default to 500 in `dicom_extraction/process/constants.py`). Similarly, the patient folder names can only be in the format of study_k, where k is an integer from 1 to MAX_STUDY_INDEX (default to 2 in `dicom_extraction/process/constants.py`). We want to reinforce this structure and naming because the folder names are used as the fake patient and study IDs in the output, and we want to make sure there is no identifiers in these folder names.

- patient_1
    - study_1/
        - dicom_1
        - dicom_2
        - ...
    - study_2/
        - dicom_1
        - ...

- patient_2

  ...


### Run test

```
python -m unittest dicom_extraction/test/test_main.py 
```


### Run script

```
python dicom_extraction/main.py --data_dir PATH_TO_DATA_SHARING_PACKAGE
```
You can try running this for an example:
```
python dicom_extraction/main.py --data_dir dicom_extraction/test/example_data_package
```
### Output

- deidentified_data/
    - metadata.csv
    - images/
        - {patient_id}-{study}-{filename_id}.png
        - ...

## Tags extracted
The dicom elements that are being extracted are in `dicom_extraction/dicom_tags`


## Other deidentification scripts for reference
- https://github.com/KitwareMedical/dicom-anonymizer/tree/master/dicomanonymizer
- https://github.com/16-Bit-Inc/dicom-anonymizer


## Notes
- If you get this error "ImportError: failed to find libmagic", try these following

        
        pip uninstall python-magic-bin
 
        pip install python-magic
        

        
    If the above doesn't work, try installing libmagic directly
    - Linux:
        ```
        sudo apt-get install libmagic1
        ```
    - Mac:
        ```
        brew install libmagic
        ```

## Medical Report Deidentification
Neamatullah et al. has developed a Perl-based de-identification software package that replaces PHI with realistic surrogate information for most free-text medical records. Here is their paper [Automated de-identification of free-text medical records](https://bmcmedinformdecismak.biomedcentral.com/articles/10.1186/1472-6947-8-32), and you can download the software package from [PhysioNet](https://physionet.org/content/deid/1.1/#files-panel).

## Deidentify DICOM images with burned-in PHI
Microsoft Presidio has developed a tool, Presidio Image Redactor, that redacts text PHI burned into DICOM medical images. This is their [documentation](https://microsoft.github.io/presidio/image-redactor/) and here is Microsoft Presidio's [github repo](https://github.com/microsoft/presidio). 
