# This file contains functions to gather demographic information on Patient and Clinician
from datetime import datetime
from Levenshtein import ratio as levratio
import re
import usaddress
import classes.person
import navigation
import boto3
from placekey.api import PlacekeyAPI

def qu_input(prompt):
    value = input(prompt)

    if value == "q" or not value:
        return 0

    else:
        return value


def yes_or_no(prompt):
    """Validates a user's input as yes (return 1) or no (return 0)."""
    while True:
        confirm = qu_input(prompt)

        if not confirm:
            return 0

        if confirm.isnumeric():
            print('Please enter "yes" or "no".')

        elif confirm.lower() == "n" or confirm.lower() == "no":
            return 0

        elif confirm.lower() == "y" or confirm.lower() == "yes":
            return 1


def valid_date(value):
    """
    Checks for validity and returns in DD/MM/YYYY format
    :return: date if the date is valid, else None
    """
    try:
        date = datetime.strptime(value, "%d/%m/%Y")
        return date

    except ValueError as err:
        return err


def valid_name(value):
    """Gathers name information. Returns first name, middle name, and last name"""
    name_regex = re.compile(r"([A-Za-z]+),\s*([A-Za-z]+)(\s+)*([A-Za-z]*)")

    try:
        val_name = re.match(name_regex, value)

        return [val_name.group(1).capitalize(), val_name.group(2).capitalize(), val_name.group(4).capitalize()]

    except AttributeError as err:
        return err


def valid_address(value):
    """Uses Place Key api to ensure address is valid: https://www.placekey.io/blog/getting-started-with-placekey-io
        Returns address dictionary with keys for street, building/apt number, city, state, country, and post code."""
    # Initiate AWS SSM integration for secrets storage
    ssm = boto3.client('ssm')

    # Grab api key from AWS
    placekey_api_key = ssm.get_parameter(Name="placekey_api_key")
    pk_api = PlacekeyAPI(placekey_api_key)

    # Parse address text from user
    try:
        address = usaddress.tag(value)

    except usaddress.RepeatedLabelError as err:
        return err

    # Verify address is real using Placekey API. If real, return address.
    address_query = {
        "street_address": address["AddressNumber"] + address["StreetNamePreDirectional"] + address["StreetName"] + address["StreetNamePostType"],
        "city": address["PlaceName"],
        "region": address["StateName"],
        "postal_code": address["ZipCode"],
        "iso_country_code": "US",
    }

    if pk_api.lookup_placekey(address_query):
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
    print(prompt)
    for x, cat in enumerate(cat_list):
        print(f"    {x + 1}. {cat.capitalize()}")


def valid_cat_list(value, cat_list):
    """
    Validates that the input from a user is in the category list.
    :return: Value from cat list.
    """
    # Return corresponding index value if entered as alphanum
    str_cat_list = [str(cat) for cat in cat_list]

    if value in str_cat_list:
        return value

    # Return index value if entered as numeric and is an index in the category list
    elif str(value).isnumeric() and int(value) - 1 < len(cat_list):
        return cat_list[int(value) - 1]

    else:
        return ValueError


def get_info(obj, attr_dict_list: list):
    """
    Takes a list of dictionaries containing attributes and input functions to prompt user for required details.
    Assigns to associated object property.
    :param obj: The object to you of which you will update the parameters.
    :param attr_dict_list: list of dictionaries of attributes to edit with the following structure:
                        term: user-friendly term/phrase for the item you'd like to modify
                        attr: attribute name to modify
                        cat_list: category list to display (if relevant)
    :return: 1 if successful, else 0 if user quites
    """

    for attr_dict in attr_dict_list:
        while True:
            # If there is a category list entered, display the options before allowing selection.
            try:
                print_cat_value(attr_dict["cat_list"], f"Select a {attr_dict['term']}:")

            except KeyError:
                pass

            # Prompt user with user-friendly text, then return value until
            value = qu_input(f"\n{attr_dict['term']}: ")

            if not value:
                if yes_or_no("You have left this information blank. Would you like to quit? "):
                    return 0

                else:
                    continue

            try:
                setattr(obj, attr_dict["attr"], value)
                break

            except ValueError as err:
                print(err)

    return 1


def confirm_info(obj, detail_dict):
    """
    This function will be used to confirm information for any object that is created from a class instance.
    It loops through the passed dictionary to display relevant parameters.
    :param obj: Object - used to guide prompt.
    :param detail_dict: Includes the details which you would like to display to the user.
    :return: 1 if change is approved, else None
    """

    print(f"Please confirm the information below: ")

    for k, v in detail_dict.items():
        print(f"{k}: {v}")

    if yes_or_no("Confirm the change to proceed (Y/N): "):
        return 1


def validate_obj_by_name(cls, name, inc_inac=0):
    """
    Uses levenshtein distance to determine a ratio of distance.
    If a perfect match is found, it will return the id of the object.
    If it is not a perfect match, adds to the match_list and displays to user to select the correct record.
    :param cls: Class of object being searched.
    :param name: Name that is being searched.
    :param inc_inac: Flags the search to include inactive records.
    :return: Object ID
    """
    navigation.clear()
    match_list = []

    for dict_id, val in cls._tracked_instances.items():
        # If flag set for hiding inactive and record is inactive, ignore
        if not inc_inac and not val["status"]:
            continue

        # Create name strings in both formats for matching from the list in tracked instances
        if issubclass(cls, classes.person.Human):
            last_first_str = f"{val['name'][0]}, {val['name'][1]} {val['name'][2]}"
            first_last_str = f"{val['name'][1]} {val['name'][2]} {val['name'][0]}"

            # Measure similarity by levenshtein distance using Last, First M notation.
            lev_last_first = levratio(last_first_str, name)

            # If perfect match, return matches ID
            if lev_last_first == 1:
                return dict_id

            # Otherwise, add to the match list if it
            elif lev_last_first > 0.6:
                # Append ID to match list for user validation
                match_list.append([dict_id, val['name'], val['dob'], val['sex']])

            # Measure similarity by levenshtein distance using First M Last notation.
            lev_first_last = levratio(first_last_str, name)

            if lev_first_last == 1:
                return dict_id

            elif lev_first_last > 0.6:
                match_list.append([dict_id, val['name'], val['dob'], val['sex']])

        # For non-person objects: Measure similarity by levenshtein distance.
        else:
            lev_rat = levratio(val["name"], name)

            if lev_rat == 1:
                return dict_id

            elif lev_rat > 0.6:
                match_list.append([dict_id, val['name'], val['dob'], val['sex']])

    # Print list of potential matches for user to select from
    if not match_list:
        print("No records found matching those details.")
        return 0

    for count, match in enumerate(match_list):
        print(f"{count + 1}) ID: {match[0]}, "
              f"Name: {match[1][0]}, {match[1][1]} {match[1][2]}, "
              f"DOB: {match[2].strftime('%d/%m/%Y')}"
              f"Sex: {match[3]}"
              )

    # Prompt user to select option from above
    while True:
        try:
            selection = qu_input("\nSelect an index number from above: ")

            # Quit if q or blank is entered
            if not selection:
                return 0

            # Convert selection to integer.
            selection = int(selection)

            # Check response by index in match list
            if 0 < selection <= len(match_list):
                obj_id = match_list[selection - 1][0]
                return obj_id

            # Prompt user to break if record does not exist
            else:
                print("Invalid selection. Please select a record from above by index number.")

        except ValueError:
            print("Response must be the index number of the record.")
