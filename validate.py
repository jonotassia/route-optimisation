# This file contains functions to gather demographic information on Patient and Clinician
from datetime import datetime
from Levenshtein import ratio as levratio
import re
import usaddress
import requests
import classes.person
import navigation
import boto3


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
    # Try name in LAST, FIRST MIDDLE
    name_regex = re.compile(r"([A-Za-z]+),\s*([A-Za-z]+)\s*([A-Za-z]*)")

    if val_name := re.match(name_regex, value):
        try:
            return [val_name.group(1).lower().capitalize(),
                    val_name.group(2).lower().capitalize(),
                    val_name.group(3).lower().capitalize()]

        except AttributeError as err:
            return err

    # Try name in FIRST MIDDLE LAST
    else:
        name_regex = re.compile(r"([A-Za-z]+)\s+([A-Za-z]*)\s+([A-Za-z]+)")

        if val_name := re.match(name_regex, value):
            try:
                return [val_name.group(3).lower().capitalize(),
                        val_name.group(1).lower().capitalize(),
                        val_name.group(2).lower().capitalize()]

            except AttributeError as err:
                return err


def valid_address(value):
    """Uses Google Geocoding api to ensure address is valid: https://developers.google.com/maps/documentation/geocoding
        Returns address dictionary with keys for street, building/apt number, city, state, country, and post code."""
    # Initiate AWS SSM integration for secrets storage
    ssm = boto3.client('ssm')

    # Grab api key from AWS and authenticate with google
    google_api_key = ssm.get_parameter(Name="GOOGLE_CLOUD_API_KEY", WithDecryption=True)["Parameter"]["Value"]

    tag_mapping = {
        'Recipient': 'recipient',
        'AddressNumber': 'street_address',
        'AddressNumberPrefix': 'street_address',
        'AddressNumberSuffix': 'street_address',
        'StreetName': 'street_address',
        'StreetNamePreDirectional': 'street_address',
        'StreetNamePreModifier': 'street_address',
        'StreetNamePreType': 'street_address',
        'StreetNamePostDirectional': 'street_address',
        'StreetNamePostModifier': 'street_address',
        'StreetNamePostType': 'street_address',
        'LandmarkName': 'building',
        'BuildingName': 'building',
        'OccupancyType': 'building',
        'OccupancyIdentifier': 'building',
        'SubaddressIdentifier': 'building',
        'SubaddressType': 'building',
        'PlaceName': 'city',
        'StateName': 'state',
        'ZipCode': 'zip_code',
    }

    # Parse address text from user
    try:
        address = usaddress.tag(value, tag_mapping)

    except usaddress.RepeatedLabelError as err:
        return err

    # Prepare the address for query in JSON request
    address_query = [v for v in address[0].values()]

    payload = {
        "address": " ".join(address_query).replace(" ", "+"),
        "key": google_api_key
    }

    # Verify address is real using Google geocoding API. If real, return address.
    try:
        response = requests.get(
            f"https://maps.googleapis.com/maps/api/geocode/json?",
            params=payload
        )

    except requests.exceptions.RequestException:
        print("Unable to validate address. Please try again.")
        return 0

    # Save and return relevant address information - Address, zip code, place_id, and coordinates.
    if response.status_code == 200:
        # Prepare coordinate details
        coord_details = response.json()["results"][0]["geometry"]["location"]

        # Pull address details
        address = response.json()["results"][0]["formatted_address"]

        # Extract zip code and building info from response
        zip_code = None
        building = None

        for component in response.json()["results"][0]["address_components"]:
            if "postal_code" in component["types"]:
                zip_code = component["long_name"]

            if "premise" in component["types"]:
                building = component["long_name"]

        # Extract plus_code or set to None if missing
        try:
            plus_code = response.json()["results"][0]["plus_code"]["global_code"]
        except KeyError:
            plus_code = address

        # Populate address dictionary
        address = {
            "address": address,
            "zip_code": zip_code,
            "building": building,
            "plus_code": plus_code,
            "coord": (coord_details["lat"], coord_details["lng"])
        }

        return address

    else:
        return ValueError


def valid_time(value):
    """
    Checks for validity and returns in HHMM format
    :return: time if the time is valid, else None
    """
    try:
        time = datetime.strptime(str(value), "%H%M").time()
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
        print(f"    {x + 1}) {cat.capitalize()}")


def valid_cat_list(value, cat_list):
    """
    Validates that the input from a user is in the category list.
    :return: Value from cat list.
    """
    # Return corresponding index value if entered as alphanum
    str_cat_list = [str(cat) for cat in cat_list]

    if value.lower() in str_cat_list:
        return value.lower()

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
        # If multiselect, turn into list and prompt for more responses
        try:
            if attr_dict["multiselect"]:
                value_list = []
        except KeyError:
            pass

        while True:
            # If there is a category list entered, display the options before allowing selection.
            try:
                print_cat_value(attr_dict["cat_list"], f"Select a {attr_dict['term']}:")

            except KeyError:
                print(f"Select a {attr_dict['term']}: \n")

            # Prompt user with user-friendly text, then return value until
            value = qu_input(f"\nSelection: ")

            if not value:
                if yes_or_no("You have left this information blank. Would you like to quit? "):
                    return 0

                else:
                    continue

            # For multiselect items, continue to ask for additional values
            try:
                if attr_dict["multiselect"]:
                    if value not in value_list:
                        value_list.append(value)

                    else:
                        print(f"Value already in list.")

                    if yes_or_no("Add another value? "):
                        continue

            except KeyError:
                pass

            # Set the attribute (from the list if multiselect, else the value string)
            try:
                try:
                    if attr_dict["multiselect"]:
                        setattr(obj, attr_dict["attr"], value_list)

                except KeyError:
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

    # TODO: Update to use context manager
    session = cls.Session()

    match_list = []

    for obj in session.query(cls).distinct().all():
        # If flag set for hiding inactive and record is inactive, ignore
        if not inc_inac and not obj.status:
            continue

        # Create name strings in both formats for matching from the list in tracked instances
        if issubclass(cls, classes.person.Human):
            last_first_str = f"{obj._name[0]}, {obj._name[1]} {obj._name[2]}"
            first_last_str = f"{obj._name[1]} {obj._name[2]} {obj._name[0]}"

            # Measure similarity by levenshtein distance using Last, First M notation.
            lev_last_first = levratio(last_first_str, name)

            # If perfect match, return matches ID
            if lev_last_first == 1:
                return obj.id

            # Otherwise, add to the match list if it
            elif lev_last_first > 0.6:
                # Append ID to match list for user validation
                match_list.append([obj.id, obj.name, obj.dob, obj.sex])

            # Measure similarity by levenshtein distance using First M Last notation.
            lev_first_last = levratio(first_last_str, name)

            if lev_first_last == 1:
                return obj.id

            elif lev_first_last > 0.6:
                match_list.append([obj.id, obj.name, obj.dob, obj.sex])

        # For non-person objects: Measure similarity by levenshtein distance.
        else:
            lev_rat = levratio(obj.name, name)

            if lev_rat == 1:
                return obj.id

            elif lev_rat > 0.6:
                match_list.append([obj.id, obj.name])

    # Print list of potential matches for user to select from
    if not match_list:
        print("No records found matching those details.")
        return 0

    if issubclass(cls, classes.person.Human):
        for count, match in enumerate(match_list):
            print(f"{count + 1}) ID: {match[0]}, "
                  f"Name: {match[1][0]}, {match[1][1]} {match[1][2]}, "
                  f"DOB: {match[2].strftime('%d/%m/%Y')}"
                  f"Sex: {match[3]}"
                  )

    else:
        for count, match in enumerate(match_list):
            print(f"{count + 1}) ID: {match[0]}, Name: {match[1]}")

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
