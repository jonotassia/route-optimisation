# This file contains functions to be used in the creating the GUI.
# Stick with TUI for now, but launch completed map into web-browser or GUI

import validate
import os
import sys
from classes.person import Patient
from classes.visits import Visit


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

            selection = input("Selection: ")

            if selection == "q" or not selection:
                return 0

            elif int(selection) == 1:
                geo_feat()
                continue

            elif int(selection) == 2:
                class_selection(class_list)
                continue

            else:
                print("Invalid selection.")

        except TypeError:
            print("Please select an option by number from the list above.\n")


def class_selection(class_list):
    while True:
        clear()

        # Prepare list of classes as strings to pass through to get_cat_value
        selection_list = [cat.__name__ for cat in class_list]

        prompt = "Which type of record would you like to create/modify?"
        selection = validate.get_cat_value(selection_list, prompt)

        if selection:
            # Convert selection back to the class object by using the matching index in the string list
            selection = class_list[selection_list.index(selection)]

            # TODO: Next test
            # Prompt user for record name or id to load
            obj = selection.load_self()

            # If record exists, prompt user to modify or delete.
            if obj:
                inact_or_modify(obj)

            # If record does not exist, prompt user if they'd like to create one.
            else:
                if validate.yes_or_no("Create a new record? "):

                    # For visits, a patient will need to be loaded in order to link it.
                    if selection == Visit:
                        print("Please select a patient to create a visit request.")
                        obj = Patient.load_self()
                        obj.generate_request()

                    # Initialize a new instance of selected Human subclass and assign attributes
                    else:
                        obj = selection()
                        obj.set_demog()
            continue

        else:
            return 0


def inact_or_modify(obj):
    while True:
        clear()
        print(f"ID: {obj._id} \n"
              f"Name: {obj.name}\n"
              f"\n"
              f"Please select an option from the list below:\n"
              f"1) Modify\n"
              f"2) Delete\n")

        try:
            selection = input("Option: ")

            if selection == "q" or not selection:
                return 0

            elif int(selection) == 1:
                obj.update_self()

            elif int(selection) == 2:
                obj.inactivate_self()

            else:
                print("Invalid selection.")

        except TypeError:
            print("Please select an option by number from the list above.\n")


def geo_feat():
    clear()
    pass
