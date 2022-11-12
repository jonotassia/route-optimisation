# This file contains classes to be used in the route optimisation tool.
import itertools
import validate
import in_out
import re
from visits import Visit
from datetime import date, time


# TODO: Determine best way to generate Visits that are not tied to a date, but relative to days of week


class Human:
    _new_hum_iter = itertools.count()  # Create a counter to assign new value each time a new obj is created
    _tracked_instances = []
    c_sex_options = ("male", "female", "not specified")

    def __init__(self, status=1, first_name="", last_name="", middle_name="", dob="", sex="", address=""):
        """Initiates a human objects with the following attributes:
        id, first name, last name, middle name, date of birth, sex, and address."""
        self.id = next(self._new_hum_iter)
        self.status = status
        self.first_name = first_name
        self.last_name = last_name
        self.middle_name = middle_name
        self.full_name = self.first_name + self.middle_name + self.last_name
        self.dob = dob
        self.sex = sex
        self.address = address

    @property
    def dob(self):
        return self.dob

    @dob.setter
    def dob(self, value):
        """Checks values of date of birth before assigning"""
        match = re.search(r'^([0-9]{1,2})\\/([0-9]{1,2})\\/([0-9]{4})$', value)

        try:
            value = date(match.group(3), match.group(2), match.group(1))
            self.dob = value

        except ValueError:
            print("Please enter a valid date of birth in the format DD/MM/YYYY")

    @property
    def sex(self):
        return self.sex

    @sex.setter
    def sex(self, value):
        """Checks values of sex before assigning"""
        if value.lower() in self.c_sex_options:
            self.sex = self.c_sex_options
        else:
            raise ValueError(f"Invalid selection. value not in {self.c_sex_options}")

    # TODO: add address with checks to list of properties.

    def set_demog(self):
        while True:
            self.first_name = validate.get_name()[0],
            self.last_name = validate.get_name()[1],
            self.middle_name = validate.get_name()[2],
            self.dob = validate.get_date(date_of_birth=1),
            self.sex = validate.get_sex(),
            self.address = validate.get_address()

            if validate.confirm_info(self):
                self.write_self()
                return 1

    def write_self(self):
        """Writes the object to file as a JSON using the pickle module"""
        in_out.write_obj(self)

    @classmethod
    def read_self(cls):
        """Class method to initialise the object from file. Returns the object"""
        in_out.read_obj(cls)

    @classmethod
    def load_tracked_instances(cls):
        in_out.load_tracked_obj(cls)


class Patient(Human):
    _new_pat_iter = itertools.count()  # Create a counter to assign new value each time a new obj is created
    _tracked_instances = []

    def __init__(self, status=1, first_name="", last_name="", middle_name="", dob="", sex="", address=""):
        """Initiates and writes-to-file a patient with the following attributes:
        id, first name, last name, middle name, date of birth, sex, and address.
        Additionally, initializes a list of Visits linked to the patient"""

        self.id = next(self._new_pat_iter)

        super().__init__(status, first_name, last_name, middle_name, dob, sex, address)

        self.visits = []

        self.write_self()

    def update_patient_address(self):
        """Updates the patient's address. Updates self.address. Writes updates to file.
            Returns 0 on successful update."""

        print(f"Please enter a new address or leave blank to enter previous start time: {self.address}\n")
        new_address = validate.get_address()

        valid = validate.yes_or_no("Please confirm that the updated details are correct.\n"
                                   f"Address: {new_address if new_address else self.address}")

        if valid:
            if new_address:
                self.address = new_address
            self.write_self()

        return 1

    def assign_team(self):
        """Assigns the patient to a team so that they can be considered in that team's route calculation"""
        pass

    def set_preferences(self):
        """Retrieves the patient's visit preferences"""
        pass

    def update_preferences(self):
        """Updates the patient's visit preferences"""
        pass

    def generate_request(self):
        """This method initializes and returns a request (class = Visit) for scheduling, which is written to file"""
        # TODO: Determine how to incorporate the concept of skills
        address = validate.get_address()
        time_earliest = validate.get_time()
        time_latest = validate.get_time()
        exp_date = validate.get_date()

        new_request = Visit(self.id, address, time_earliest, time_latest, exp_date)
        self.visits.append(new_request.id)

        return new_request

    def get_requests(self):
        pass


class Clinician(Human):
    _clin_id_iter = itertools.count()  # Create a counter to assign new value each time a new obj is created
    _tracked_instances = {}
    # TODO: Determine how to incorporate the concept of skills
    # TODO: Add licensure as an attribute

    def __init__(self, status=1, first_name="", last_name="", middle_name="", dob="", sex="", address=""):
        """Initiates and writes-to-file a clinician with the following attributes:
        id, first name, last name, middle name, date of birth, sex, and address
        Assumes standard shift time for start and end time, and inherits address for start/end address.
        These will be updated by a different function called update_start_end"""
        self.id = next(self._clin_id_iter)

        super().__init__(status, first_name, last_name, middle_name, dob, sex, address)

        self.start_address = address
        self.end_address = address
        self.start_time = time(9)
        self.end_time = time(17)

        self.write_self()

    def assign_team(self):
        """Assigns the clinician to a team so that they can be considered in that team's route calculation"""
        # TODO: Determine how to incorporate concept of a team
        pass

    def update_start_end(self):
        """Sets the starting and ending time/geocoded address for the clinician
            Updates self.start_time, self.start_address, self.end_time, and self.end_address. Writes updates to file.
            Returns 0 on successful update."""

        print(f"Please select a new shift start time or leave blank to keep previous start time: {self.start_time}\n")
        new_start_time = validate.get_time()

        print(f"Please select a new start address or leave blank to keep previous address: {self.start_address}\n")
        new_start_address = validate.get_address()

        print(f"Please select a new shift end time or leave blank to keep previous end time: {self.end_time}\n")
        new_end_time = validate.get_time()

        print(f"Please select a new end address or leave blank to keep previous address: {self.end_address}\n")
        new_end_address = validate.get_address()

        valid = validate.yes_or_no("Please confirm that the updated details are correct.\n"
                                   f"Start Time: {new_start_time if new_start_time else self.start_time}"
                                   f"Start Address: {new_start_address if new_start_address else self.start_address}"
                                   f"End Time: {new_end_time if new_end_time else self.end_time}"
                                   f"End Address: {new_end_address if new_end_address else self.end_address}")
        if valid:
            if new_start_time:
                self.start_time = new_start_time

            if new_start_address:
                self.start_address = new_start_address

            if new_end_time:
                self.end_time = new_end_time

            if new_end_address:
                self.end_address = new_end_address

            self.write_self()

        return 1

    def optimize_clinician_trip(self):
        """Calculates the estimated trip route for the clinician. Allows for overrides of start/end constraints"""
        pass
