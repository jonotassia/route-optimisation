# This file contains various functions to be used in the route optimisation tool.

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


def assign_routes():
    """Considers availability of all patients and number of requests to book and allocates appropriately"""
    pass


def confirm_info(obj):
    """This function will be used to confirm information for any object that is created
     from one of the classes in classes.py"""

    print(f"A {type(obj).__name__} with the following details will be created: ")

    for k, v in vars(obj).items():
        print(f"{k}: {v}")

    if yes_or_no("Confirm the change to proceed (Y/N): "):
        return 1


def evaluate_requests():
    """Evaluates all requests and marks them as no shows if they are past their expected date"""
    # TODO: Determine how to pull all requests without being in a request context. Suggestion: Use a database.
    pass
