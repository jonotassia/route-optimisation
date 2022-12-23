# This file contains functions to be used in the creating the GUI.
# Stick with TUI for now, but launch completed map into web-browser or GUI
import validate
import geolocation
import os
import classes
from data_manager import DataManagerMixin


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

        selection = validate.qu_input("Selection: ")

        if not selection:
            return 0

        elif selection == "1":
            geo_feat()
            continue

        elif selection == "2":
            obj_menu(class_list)
            continue

        # TODO: Remove before deployment
        elif selection == "dev":
            with DataManagerMixin.class_session_scope() as session:
                classes.team.Team.import_csv(session, filepath="./investigation/team_import.csv")
            with DataManagerMixin.class_session_scope() as session:
                classes.person.Patient.import_csv(session, filepath="./investigation/pat_import.csv")
            with DataManagerMixin.class_session_scope() as session:
                classes.person.Clinician.import_csv(session, filepath="./investigation/clin_import.csv")
            with DataManagerMixin.class_session_scope() as session:
                classes.visits.Visit.import_csv(session, filepath="./investigation/visit_import.csv")

        else:
            print("Invalid selection.")


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
            clear()
            print("Please select an option below:\n"
                  "     1) Find Record\n"
                  "     2) Create New Record\n"
                  "     3) Import/Export Record(s)\n")

            selection = validate.qu_input("Selection: ")

            if not selection:
                break

            if selection == "1":
                with cls.class_session_scope() as session:
                    obj_selection(cls, session)
                    continue

            elif selection == "2":
                with cls.class_session_scope() as session:
                    create_object_director(cls, session)
                    continue

            elif selection == "3":
                import_export_menu(cls)
                continue

            else:
                print("Invalid Selection.")


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
        selection = validate.qu_input("\nSelection: ")

        if not selection:
            return 0

        # Validate that user passed a valid class
        selection = validate.valid_cat_list(selection, selection_list)

        # Convert selection back to the class object by using the matching index in the string list
        cls = class_list[selection_list.index(selection)]

        return cls


def obj_selection(cls, session):
    """
    Prompts user for a class to enter, then asks for an object name or ID.
    If it exists, moves them to the modify or inactivate function.
    If it does not, prompts them to create a new object.
    :param session: Session for querying database
    :return: None
    """
    while True:
        # Prompt user for object details and load object
        obj = cls.get_obj(session)

        # If object exists, send user to modification screen. If record inactivated, quit.
        if obj:
            if not obj.update_self():
                return 0

        # If object does not exist, prompt user to create object as appropriate based on class.
        else:
            create_object_director(cls, session)

        if not validate.yes_or_no("Search for another object? "):
            break


def create_object_director(cls, session):
    """
    Directs the system to create a new record based on its class.
    :param cls: Class of object to be created.
    :param session: Session for querying database
    :return: None
    """
    clear()
    print(f"Record Type: {cls.__qualname__}".center(40))

    cont = validate.yes_or_no("\nCreate a new record? ")

    if cont:
        obj = cls.create_self(session)
        return obj


def import_export_menu(cls):
    """
    Menu containing different import/export options.
    :param cls: Class for import/export
    :return: None
    """
    while True:
        clear()

        print("Please select an option from the list below:\n"
              "    1) Create Flat File\n"
              "    2) Export Records\n"
              "    3) Import Records\n")

        selection = validate.qu_input("Selection: ")

        if not selection:
            return 0

        elif selection == "1":
            cls.generate_flat_file()
            continue

        elif selection == "2":
            with cls.class_session_scope() as session:
                cls.export_csv(session)
                continue

        elif selection == "3":
            with cls.class_session_scope() as session:
                cls.import_csv(session)
                continue

        else:
            print("Invalid selection.")


def geo_feat():
    """
    Menu for users to select geolocation features
    :return: 0 if no selection
    """
    while True:
        clear()

        print("Please select an option from the list below:\n"
              "    1) Clinician Optimizer\n"
              "    2) Team Optimizer\n"
              "    3) Display Route\n")

        selection = validate.qu_input("Selection: ")

        if not selection:
            return 0

        elif selection == "1":
            with classes.person.Clinician.class_session_scope() as session:
                obj = classes.person.Clinician.get_obj(session)
                if not obj:
                    continue
                obj.optimize_route()

        elif selection == "2":
            with classes.team.Team.class_session_scope() as session:
                obj = classes.team.Team.get_obj(session)
                if not obj:
                    continue
                obj.optimize_route()

        elif selection == "3":
            # Prompt user for which type of record to load
            print("For which of the following would you like to display the route?:\n"
                  "     1) Clinician\n"
                  "     2) Team\n")

            selection = -1
            while selection not in ["1", "2"]:
                selection = validate.qu_input("Selection: ")

                if not selection:
                    return 0

            if selection == "1":
                with classes.person.Clinician.class_session_scope() as session:
                    obj = classes.person.Clinician.get_obj(session)
                    if not obj:
                        continue
                    obj.display_route()

            elif selection == "2":
                with classes.team.Team.class_session_scope() as session:
                    obj = classes.team.Team.get_obj(session)
                    if not obj:
                        continue
                    obj.display_route()

            continue

        else:
            print("Invalid selection.")

