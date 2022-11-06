# This file contains various functions to be used in the route optimisation tool.

def assign_routes():
    """Considers availability of all patients and number of requests to book and allocates appropriately"""
    pass


def create_clinician():
    """Creates a clinician record and saves them to the CLINICIAN database"""
    pass


def create_patient():
    """Creates a clinician record and saves them to the PATIENT database"""
    pass


def confirm_info(obj):
    """This function will be used to confirm information for any object that is created
     from one of the classes in classes.py"""

    print(f"A {type(obj).__name__} with the following details will be created: ")

    for k, v in obj.vars().items():
        print(f"{k}: {v}")

    while True:
        confirm = input("Confirm details (Y/N): ").lower()

        if confirm == "y":
            return 1

        elif confirm == "n":
            return 0


