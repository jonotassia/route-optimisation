# This file contains classes to be used in the route optimisation tool.
import itertools
import demo
import lib_func


class Patient:
    new_pat_iter = itertools.count()

    def __init__(self):
        self.pat_id = next(self.new_pat_iter)

        while True:
            demographics = demo.basic_demo()

            if lib_func.confirm_info():
                break

        self.first_name = demographics["First Name"]
        self.last_name = demographics["Last Name"]
        self.middle_name = demographics["Middle Name"]
        self.dob = demographics["Date of Birth"]
        self.sex = demographics["Sex"]
        self.address = demographics["Address"]

        with open(f"./data/patients/pat_{self.pat_id}", "w") as file:
            file.write(demographics)

        print("Patient created.")

    def update_patient_details(self):
        pass

    def assign_team(self):
        """Assigns the clinician to a team so that they can be considered in that team's route"""
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


class Clinician:
    clin_id_iter = itertools.count()

    def __init__(self):
        self.clin_id = next(self.clin_id_iter)

        while True:
            demographics = demo.basic_demo()

            if lib_func.confirm_info():
                break

        self.first_name = demographics["First Name"]
        self.last_name = demographics["Last Name"]
        self.middle_name = demographics["Middle Name"]
        self.dob = demographics["Date of Birth"]
        self.sex = demographics["Sex"]
        self.address = demographics["Address"]

        with open(f"./data/clinicians/clin_{self.clin_id}", "w") as file:
            file.write(demographics)

        print("Patient created.")

    def update_clinician_details(self):
        pass

    def assign_team(self):
        """Assigns the clinician to a team so that they can be considered in that team's route"""
        pass

    def update_start_end(self):
        """Sets the starting and ending time/geocoded address for the clinician"""
        pass

    def calculate_clinician_trip(self):
        """Calculates the estimated trip route for the clinician. Allows for overrides of start/end constraints"""
        pass


class Request:
    req_id_iter = itertools.count()

    def __init__(self, address, time):
        req_id = next(self.req_id_iter)
        self.address = address
        self.time = time

        with open("./data/requests", "w") as file:
            pass

    def cancel_request(self):
        pass

    def update_request(self):
        pass
