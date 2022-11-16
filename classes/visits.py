# This file contains the Visit class to be used in the route optimisation tool.
import pickle
import itertools
import validate
import in_out
import classes
from datetime import datetime, date


class Visit:
    visit_id_iter = itertools.count(10000)  # Create a counter to assign new value each time a new obj is created
    tracked_instances = {}
    _c_sched_status = ("unscheduled", "scheduled", "no show", "cancelled")
    _c_cancel_reason = ("clinician unavailable", "patient unavailable", "no longer needed", "expired", "system action")

    def __init__(self, pat_id, status=1, sched_status="", address="", time_earliest="", time_latest="", exp_date=""):
        """Initializes a new request and links with pat_id. It contains the following attributes:
            req_id, pat_id, name, status, address, the earliest time, latest time, sched status, and cancel_reason"""
        self._id = next(self.visit_id_iter)
        self._pat_id = pat_id
        self._name = "Visit" + str(self._id)
        self._status = status
        self.address = address
        self.time_earliest = time_earliest
        self.time_latest = time_latest
        self.exp_date = exp_date
        self.cancel_reason = None
        self.sched_status = sched_status

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return "Visit" + str(self._id)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        """Checks values of sex before assigning"""
        try:
            if value == 1 or 0:
                self.status = value

            else:
                raise ValueError

        except ValueError:
            print("Status can only be 0 or 1.")

    def update_self(self):
        """Allows the user to update visit information, including date/time window or address
            Updates self.date, self.time_earliest, and self.time_latest. Writes updates to file.
            Returns 0 on successful update."""

        while True:
            selection = input("What would you like to update:"
                              "     1. Visit Date and Time"
                              "     2. Visit Address")

            if selection == "q" or "":
                return 0

            # Update request date and time
            elif selection == 1:
                print(f"Please select a new date or leave blank to keep previous date: {self.exp_date}\n")
                new_date = validate.get_date()

                print(f"Please select a new start time window or leave blank to "
                      f"keep previous start window time: {self.time_earliest}\n")
                new_start = validate.get_time()

                print(f"Please select a new end time window or leave blank to "
                      f"keep previous end window time: {self.time_latest}\n")
                new_end = validate.get_time()

                valid = validate.yes_or_no("Please confirm that the updated details are correct.\n"
                                           f"Date: {new_date if new_date else self.exp_date}"
                                           f"Start Window: {new_start if new_start else self.time_earliest}"
                                           f"End Window: {new_end if new_end else self.time_latest}")

                if valid:
                    if new_date:
                        self.exp_date = new_date

                    if new_start:
                        self.time_earliest = new_start

                    if new_end:
                        self.time_latest = new_end
                    self.write_self()

                break

            # Update request address
            elif selection == 2:
                print(f"Please select a new address or leave blank to keep previous address: {self.address}")
                new_address = validate.get_address()

                valid = validate.yes_or_no("Please confirm that the updated details are correct."
                                           f"Address: {new_address if new_address else self.address}")

                if valid:
                    if new_address:
                        self.address = new_address
                    self.write_self()

                break

            else:
                print("Please select a valid option.\n")

    def schedule_visit(self):
        pass

    def write_self(self):
        """Writes the object to file as a JSON using the pickle module"""
        in_out.write_obj(self)

    @classmethod
    def create_self(cls):
        print("Please select a patient to create a visit request.")
        pat = classes.person.Patient.load_self()
        obj = pat.generate_request()

        while True:
            # Assign address
            address = validate.get_address()

            if address:
                obj.address = address

            else:
                if not validate.yes_or_no("You have left this information blank. Would you like to quit?"):
                    break

            # Assign expected date
            exp_date = validate.get_date()

            if exp_date:
                obj.exp_date = exp_date

            else:
                if not validate.yes_or_no("You have left this information blank. Would you like to quit?"):
                    break

            # Assign start time window
            time_earliest = validate.get_time()

            if time_earliest:
                obj.time_earliest = time_earliest

            else:
                if not validate.yes_or_no("You have left this information blank. Would you like to quit?"):
                    break

            # Assign start time window
            time_latest = validate.get_time()

            if time_latest:
                obj.time_latest = time_latest

            else:
                if not validate.yes_or_no("You have left this information blank. Would you like to quit?"):
                    break

            detail_dict = {
                "Visit Address": address,
                "Expected Date": exp_date,
                "Window Start": time_earliest,
                "Window End": time_latest
            }

            # If user confirms information is correct, a new object is created, written, and added to _tracked_instances
            if validate.confirm_info(obj, detail_dict):
                pat.write_self()
                return obj

        print("Record not created.")
        return 0


    @classmethod
    def load_self(cls):
        """Class method to initialise the object from file. Returns the object"""
        in_out.get_obj(cls)

    @classmethod
    def load_tracked_instances(cls):
        in_out.load_tracked_obj(cls)

    def inactivate_self(self):
        """This method sets the status of a visit request to inactive and the sched status to "cancelled".
        Prompts the user for a cancel reason and files back to self.cancel_reason
        Removes this request from the associated patient.
        It will not be cancelled if the request meets any of the below criteria:
        - The request is in the past
        - The request has already been scheduled
        - the request has already been deleted
        """

        # Checks if request is already inactive
        if self.status == 0:
            print("This record is already inactive.")
            return 0

        # Checks that sched status is scheduled using the schedule category list
        elif self.sched_status == self._c_sched_status[1]:
            print("This request is already scheduled. Please cancel the appointment instead.")
            return 0

        else:
            reason = validate.get_cat_value(self._c_cancel_reason, "Select a cancel reason. ")

            prompt = "Are you sure you want to cancel this request? You will be unable to schedule this request."
            if validate.yes_or_no(prompt):
                self.cancel_reason = reason
                self.status = 0
                self.write_self()

                # Remove visit from patient's list
                patient = in_out.load_obj(classes.person.Patient, f"./data/Patient/{self._pat_id}")
                patient.visits.remove(self._id)
                patient.write_self()

                print("Visit successfully cancelled.")

                return 1

    @classmethod
    async def evaluate_requests(cls):
        """Evaluates all Visits and marks them as no shows if they are past their expected date"""
        for instance in cls.tracked_instances:
            try:
                async with open(f"./data/{cls.__qualname__}/{instance['id']}", "rb") as read_file:
                    request = pickle.load(read_file)

                    # Evaluate date against current date and mark as expired if due before current date
                    if datetime.strptime(request.exp_date, '%m-%d-%Y').date() < date.today():
                        request.status = 0
                        request.cancel_reason = cls._c_cancel_reason[3]
                        cls.write_self(request)

            except FileNotFoundError as err:
                print("File could not be found.")
                return err

    # TODO: Add a class method to reactivate a record
