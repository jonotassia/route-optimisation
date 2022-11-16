# This file contains functions to gather demographic information on Patient and Clinician
from datetime import datetime
from Levenshtein import ratio as levratio
import re


def qu_input(prompt):
    value = input(prompt)

    if value == "q" or not value:
        return 0

    else:
        return value


def yes_or_no(prompt):
    """Validates a user's input as yes (return 1) or no (return 0)."""
    while True:
        confirm = qu_input(prompt).lower()

        if not confirm:
            return 0

        elif confirm == ("n" or "no"):
            return 0

        elif confirm == ("y" or "yes"):
            return 1


def valid_date(value):
    """
    Checks for validity and returns in DD/MM/YYYY format
    :return: date if the date is valid, else None
    """
    try:
        date = datetime.strptime(value, "%d/%m/%Y").date()
        return date

    except ValueError as err:
        return err


def valid_name(value):
    """Gathers name information. Returns first name, middle name, and last name"""
    name_regex = re.compile(r"([A-Za-z]+),\s*([A-Za-z]+)(\s+)*([A-Za-z]*)")

    try:
        valid_name = re.match(name_regex, value)

        return [valid_name.group(1).capitalize(), valid_name.group(2).capitalize(), valid_name.group(4).capitalize()]

    except ValueError as err:
        return err


def valid_address(value):
    """Uses Place Key api to ensure address is valid: https://www.placekey.io/blog/getting-started-with-placekey-io
        Returns address dictionary with keys for street, building/apt number, city, state, country, and post code."""
    # TODO: Implement Placekey API to validate address
    address = value

    if address:
        return address

    else:
        return ValueError


def valid_time(value):
    """
    Checks for validity and returns in HHMM format
    :return: time if the time is valid, else None
    """
    try:
        time = datetime.strptime(value, "%H%M").time()
        return time

    except ValueError as err:
        return err


def print_cat_value(cat_list, prompt):
    """
    Takes a category list and prompt as a parameter.
    :return: None
    """
    # Display category values and prompt user for selection
    while True:
        print(prompt)
        for x, cat in enumerate(cat_list):
            print(f"    {x+1}. {cat.capitalize()}")


def valid_cat_list(value, cat_list):
    """
    Validates that the input from a user is in the category list.
    :return: Value from cat list.
    """
    # Return corresponding index value if entered as alphanum
    if value in cat_list:
        return value

    # Return index value if entered as numeric and is an index in the category list
    elif value.isnumeric() and int(value) - 1 in range(len(cat_list)):
        return cat_list[int(value) - 1]

    else:
        return ValueError


def get_info(obj, attr_dict_list: list):
    """
    Takes a list of dictionaries containing attributes and input functions to prompt user for required details.
    Assigns to associated object property.
    :param obj: The object to you of which you will update the parameters.
    :param attr_dict_list: list of dictionaries of attributes to edit with the following structure:
                        term: user-friendly term for the item you'd like to modify
                        attr: attribute name to modify
                        cat_list: category list to display (if relevant)
    :return: 1 if successful, else 0 if user quites
    """

    for attr_dict in attr_dict_list:
        while True:
            # If there is a category list entered, display the options before allowing selection.
            if attr_dict["cat_list"]:
                print_cat_value(attr_dict["cat_list"], f"Select a {attr_dict['name']}:")

            # Prompt user with user-friendly text, then return value until
            value = qu_input(f"{attr_dict['name']}: ")

            if not value:
                if yes_or_no("You have left this information blank. Would you like to quit?"):
                    continue

                else:
                    return 0

            try:
                obj.attr = value
                return 1

            except ValueError as err:
                print(err)


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
            selection = qu_input("Select an index number or enter an ID from above: ")

            # Quit if q or blank is entered
            if not selection:
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
