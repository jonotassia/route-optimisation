# This file contains functions to gather demographic information on Patient and Clinician
from datetime import datetime
from Levenshtein import ratio as levratio


def yes_or_no(prompt):
    """Validates a user's input as yes (return 1) or no (return 0)."""
    while True:
        confirm = input(prompt).lower()

        if confirm == "q" or not confirm:
            return 0

        elif confirm == ("n" or "no"):
            return 0

        elif confirm == ("y" or "yes"):
            return 1


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


def confirm_info(obj, detail_dict):
    """
    This function will be used to confirm information for any object that is created from a class instance.
    It loops through the passed dictionary to display relevant parameters.
    :param obj: Object - used to guide prompt.
    :param detail_dict: Includes the details which you would like to display to the user.
    :return: 1 if change is approved, else None
    """

    print(f"\nA {type(obj).__name__} with the following details will be created: ")

    for k, v in detail_dict.items():
        print(f"{k}: {v}")

    if yes_or_no("Confirm the change to proceed (Y/N): "):
        return 1


def validate_obj_by_name(cls, obj, inc_inac=0):
    print("Please enter the index or ID of the correct match below:")
    match_list = []

    for dict_id, val in cls._tracked_instances.items():
        # If flag set for hiding inactive and record is inactive, ignore
        if not inc_inac and not val["id"] == 0:
            continue

        # Measure similarity by levenshtein distance and prompt user to confirm details.
        # Append ID to match list for user validation
        elif levratio(val["name"], obj) > 0.8:
            match_list.append([dict_id, val['name'], val['dob']])

    # Print list of potential matches for user to select from
    if match_list:
        for count, match in enumerate(match_list):
            print(f"{count}) ID: {match[0]} Name: {match[1]}, DOB: {match[2]}")

    else:
        print("No records found matching those details.")
        return 0

    # Prompt user to select option from above
    while True:
        try:
            selection = input("Select an index number or enter an ID from above: ")

            # Quit if q or blank is entered
            if selection == 'q' or not selection:
                return 0

            selection = int(selection)

            # Masterfile IDs begin after 10000, so if number under that range, it will select as an index
            if selection in match_list and selection > 9999:
                obj = selection
                return obj

            elif selection in len(match_list):
                obj = match_list[selection]
                return obj

            # Prompt user to break if record does not exist
            else:
                print("Record does not exist.")

                if not yes_or_no("Continue with selection? "):
                    return 0

        except TypeError:
            print("Response must be a number.")
