# This file contains various functions to be used in the route optimisation tool.
import pickle
import pathlib
import validate
import classes
import pandas as pd
import time


def write_obj(obj):
    """
    Writes the object to file as a JSON using the pickle module
    Adds/updates the tracked instances class attribute
    """
    with open(f"./data/{obj.__class__.__name__}/{obj.id}.pkl", "wb") as file:
        pickle.dump(obj, file)

    # Update tracked instance dictionary with new value (overwrites old values).
    if isinstance(obj, classes.person.Human):
        obj._tracked_instances[obj.id] = {"status": obj._status,
                                          "name": obj._name,
                                          "dob": obj._dob,
                                          "sex": obj._sex}

    elif isinstance(obj, classes.visits.Visit):
        obj._tracked_instances[obj.id] = {"status": obj._status,
                                          "date": obj._exp_date}

        # Create or add to the search by date list for visits
        try:
            obj._instance_by_date[obj.exp_date].append(obj.id)

        except KeyError:
            obj._instance_by_date[obj._exp_date] = [obj.id]

    else:
        obj._tracked_instances[obj.id] = {"status": obj._status,
                                          "name": obj._name}

    print(f"{obj.__class__.__name__} successfully saved.\n")

    return 1


def get_obj(cls, inc_inac=0):
    """
    Class method to initialise a class instance from file. Returns the file as an object
    Prompts user to include inactive records as well.
    """

    while True:
        search_obj = validate.qu_input("Name or ID: ")

        # Quit if q or blank is entered
        if not search_obj:
            return 0

        # If not an id, search for instance in self.tracked_instances
        if search_obj.isnumeric():
            obj_id = search_obj
            break

        obj_id = validate.validate_obj_by_name(cls, search_obj, inc_inac=inc_inac)

        if obj_id:
            break

    # Generate and return object of class that is passed as argument
    if obj_id:
        file = f"./data/{cls.__qualname__}/{obj_id}.pkl"
        return load_obj(cls, file, inc_inac=inc_inac)

    else:
        print("Record not found.")
        return 0


def load_obj(cls, file_path, inc_inac=0):
    """Loads an object from file. Leveraged by class methods when loading an object from file."""
    # TODO: Determine why this is still pulling in inactive records when flag set
    try:
        with open(file_path, "rb") as file:
            obj = pickle.load(file)

        # If set to only show active and record is inactive, return that this record is inactive.
        if inc_inac and obj.status == 0:
            print("Record has been deactivated.")
            return 0

        # print(f"{cls.__qualname__} successfully loaded.")
        return obj

    except (FileNotFoundError, OSError):
        print(f"\n{cls.__qualname__} could not be found.")


def load_tracked_obj(cls):
    """Class method to initialise all instances of a class from file. Modifies the class attribute tracked_instances.
        This is uses to allow for quick searching by name, date of birth, and ID"""
    # TODO: Convert to a pull from a set of text files rather than reading each individual object file.
    try:
        file_path = pathlib.Path(f"./data/{cls.__qualname__}/").glob("*.pkl")
        # Quit if there are no files in that masterfile
        for file in file_path:
            if not file:
                return 0

            obj = load_obj(cls, file)

            # Update tracked instance dictionary with new value (overwrites old values).
            if isinstance(obj, classes.person.Human):
                cls._tracked_instances[obj.id] = {"status": obj._status,
                                                  "name": obj._name,
                                                  "dob": obj._dob,
                                                  "sex": obj._sex}

            elif isinstance(obj, classes.visits.Visit):
                cls._tracked_instances[obj.id] = {"status": obj._status,
                                                  "date": obj._exp_date}

                # Create or add to the search by date list for visits
                try:
                    obj._instance_by_date[obj.exp_date].append(obj.id)

                except KeyError:
                    obj._instance_by_date[obj.exp_date] = [obj.id]

            else:
                cls._tracked_instances[obj.id] = {"status": obj._status,
                                                  "name": obj._name}

            # next(cls._id_iter)

    except (FileNotFoundError, OSError):
        print(f"{cls.__qualname__} could not be found.")


def generate_flat_file(cls):
    """
    Generates a flat file for import. User can populate and import using read_csv()
    :param cls: Class to generate flat file
    :return: 1 if successful
    """
    # Get a list of params in the __init__ definition
    params = cls.__init__.__code__.co_varnames

    # Create a pandas dataframe with just column headings (remove init_dict) and save to csv
    flat_file = pd.DataFrame(columns=params)
    flat_file = flat_file.drop(["self", "kwargs"], axis=1)

    while True:
        try:
            filepath = validate.qu_input("Enter a file location to export the .csv to: ")

            if not filepath:
                return 0

            flat_file.to_csv(filepath)
            print("Export successful.")
            time.sleep(2)

            return 1

        except (FileNotFoundError, OSError):
            print("File not found. Ensure the input file contains '.csv' at the end.")


def export_csv(cls):
    """
    Generates a flat file for import. User can populate and import using read_csv()
    :param cls: Class to generate flat file
    :return: 1 if successful
    """
    # Get a list of params in the __init__ definition, and remove self and kwargs
    params = cls.__init__.__code__.co_varnames[1:-1]

    # Initialize a blank list of objects to write, then populate with user's requested objects
    obj_data = []
    while True:
        obj = get_obj(cls)

        if not obj:
            break

        # Create a dict for each object, then append to list
        val_obj_dict = {param: obj.__getattribute__(param) for param in params}
        obj_data.append(val_obj_dict)

    if not obj_data:
        return 0

    # Create a pandas dataframe with column headings, then populate with data from list above
    data_export = pd.DataFrame(data=obj_data, columns=params)


    # Write to file
    while True:
        try:
            filepath = validate.qu_input("Enter a file location to export the .csv to: ")

            if not filepath:
                return 0

            data_export.to_csv(filepath)
            print("Export successful.")
            time.sleep(2)

            return 1

        except (FileNotFoundError, OSError):
            print("File not found. Ensure the input file contains '.csv' at the end.")


def import_csv(cls, filepath=None):
    """
    Reads a file from csv and saves them as objects.
    :param cls: Class of object(s) to be created.
    :param filepath: Filepath of CSV file
    :return: 1 if successful
    """
    # TODO: Make sure this matches on ID before it imports
    while True:
        try:
            # If filepath not passed through, prompt user input
            if not filepath:
                filepath = validate.qu_input("Enter a csv file location to load the file: ")

            # If still blank, exit
            if not filepath:
                return 0

            import_data = pd.read_csv(filepath)
            import_data = import_data.fillna(0)
            data_dict_list = import_data.to_dict("records")

            # Loop through each dict from the import and initialize + save a new object
            for data in data_dict_list:
                obj = cls(**data)
                obj.write_self()

            print("Import successful.")
            time.sleep(2)

            return 1

        except (FileNotFoundError, OSError):
            print("File not found. Ensure the input file contains '.csv' at the end.")


