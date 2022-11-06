# This file contains classes to be used in the route optimisation tool.
import pickle
import itertools
import demog
import lib_func


# TODO: Determine how to dynamically generate new variables so that they are unique
#       (perhaps point a global dictionary or list to a file)?

# TODO: Determine best way to generate requests that are not tied to a date, but relative to days of week


class Patient:
    new_pat_iter = itertools.count()  # Create a counter to assign new value each time a new obj is created

    def __init__(self, status=1, first_name="", last_name="", middle_name="", dob="", sex="", address=""):
        """Initiates and writes-to-file a patient with the following attributes:
        id, first name, last name, middle name, date of birth, sex, and address"""
        self.pat_id = next(self.new_pat_iter)
        self.status = status
        self.first_name = first_name
        self.last_name = last_name
        self.middle_name = middle_name
        self.dob = dob
        self.sex = sex
        self.address = address

        self.write_pat()

        print("Patient successfully saved.")

    def set_patient_demog(self):
        while True:
            demog.basic_demog(self)

            if lib_func.confirm_info(self):
                break

        self.write_pat()

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
        """This method initializes and returns a request (class = Request) for scheduling, which is written to file"""

        address = demog.get_address()
        time_earliest = demog.get_time()
        time_latest = demog.get_time()
        date = demog.get_date()

        new_request = Request(self.pat_id, address, time_earliest, time_latest, date)
        return new_request

    def write_pat(self):
        with open(f"./data/patients/pat_{self.pat_id}", "wb") as file:
            pickle.dump(self, file)

        print("Patient successfully saved.")

    @classmethod
    def load_pat(cls):
        # TODO: Determine how to let them search by name as well
        clin_id = input("Patient ID: ")

        try:
            with open(f"./data/patients/clin_{clin_id}", "rb") as file:
                patient = pickle.load(file)

                print("Patient successfully loaded.")

            return patient

        except FileNotFoundError:
            print("Patient could not be found.")


class Clinician:
    clin_id_iter = itertools.count()  # Create a counter to assign new value each time a new obj is created

    def __init__(self, status=1, first_name="", last_name="", middle_name="", dob="", sex="", address=""):
        """Initiates and writes-to-file a clinician with the following attributes:
        id, first name, last name, middle name, date of birth, sex, and address"""
        self.clin_id = next(self.clin_id_iter)
        self.status = status
        self.first_name = first_name
        self.last_name = last_name
        self.middle_name = middle_name
        self.dob = dob
        self.sex = sex
        self.address = address

        with open(f"./data/patients/clin_{self.clin_id}", "w") as file:
            file.write(str(vars(self)))

        print("Clinician successfully saved.")

    def set_clin_demog(self):
        while True:
            demog.basic_demog(self)

            if lib_func.confirm_info(self):
                break

        self.write_clin()

    def update_clin_details(self):
        pass

    def assign_team(self):
        """Assigns the clinician to a team so that they can be considered in that team's route"""
        pass

    def update_start_end(self):
        """Sets the starting and ending time/geocoded address for the clinician"""
        pass

    def optimize_clinician_trip(self):
        """Calculates the estimated trip route for the clinician. Allows for overrides of start/end constraints"""
        pass

    def write_clin(self):
        with open(f"./data/patients/clin_{self.clin_id}", "wb") as file:
            pickle.dump(self, file)

        print("Clinician successfully saved.")

    @classmethod
    def load_clin(cls):
        # TODO: Determine how to let them search by name as well
        clin_id = input("Clinician ID: ")

        try:
            with open(f"./data/patients/clin_{clin_id}", "rb") as file:
                clinician = pickle.load(file)

                print("Clinician successfully loaded.")

            return clinician

        except FileNotFoundError:
            print("Clinician could not be found.")


class Request:
    req_id_iter = itertools.count()  # Create a counter to assign new value each time a new obj is created

    def __init__(self, pat_id, status=1, address="", time_earliest="", time_latest="", date=""):
        """Initializes a new request and links with pat_id. It contains the following attributes:
            req_id, pat_id, address, the earliest time, and latest time"""
        self.req_id = next(self.req_id_iter)
        self.status = status
        self.pat_id = pat_id
        self.address = address
        self.time_earliest = time_earliest
        self.time_latest = time_latest
        self.date = date

        self.write_req()

    def cancel_request(self):
        pass

    def update_request(self):
        pass

    def write_req(self):
        with open(f"./data/requests/req_{self.req_id}", "wb") as file:
            pickle.dump(self, file)

        print("Request successfully saved.")

    @classmethod
    def load_req(cls):
        req_id = input("Request ID: ")

        try:
            with open(f"./data/requests/req_{req_id}", "rb") as file:
                request = pickle.load(file)

                print("Request successfully loaded.")

            return request

        except FileNotFoundError:
            print("Request could not be found.")
