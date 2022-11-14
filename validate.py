# This file contains functions to gather demographic information on Patient and Clinicians
from datetime import datetime


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

        if date == "q" or not date:
            return 0

        else:
            try:
                date = datetime.strptime(date, "%d/%m/%Y").date()
                return date

            except ValueError:
                print("Please enter a valid date in the format DD/MM/YYYY.\n")


def get_name():
    """Gathers name information. Returns first name, middle name, and last name"""
    while True:
        first_name = input("First Name: ").lower()

        if first_name == "q" or not first_name:
            return 0

        elif first_name.isalpha():
            break

        else:
            print("Please enter a first name.")

    while True:
        last_name = input("Last Name: ").lower()

        if last_name == "q" or not last_name:
            return 0

        elif last_name.isalpha():
            break

        else:
            print("Please enter a last name.")

    while True:
        middle_name = input("Middle Name (Optional): ").lower()

        if not middle_name:
            break

        if middle_name.isalpha():
            break

        else:
            print("Please enter a valid middle name.")

    return first_name.capitalize(), middle_name.capitalize(), last_name.capitalize()


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

        if time == "q" or not time:
            return 0

        else:
            try:
                time = datetime.strptime(time, "%H%M").time()
                return time

            except ValueError:
                print("Invalid Time. Please enter in the format HHMM.\n")


def yes_or_no(prompt):
    """Validates a user's input as yes (return 1) or no (return 0)."""
    while True:
        confirm = input(prompt).lower()

        if confirm == "y" or "yes":
            return 1

        elif confirm == "n" or "no":
            return 0


def get_cat_value(cat_list, prompt):
    """
    Takes a category list and prompt as a parameter. Validates that the input from a user is in the category list.
    If is_class is set to True, the class list will be looped and converted to human-readable format.
    :return: The index value if the user selects a value in the category list, or 0 if the user quits"""

    # Display category values and prompt user for selection
    while True:
        print(prompt)
        for x, cat in enumerate(cat_list):
            print(f"    {x+1}. {cat.capitalize()}")

        selection = input(f"\nSelection: ").lower()

        if selection == "q" or not selection:
            return 0

        # Return corresponding index value if entered as alphanum
        if selection in cat_list:
            return selection

        # Return index value if entered as numeric and is an index in the category list
        elif selection.isnumeric() and int(selection)-1 in range(len(cat_list)):
            return cat_list[int(selection)-1]

        else:
            print("Invalid selection.")


def confirm_info(obj):
    """This function will be used to confirm information for any object that is created
     from a class instance."""

    print(f"A {type(obj).__name__} with the following details will be created: ")

    for k, v in vars(obj).items():
        print(f"{k}: {v}")

    if yes_or_no("Confirm the change to proceed (Y/N): "):
        return 1

