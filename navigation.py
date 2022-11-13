# This file contains functions to be used in the creating the GUI.
# Stick with TUI for now, but launch completed map into web-browser or GUI

import validate
from person import Patient


def main_menu(class_list):
    while True:
        try:
            selection = int(input("""
                Please select an option from the list below:
                    1) Geolocation Features
                    2) Create/Modify Records
            """))

            if selection == "q" or "":
                return 0

            elif selection == 1:
                geo_feat()
                continue

            elif selection == 2:
                class_selection(class_list)
                continue

            else:
                print("Invalid selection.")

        except TypeError:
            print("Please select an option by number from the list above.\n")


def class_selection(class_list):
    print("Which type of record would you like to create/modify?")

    for i, cls in enumerate(class_list):
        print(f"{i}) {cls}")

    while True:
        try:
            selection = int(input("Select a number from above: "))

            if selection == "q" or "":
                return 0

            # Verify that the selection is in the class list
            elif selection in range(len(class_list)):
                selection = class_list[selection]

                # Prompt user for record name or id to load
                obj = class_list[selection].read_self()

                # If record exists, prompt user to modify or delete.
                if obj:
                    inact_or_modify(obj)

                # If record does not exist, prompt user if they'd like to create one.
                else:
                    if validate.yes_or_no("Create a new record? "):

                        # For visits, a patient will need to be loaded in order to link it.
                        if selection == "Visit":
                            print("Please select a patient to create a visit request.")
                            obj = Patient.load_self()
                            obj.generate_request()

                        # Initialize a new instance of selected Human subclass and assign attributes
                        else:
                            obj = selection()
                            obj.set_demog()

                continue

            else:
                print("Invalid selection.")

        except TypeError:
            print("Please select an option by number from the list above.\n")


def inact_or_modify(obj):
    while True:
        print(f"""
            ID: {obj._id} 
            Name: {obj.name}

            Please select an option from the list below:
                1) Modify
                2) Delete
        """)

        try:
            selection = int(input("Option: "))

            if selection == "q" or "":
                return 0

            elif selection == 1:
                obj.update_self()

            elif selection == 2:
                obj.inactivate_self()

            else:
                print("Invalid selection.")

        except TypeError:
            print("Please select an option by number from the list above.\n")


def geo_feat():
    pass
