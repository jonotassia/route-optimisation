# This file contains classes to be used in the route optimisation tool.
import pickle
import itertools
import demog
import lib_func
import re
from datetime import date, time

# TODO: Determine how to dynamically generate new variables so that they are unique
#       (perhaps point a global dictionary or list to a file)?

# TODO: Determine best way to generate Request that are not tied to a date, but relative to days of week


class Human:
    new_hum_iter = itertools.count()  # Create a counter to assign new value each time a new obj is created
    sex_options = ["male", "female", "not specified"]

    def __init__(self, status=1, first_name="", last_name="", middle_name="", dob="", sex="", address=""):
        """Initiates a human objects with the following attributes:
        id, first name, last name, middle name, date of birth, sex, and address."""
        self.id = next(self.new_hum_iter)
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
        if value.lower() in self.sex_options:
            self.sex = self.sex_options
        else:
            raise ValueError(f"Invalid selection. value not in {self.sex_options}")

    # TODO: add address with checks to list of properties.

    def set_demog(self):
        while True:
            self.first_name = demog.get_name()[0],
            self.last_name = demog.get_name()[1],
            self.middle_name = demog.get_name()[2],
            self.dob = demog.get_date(date_of_birth=1),
            self.sex = demog.get_sex(),
            self.address = demog.get_address()

            if lib_func.confirm_info(self):
                self.write_self()
                return 1

    def write_self(self):
        """Writes the object to file as a JSON using the pickle module"""
        lib_func.write_obj(self)

    @classmethod
    def read_self(cls):
        """Class method to initialise the object from file. Returns the object"""
        lib_func.read_obj(cls)


class Patient(Human):
    new_pat_iter = itertools.count()  # Create a counter to assign new value each time a new obj is created

    def __init__(self, status=1, first_name="", last_name="", middle_name="", dob="", sex="", address=""):
        """Initiates and writes-to-file a patient with the following attributes:
        id, first name, last name, middle name, date of birth, sex, and address.
        Additionally, initializes a list of Request linked to the patient"""

        self.id = next(self.new_pat_iter)

        super().__init__(status, first_name, last_name, middle_name, dob, sex, address)

        self.requests = []

        self.write_self()

    def update_patient_address(self):
        """Updates the patient's address. Updates self.address. Writes updates to file.
            Returns 0 on successful update."""

        print(f"Please enter a new address or leave blank to enter previous start time: {self.address}\n")
        new_address = demog.get_address()

        valid = lib_func.yes_or_no("Please confirm that the updated details are correct.\n"
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
        """This method initializes and returns a request (class = Request) for scheduling, which is written to file"""
        # TODO: Determine how to incorporate the concept of skills
        address = demog.get_address()
        time_earliest = demog.get_time()
        time_latest = demog.get_time()
        date = demog.get_date()

        new_request = Request(self.id, address, time_earliest, time_latest, date)
        self.requests.append(new_request.req_id)

        return new_request

    def get_requests(self):
        pass


class Clinician(Human):
    clin_id_iter = itertools.count()  # Create a counter to assign new value each time a new obj is created
    # TODO: Determine how to incorporate the concept of skills
    # TODO: Add licensure as an attribute

    def __init__(self, status=1, first_name="", last_name="", middle_name="", dob="", sex="", address=""):
        """Initiates and writes-to-file a clinician with the following attributes:
        id, first name, last name, middle name, date of birth, sex, and address
        Assumes standard shift time for start and end time, and inherits address for start/end address.
        These will be updated by a different function called update_start_end"""
        self.id = next(self.clin_id_iter)

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
        new_start_time = demog.get_time()

        print(f"Please select a new start address or leave blank to keep previous address: {self.start_address}\n")
        new_start_address = demog.get_address()

        print(f"Please select a new shift end time or leave blank to keep previous end time: {self.end_time}\n")
        new_end_time = demog.get_time()

        print(f"Please select a new end address or leave blank to keep previous address: {self.end_address}\n")
        new_end_address = demog.get_address()

        valid = lib_func.yes_or_no("Please confirm that the updated details are correct.\n"
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


class Request:
    req_id_iter = itertools.count()  # Create a counter to assign new value each time a new obj is created
    c_sched_status = ["Unscheduled", "Scheduled", "No Show", "Cancelled"]
    c_cancel_reason = ["Clinician unavailable", "Patient Unavailable", "No longer needed"]

    def __init__(self, pat_id, status=1, sched_status="", address="", time_earliest="", time_latest="", date=""):
        """Initializes a new request and links with pat_id. It contains the following attributes:
            req_id, pat_id, status, address, the earliest time, latest time, sched status, and cancel_reason"""
        self.req_id = next(self.req_id_iter)
        self.pat_id = pat_id
        self.status = status
        self.address = address
        self.time_earliest = time_earliest
        self.time_latest = time_latest
        self.date = date
        self.cancel_reason = None
        self.sched_status = sched_status

        self.write_self()

    def cancel_request(self):
        """This method sets the status of a request to inactive and the sched status to "cancelled".
        Prompts the user for a cancel reason and files back to self.cancel_reason
        It will not be cancelled if the request meets any of the below criteria:
        - The request is in the past
        - The request has already been scheduled
        - the request has already been deleted
        """

        # Checks if request is already inactive
        if self.status == 0:
            print("This request is already inactive.")
            return 0

        # Checks that sched status is scheduled using the schedule category list
        elif self.sched_status == self.c_sched_status[1]:
            print("This request is already scheduled. Please cancel the appointment instead.")
            return 0

        else:
            reason = lib_func.get_cat_value(self.c_cancel_reason, "Select a cancel reason. ")

            prompt = "Are you sure you want to cancel this request? You will be unable to schedule this request."
            if lib_func.yes_or_no(prompt):
                self.cancel_reason = reason
                self.status = 0

            self.write_self()

            return 1

    def update_request(self):
        """Allows the user to update request information, including date/time window or address
            Updates self.date, self.time_earliest, and self.time_latest. Writes updates to file.
            Returns 0 on successful update."""

        while True:
            selection = input("What would you like to update:"
                              "     1. Request Date and Time"
                              "     2. Request Address")

            if selection == "q" or "":
                return 0

            # Update request date and time
            elif selection == 1:
                print(f"Please select a new date or leave blank to keep previous date: {self.date}\n")
                new_date = demog.get_date()

                print(f"Please select a new start time window or leave blank to "
                      f"keep previous start window time: {self.time_earliest}\n")
                new_start = demog.get_time()

                print(f"Please select a new end time window or leave blank to "
                      f"keep previous end window time: {self.time_latest}\n")
                new_end = demog.get_time()

                valid = lib_func.yes_or_no("Please confirm that the updated details are correct.\n"
                                           f"Date: {new_date if new_date else self.date}"
                                           f"Start Window: {new_start if new_start else self.time_earliest}"
                                           f"End Window: {new_end if new_end else self.time_latest}")

                if valid:
                    if new_date:
                        self.date = new_date

                    if new_start:
                        self.time_earliest = new_start

                    if new_end:
                        self.time_latest = new_end
                    self.write_self()

                break

            # Update request address
            elif selection == 2:
                print(f"Please select a new address or leave blank to keep previous address: {self.address}")
                new_address = demog.get_address()

                valid = lib_func.yes_or_no("Please confirm that the updated details are correct."
                                           f"Address: {new_address if new_address else self.address}")

                if valid:
                    if new_address:
                        self.address = new_address
                    self.write_self()

                break

            else:
                print("Please select a valid option.\n")

    def schedule_request(self):
        pass

    def write_self(self):
        """Writes the object to file as a JSON using the pickle module"""
        lib_func.write_obj(self)

    @classmethod
    def read_self(cls):
        """Class method to initialise the object from file. Returns the object"""
        lib_func.read_obj(cls)