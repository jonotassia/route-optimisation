# This file contains relevant classes and functions to be used in the route optimisation tool.

class Patient():
    def __init__(self, id, address):
        pass

    def update_patient_details(self):
        pass

    def get_preferences(self):
        """Retrieves the patient's visit preferences"""
        pass

    def update_preferences(self):
        """Updates the patient's visit preferences"""
        pass

    def generate_request(self):
        """This method generates a request (class = Request) for scheduling"""
        pass


class Clinician():
    def __init__(self, id, start_address, end_address, shift_start, shift_end, team):
        pass

    def update_clinician_details(self):
        pass

    def override_start_end(self):
        """Sets the starting and ending time/geocoded address for the clinician"""
        pass

    def calculate_clinician_trip(self):
        """Calculates the estimated trip route for the clinician. Allows for overrides of start/end constraints"""
        pass


class Request():
    def __init__(self, id, address, time):
        pass

    def cancel_request(self):
        pass

    def update_request(self):
        pass


def assign_routes():
    """Considers availability of all patients and number of requests to book and allocates appropriately"""
    pass


def create_clinician():
    """Creates a clinician record and saves them to the CLINICIAN database"""
    pass


def create_patient():
    """Creates a clinician record and saves them to the PATIENT database"""
    pass
