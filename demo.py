# This file contains functions to gather demographic information on patients and clinicians
import re
import datetime


def basic_demo():
    """This function will be re-used for both patients and clinician to gather basic demographic details.
        It will return a dictionary of demographic details to initialize patient/clinician objects"""

    demo = {"First Name": (get_name())[0],
            "Last Name": (get_name())[1],
            "Middle Name": (get_name())[2],
            "Date of Birth": get_dob(),
            "Sex": get_sex(),
            "Address": get_address()}

    return demo


def get_dob():
    """Gathers date of birth. Checks for validity and returns dob in DD/MM/YYYY format"""
    while True:
        dob = input("Date of Birth (DD/MM/YYYY): ")
        match = re.search(r'^([0-9]{1,2})\\/([0-9]{1,2})\\/([0-9]{4})$', dob)

        try:
            dob = datetime.date(match.group(3), match.group(2), match.group(1))
            break

        except ValueError:
            print("Please enter a valid date of birth in the format DD/MM/YYYY")

    return dob


def get_name():
    """Gathers name information. Returns first name, middle name, and last name"""
    while True:
        first_name = input("First Name: ").capitalize()

        if first_name:
            break

        else:
            print("Please enter a first name.")

    while True:
        last_name = input("Last Name: ").capitalize()

        if last_name:
            break

        else:
            print("Please enter a last name.")

    middle_name = input("Middle Name (Optional): ").capitalize()

    return first_name, middle_name, last_name


def get_sex():
    """Gathers sex information. Returns sex"""
    sex_options = ["male", "female", "any"]

    while True:
        pref_sex = input("Sex Preference: ").capitalize()

        if pref_sex.lower() in sex_options:
            return pref_sex


def get_address():
    """Uses Place Key api to ensure address is valid: https://www.placekey.io/blog/getting-started-with-placekey-io
        Returns address dictionary with keys for street, building/apt number, city, state, country, and post code."""
    # TODO: Implement Placekey API to validate address
    address = input("Address: ")
