# This file contains various functions to be used in the route optimisation tool.
import pickle
import pathlib
from Levenshtein import ratio as levratio
import asyncio


def write_obj(obj):
    """Writes the object to file as a JSON using the pickle module"""
    with open(f"./data/{obj.__class__.__name__}/{obj.id}", "wb") as file:
        pickle.dump(obj, file)

    # if object does not exist within the tracked_instances dictionary, append.
    if obj._tracked_instances[obj.id]:
        print(f"{obj.__class__.__name__} successfully saved.")

    else:
        obj._tracked_instances[obj.id] = {"full_name": obj["full_name"],
                                          "dob": obj["dob"]}


def get_obj(cls):
    """Class method to initialise a patient from file. Returns the patient as a Patient object"""
    # TODO: Determine how to let them search by name as well. Suggestion: use database.
    obj_id = input("Name or ID: ")

    # If not an id, search for instance in self.tracked_instances
    if obj_id.isalpha():
        print("Please enter the index or ID of the correct match below:")
        count = 1
        match_list = []

        # Measure similarity by levenshtein distance and prompt user to confirm details
        for dict_id, val in cls._tracked_instances.items():
            if levratio(val["full_name"], obj_id) > 0.8:
                print(f"{count}) Name: {val['full_name']}, ID: {val['id']}, DOB: {val['dob']}")
                match_list.append(dict_id)
                count += 1

        while True:
            try:
                selection = int(input("Select an index number or enter an ID: "))

                # Masterfile IDs begin after 10000, so if number under that range, it will select as an index
                if selection in match_list and selection > 9999:
                    obj_id = selection
                    break

                elif selection in len(match_list):
                    obj_id = match_list[selection]
                    break

                else:
                    print("Invalid selection.")

            except TypeError:
                continue

    file = f"./data/{cls.__class__.__name__}/{obj_id}"
    load_obj(cls, file)


async def load_obj(cls, file_path):
    """Loads an object from file. Leveraged by class methods when loading an object from file."""
    try:
        with open(file_path, "rb") as file:
            obj = pickle.load(file)

        print(f"{cls.__class__.__name__} successfully loaded.")
        return obj

    except FileNotFoundError:
        print(f"{cls.__class__.__name__} could not be found.")


async def load_tracked_obj(cls):
    """Class method to initialise all instances of a class from file. Modifies the class attribute tracked_instances.
        This is uses to allow for quick searching by name, date of birth, and ID"""
    # TODO: Determine if there is a way to remove name and dob dynamically for requests

    file_path = pathlib.Path(f"./data/{cls.__class__.__name__}").glob("*.txt")
    for file in file_path:
        obj = await load_obj(cls, file)
        obj._tracked_instances[obj["id"]] = {"full_name": obj["full_name"],
                                             "dob": obj["dob"]}


def assign_routes():
    """Considers availability of all Patient and number of Visit to book and allocates appropriately"""
    pass
