# This file contains various functions to be used in the route optimisation tool.
import pickle
import pathlib
import validate
import classes


def write_obj(obj):
    """
    Writes the object to file as a JSON using the pickle module
    Adds/updates the tracked instances class attribute
    """
    with open(f"./data/{obj.__class__.__name__}/{obj.id}.pkl", "wb") as file:
        pickle.dump(obj, file)

    # Update tracked instance dictionary with new value (overwrites old values). Varies type of object.
    if isinstance(obj, classes.person.Human):
        obj._tracked_instances[obj.id] = {"status": obj._status,
                                          "name": obj._name,
                                          "dob": obj._dob,
                                          "sex": obj._sex}

    else:
        obj._tracked_instances[obj.id] = {"status": obj._status,
                                          "name": obj._name}

    print(f"{obj.__class__.__name__} successfully saved.\n")


def get_obj(cls):
    """
    Class method to initialise a class instance from file. Returns the file as an object
    Prompts user to include inactive records as well.
    """

    while True:
        obj_id = 0
        obj = validate.qu_input("Name or ID: ")

        # Quit if q or blank is entered
        if not obj:
            return 0

        # Prompt and flag for including inactive records
        inc_inac = True if validate.yes_or_no("Include inactive? ") else False

        # If not an id, search for instance in self.tracked_instances
        if obj.isnumeric():
            obj_id = obj
            break

        elif obj.isalpha():
            obj_id = validate.validate_obj_by_name(cls, obj, inc_inac=inc_inac)
            break

        else:
            print("Invalid response.")
            continue

    # Generate and return object of class that is passed as argument
    if obj_id:
        file = f"./data/{cls.__qualname__}/{obj_id}.pkl"
        return load_obj(cls, file)

    else:
        print("Record not found.")
        return 0


def load_obj(cls, file_path):
    """Loads an object from file. Leveraged by class methods when loading an object from file."""
    try:
        with open(file_path, "rb") as file:
            obj = pickle.load(file)

        print(f"{cls.__qualname__} successfully loaded.")
        return obj

    except FileNotFoundError:
        print(f"{cls.__qualname__} could not be found.")


def load_tracked_obj(cls):
    """Class method to initialise all instances of a class from file. Modifies the class attribute tracked_instances.
        This is uses to allow for quick searching by name, date of birth, and ID"""
    # TODO: Convert to a pull from a set of text files rather than reading each individual object file.
    obj = None
    try:
        file_path = pathlib.Path(f"./data/{cls.__qualname__}/").glob("*.pkl")
        for file in file_path:
            obj = load_obj(cls, file)

        # Update tracked instance dictionary with new value (overwrites old values).
        if isinstance(obj, classes.person.Human):
            cls._tracked_instances[obj.id] = {"status": obj._status,
                                              "name": obj._name,
                                              "dob": obj._dob,
                                              "sex": obj._sex}

        else:
            cls._tracked_instances[obj.id] = {"status": obj._status,
                                              "name": obj._name}

        next(cls._id_iter)

    except FileNotFoundError:
        print(f"{cls.__qualname__} could not be found.")


