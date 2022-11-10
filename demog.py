# This file contains functions to gather demographic information on Patient and Clinicians
import re
import datetime


def get_date(date_of_birth=0):
    """Gathers a date (either birthdate or appt date).
        Checks for validity and returns dob in DD/MM/YYYY format
        Keyword Arguments:
            date_of_birth: determines if this is a date used for date of birth (1). Default 0."""
    while True:
        if date_of_birth:
            date = input("Date of Birth (DD/MM/YYYY): ")
        else:
            date = input("Date (DD/MM/YYYY): ")

        match = re.search(r'^([0-9]{1,2})\\/([0-9]{1,2})\\/([0-9]{4})$', date)

        if date == "q" or "":
            return 0

        else:
            try:
                date = datetime.date(match.group(3), match.group(2), match.group(1))
                return date

            except ValueError:
                print("Please enter a valid date of birth in the format DD/MM/YYYY")


def get_name():
    """Gathers name information. Returns first name, middle name, and last name"""
    while True:
        first_name = input("First Name: ").capitalize()

        if first_name == "q" or "":
            return 0

        elif first_name:
            break

        else:
            print("Please enter a first name.")

    while True:
        last_name = input("Last Name: ").capitalize()

        if last_name == "q" or "":
            return 0

        elif last_name:
            break

        else:
            print("Please enter a last name.")

    middle_name = input("Middle Name (Optional): ").capitalize()

    return first_name, middle_name, last_name


def get_sex():
    """Gathers sex information. Returns sex"""
    sex_options = ["male", "female", "not specified"]

    while True:
        sex = input("Sex: ").capitalize()

        if sex == "q" or "":
            return 0

        elif sex.lower() in sex_options:
            return sex

        else:
            print("Please enter a valid sex from the options below.")
            for i, k in enumerate(sex_options):
                print(f"{i}. {k}")

def get_address():
    """Uses Place Key api to ensure address is valid: https://www.placekey.io/blog/getting-started-with-placekey-io
        Returns address dictionary with keys for street, building/apt number, city, state, country, and post code."""
    # TODO: Implement Placekey API to validate address
    address = input("Address: ")

    if address == "q" or "":
        return 0

    else:
        return address


def get_time():
    """Gets, validates, and returns a time"""
    while True:
        time = input("Time (HHMM): ")
        match = re.search(r"^([0-1]?[0-9]|2[0-3]):?([0-5][0-9])$", time)

        if time == "q" or "":
            return 0

        else:
            try:
                time = datetime.time(match.group(1), match.group(2))
                return time

            except ValueError:
                print("Invalid Time. Please enter in the format HHMM")
