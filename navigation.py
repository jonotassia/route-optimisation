# This file contains functions to be used in the creating the GUI.
# Stick with TUI for now, but launch completed map into web-browser or GUI
import validate
import display_map
import geolocation
import os


def clear():
    """
    Clears screen based on system type.
    :return: None
    """
    # Clear for Linux/Mac
    if os.name == 'posix':
        os.system("clear")

    # Clear for Windows
    else:
        os.system("cls")

    return None


def main_menu(class_list):
    while True:
        clear()

        print("Please select an option from the list below:\n"
              "    1) Geolocation Features\n"
              "    2) Create/Modify Records\n")

        try:

            selection = validate.qu_input("Selection: ")

            if not selection:
                return 0

            elif selection == "1":
                geo_feat()
                continue

            elif selection == "2":
                obj_menu(class_list)
                continue

            else:
                print("Invalid selection.")

        except TypeError:
            print("Please select an option by number from the list above.\n")


def obj_menu(class_list):
    """
    Prompts user for a class to enter, then asks for an object name or ID.
    If it exists, moves them to the modify or inactivate function.
    If it does not, prompts them to create a new object.
    :param class_list: List of classes. Inherited from main function
    :return: None
    """
    while True:
        clear()

        # Prompt user for the class they want to modify/create
        cls = class_selection(class_list)

        if not cls:
            return 0

        while True:
            # Prompt user for object details and load object
            obj = cls.load_self()

            # If object exists, send user to modification screen. If record inactivated, quit.
            if obj:
                if not obj.update_self():
                    return 0

            # If object does not exist, prompt user to create object as appropriate based on class.
            else:
                create_object_director(cls)

            if not validate.yes_or_no("Search for another object? "):
                break


def class_selection(class_list):
    """
    Prompts user to select a class.
    :param class_list: List of classes. Inherited from main function
    :return: The class the user selected, or 0 if quit
    """
    # Prepare list of classes as strings to pass through to get_cat_value
    selection_list = [cat.__name__ for cat in class_list]

    prompt = "Which type of record would you like to create/modify?"
    validate.print_cat_value(selection_list, prompt)

    while True:
        selection = validate.qu_input("Selection: ")

        if not selection:
            return 0

        # Validate that user passed a valid class
        selection = validate.valid_cat_list(selection, selection_list)

        # Convert selection back to the class object by using the matching index in the string list
        cls = class_list[selection_list.index(selection)]

        return cls


def create_object_director(cls):
    """
    Directs the system to create a new record based on its class.
    :param cls: Class of object to be created.
    :return: None
    """
    clear()
    print(f"Record Type: {cls.__qualname__}".center(40))

    cont = validate.yes_or_no("\nCreate a new record? ")

    if cont:
        obj = cls.create_self()
        return obj


def geo_feat():
    """
    Menu for users to select geolocation features
    :return: 0 if no selection
    """
    while True:
        clear()

        print("Please select an option from the list below:\n"
              "    1) Clinician Optimizer\n"
              "    2) Team Optimizer\n")

        try:

            selection = validate.qu_input("Selection: ")

            if not selection:
                return 0

            elif selection == "1":
                geolocation.optimize_trip()
                continue

            elif selection == "2":
                geolocation.optimize_team()
                continue

            else:
                print("Invalid selection.")

        except TypeError:
            print("Please select an option by number from the list above.\n")
