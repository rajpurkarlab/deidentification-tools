from datetime import datetime
import logging


def string_to_int(string):
    """Converts strings with leading zeros (e.g., '0053') to an int"""

    int_start_index = 0
    for i in range(len(string)):
        char_value = string[i]
        if char_value != "0" or i == len(string) - 1:
            int_start_index = i
            break

    try:
        extracted_int = int(string[int_start_index:])
    except Exception as e:
        logging.warning(e)
        extracted_int = None
    return extracted_int


def extract_modified_age(agestring):
    # Example 049Y
    try:
        unit = agestring[-1]  # e.g., Y
        extracted_int = string_to_int(agestring[:-1])
        modified_int = min(extracted_int, 90)
        modified_value = f"{modified_int}{unit}"
    except Exception as e:
        logging.warning(e)
        modified_value = None
    return modified_value


def extract_weekday_from_date(studydate_string):
    try:
        date_format = "%Y%m%d"
        study_date = datetime.strptime(studydate_string, date_format).date()
        modified_value = study_date.weekday()
    except Exception as e:
        logging.warning(e)
        modified_value = None
    return modified_value


def extract_year_from_date(studydate_string):
    try:
        date_format = "%Y%m%d"
        study_date = datetime.strptime(studydate_string, date_format).date()
        modified_value = study_date.year
    except Exception as e:
        logging.warning(e)
        modified_value = None
    return modified_value


def extract_hour_of_day_from_time(studytime_string):
    if type(studytime_string) == str and len(studytime_string) >= 2:
        try:
            hour = int(studytime_string[:2])
            modified_value = hour if hour in range(24) else None
        except Exception as e:
            logging.warning(e)
            modified_value = None
    else:
        modified_value = None
    return modified_value
