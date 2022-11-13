# This file contains various functions to be used in the route optimisation tool.
import pickle
import pathlib
from Levenshtein import ratio as levratio

import validate


def write_obj(obj):
    """Writes the object to file as a JSON using the pickle module"""
    with open(f"./data/{obj.__class__.__name__}/{obj._id}", "wb") as file:
        pickle.dump(obj, file)

    # if object does not exist within the tracked_instances dictionary, append.
    if obj._tracked_instances[obj._id]:
        print(f"{obj.__class__.__name__} successfully saved.")

    else:
        obj._tracked_instances[obj._id] = {"name": obj.name,
                                           "dob": obj.dob}


def get_obj(cls):
    """
    Class method to initialise a class instance from file. Returns the file as an object
    Prompts user to include inactive records as well.
    """

    obj_id = input("Name or ID: ")

    if validate.yes_or_no("Include inactive? "):
        inc_inac = True

    else:
        inc_inac = False

    # If not an id, search for instance in self.tracked_instances
    if obj_id.isalpha():
        print("Please enter the index or ID of the correct match below:")
        match_list = []

        for dict_id, val in cls._tracked_instances.items():
            # If flag set for hiding inactive and record is inactive, ignore
            if not inc_inac and not val["id"] == 0:
                continue

            # Measure similarity by levenshtein distance and prompt user to confirm details.
            # Append ID to match list for user validation
            elif levratio(val["name"], obj_id) > 0.8:
                match_list.append([dict_id, val['name'], val['dob']])

        if match_list:
            for count, match in enumerate(match_list):
                print(f"{count}) ID: {match[0]} Name: {match[1]}, DOB: {match[2]}")

        else:
            print("No records found matching those details.")
            return 0

        while True:
            try:
                selection = int(input("Select an index number or enter an ID frome above: "))

                # Masterfile IDs begin after 10000, so if number under that range, it will select as an index
                if selection in match_list and selection > 9999:
                    obj_id = selection
                    break

                elif selection in len(match_list):
                    obj_id = match_list[selection]
                    break

                # Prompt user to break if record does not exist
                else:
                    print("Record does not exist.")

                    if not validate.yes_or_no("Continue with selection? "):
                        return 0

            except TypeError:
                continue

        file = f"./data/{cls.__class__.__name__}/{obj_id}"
        return load_obj(cls, file)


def load_obj(cls, file_path):
    """Loads an object from file. Leveraged by class methods when loading an object from file."""
    try:
        with open(file_path, "rb") as file:
            obj = pickle.load(file)

        print(f"{cls.__class__.__name__} successfully loaded.")
        return obj

    except FileNotFoundError:
        print(f"{cls.__class__.__name__} could not be found.")


def load_tracked_obj(cls):
    """Class method to initialise all instances of a class from file. Modifies the class attribute tracked_instances.
        This is uses to allow for quick searching by name, date of birth, and ID"""
    # TODO: Determine if there is a way to remove name and dob dynamically for requests

    try:
        file_path = pathlib.Path(f"./data/{cls.__name__}").glob("*.txt")
        for file in file_path:
            obj = load_obj(cls, file)
            cls._tracked_instances[obj.id] = {"status": obj.status,
                                              "name": obj.name,
                                              "dob": obj.name}

    except FileNotFoundError:
        print(f"{cls.__name__} could not be found.")


def assign_routes():
    """Considers availability of all Patient and number of Visit to book and allocates appropriately"""
    pass
