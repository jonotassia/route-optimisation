# This file contains various functions to be used in the route optimisation tool.
import pickle
import pathlib
from Levenshtein import ratio as levratio


def yes_or_no(prompt):
    """Validates a user's input as yes (return 1) or no (return 0)."""
    while True:
        confirm = input(prompt).lower()

        if confirm == "y":
            return 1

        elif confirm == "n":
            return 0


def get_cat_value(cat_list, prompt):
    """Takes a category list as a parameter. Validates that the input from a user is in the category list
        Returns the index value if the user selects a value in the category list, or 0 if the user quits"""

    for i in range(len(cat_list)):
        print(f"{i}. {cat_list[i]}")

    while True:
        selection = input(prompt + 'Enter "q" or leave blank to quit.')

        if selection == "q" or "":
            return 0

        elif selection in cat_list or range(len(cat_list)):
            # Return index value if entered as numeric
            if selection.isnumeric():
                return selection

            # Return corresponding index value if entered as alphanum
            elif selection.isalnum():
                return cat_list.index(selection)

        else:
            print("Invalid selection.")


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


def read_obj(obj):
    """Class method to initialise a patient from file. Returns the patient as a Patient object"""
    # TODO: Determine how to let them search by name as well. Suggestion: use database.
    obj_id = input("Name or ID: ")

    # If not an id, search for instance in self.tracked_instances
    if obj_id.isalpha():
        print("Please enter the index or ID of the correct match below:")
        count = 1
        match_list = []

        # Measure similarity by levenshtein distance and prompt user to confirm details
        for dict_id, val in obj._tracked_instances.items():
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

    # Load from file
    try:
        with open(f"./data/{obj.__class__.__name__}/{obj_id}", "rb") as file:
            patient = pickle.load(file)

        print(f"{obj.__class__.__name__} successfully loaded.")
        return patient

    except FileNotFoundError:
        print(f"{obj.__class__.__name__} could not be found.")


def load_tracked_obj(obj):
    """Class method to initialise all instances of a class from file. Modifies the class attribute tracked_instances.
        This is uses to allow for quick searching by name, date of birth, and ID"""
    # TODO: Determine if there is a way to remove name and dob dynamically for requests

    try:
        file_path = pathlib.Path(f"./data/{obj.__class__.__name__}").glob("*.txt")
        for file in file_path:
            obj_details = pickle.load(open(file, "rb"))
            obj._tracked_instances[obj_details["id"]] = {"full_name": obj_details["full_name"],
                                                        "dob": obj_details["dob"]}

    except FileNotFoundError:
        print(f"{obj.__class__.__name__} could not be found.")


def assign_routes():
    """Considers availability of all Patient and number of Request to book and allocates appropriately"""
    pass


def confirm_info(obj):
    """This function will be used to confirm information for any object that is created
     from one of the classes in classes.py"""

    print(f"A {type(obj).__name__} with the following details will be created: ")

    for k, v in vars(obj).items():
        print(f"{k}: {v}")

    if yes_or_no("Confirm the change to proceed (Y/N): "):
        return 1
