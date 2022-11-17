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
        self._address = address
        self._time_earliest = time_earliest
        self._time_latest = time_latest
        self._exp_date = exp_date
        self._cancel_reason = None
        self._sched_status = sched_status

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
        """Checks values of status before assigning"""
        try:
            if value == 1 or 0:
                self.status = value

            else:
                raise ValueError

        except ValueError:
            print("Status can only be 0 or 1.")

    @property
    def address(self):
        return self._address

    @address.setter
    def address(self, value):
        """Checks values of date of birth before assigning"""
        address = validate.valid_address(value)

        if address:
            self._address = address

        else:
            raise ValueError("Please enter a valid date in the format DD/MM/YYYY.\n")

    @property
    def time_earliest(self):
        return self._time_earliest

    @time_earliest.setter
    def time_earliest(self, value):
        """Checks values of time window start before assigning"""
        time = validate.valid_time(value)

        if time:
            self._time_earliest = time

        else:
            raise ValueError("Please enter a valid time in the format HHMM.\n")

    @property
    def time_latest(self):
        return self._time_latest

    @time_latest.setter
    def time_latest(self, value):
        """Checks values of time window end before assigning"""
        time = validate.valid_time(value)

        if time:
            self._time_latest = time

        else:
            raise ValueError("Please enter a valid time in the format HHMM.\n")

    @property
    def cancel_reason(self):
        return self._cancel_reason

    @cancel_reason.setter
    def cancel_reason(self, value):
        """Checks values of cancel reason before assigning"""
        reason = validate.valid_cat_list(value, self._c_cancel_reason)

        if reason:
            self._cancel_reason = reason

        else:
            raise ValueError(f"Invalid selection. Value not in {self._c_cancel_reason}")

    @property
    def sched_status(self):
        return self._sched_status

    @sched_status.setter
    def sched_status(self, value):
        """Checks values of sched status before assigning"""
        reason = validate.valid_cat_list(value, self._c_sched_status)

        if reason:
            self._sched_status = reason

        else:
            raise ValueError(f"Invalid selection. Value not in {self._c_sched_status}")

    @property
    def exp_date(self):
        return self._exp_date

    @exp_date.setter
    def exp_date(self, value):
        """Checks values of expected date before assigning"""
        date = validate.valid_date(value)

        if date:
            self._exp_date = date

        else:
            raise ValueError("Please enter a valid date in the format DD/MM/YYYY.\n")

    def update_self(self):
        """Allows the user to update visit information, including date/time window or address
            Updates self.date, self.time_earliest, and self.time_latest. Writes updates to file.
            Returns 0 on successful update."""

        while True:
            selection = validate.qu_input("What would you like to update:"
                                          "     1. Visit Date and Time"
                                          "     2. Visit Address")

            if not selection:
                return 0

            # Update request date and time
            elif selection == 1:
                attr_list = [
                    {
                        "term": f"Expected Date (DD/MM/YYYY). Previous: {self.exp_date if self.exp_date else 'None'}",
                        "attr": self.exp_date
                    },
                    {
                        "term": f"Start Time Window. Previous: {self.time_earliest if self.time_earliest else 'None'}",
                        "attr": self.time_earliest
                    },
                    {
                        "term": f"End Time Window. Previous: {self.time_latest if self.time_latest else 'None'}",
                        "attr": self.time_latest
                    },
                ]

                # Update all attributes from above. Quit if user quits during any attribute
                if not validate.get_info(self, attr_list):
                    self.refresh_self()
                    return 0

                detail_dict = {
                    "Expected Date": self.exp_date,
                    "Start Time Window": self.time_earliest,
                    "End Time Window": self.time_latest,
                }

                # If user does not confirm info, changes will be reverted.
                if not validate.confirm_info(self, detail_dict):
                    self.refresh_self()
                    return 0

                self.write_self()

                return 1

            # Update request address
            elif selection == 2:
                attr_list = [
                    {
                        "term": f"Address. Previous: {self.address if self.address else 'None'}",
                        "attr": self.address
                    }
                ]

                # Update all attributes from above. Quit if user quits during any attribute
                if not validate.get_info(self, attr_list):
                    self.refresh_self()
                    return 0

                detail_dict = {
                    "Address": self.address
                }

                # If user does not confirm info, changes will be reverted.
                if not validate.confirm_info(self, detail_dict):
                    self.refresh_self()
                    return 0

                self.write_self()
                return 1

    def schedule_visit(self):
        pass

    def write_self(self):
        """Writes the object to file as a JSON using the pickle module"""
        in_out.write_obj(self)

    @classmethod
    def create_self(cls):
        """
        Object initialized from patient and adds to pat._visits. Loops through each detail and assigns to the object.
        If any response is blank, the user will be prompted to quit or continue.
        If they continue, they will begin at the element that the quit out of
        Once details are completed, the user is prompted to review information and complete creation.
        :return:
            1 if the user completes initialization
            0 if the user does not
        """
        print("Please select a patient to create a visit request.")
        pat = classes.person.Patient.load_self()
        obj = pat.generate_request()

        attr_list = [
            {
                "term": "Address",
                "attr": obj.address
            },
            {
                "term": "Expected Date",
                "attr": obj.exp_date
            },
            {
                "term": "Window Start Time",
                "attr": obj.time_earliest,
            },
            {
                "term": "Window End Time",
                "attr": obj.time_latest
            }
        ]

        # Update all attributes from above. Quit if user quits during any attribute
        if not validate.get_info(obj, attr_list):
            return 0

        detail_dict = {
            "ID": obj.id,
            "Visit Address": obj.address,
            "Expected Date": obj.exp_date,
            "Window Start Time": obj.time_earliest,
            "Window End Time": obj.time_latest
        }

        # If user confirms information is correct, a new object is created, written, and added to _tracked_instances
        if not validate.confirm_info(obj, detail_dict):
            print("Record not created.")
            return 0

        pat.write_self()
        obj.write_self()
        return obj

    def refresh_self(self):
        """Refreshes an existing object from file in the in case users need to backout changes. Returns the object"""
        print("Reverting changes...")
        in_out.load_obj(self, f"./data/{self.__class__.__name__}/{self.id}.pkl")

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
            attr_list = [
                {
                    "term": "Cancel Reason: ",
                    "attr": self.cancel_reason,
                    "cat_list": self._c_cancel_reason
                }
            ]

            # Update all attributes from above. Quit if user quits during any attribute
            if not validate.get_info(self, attr_list):
                return 0

            prompt = "Are you sure you want to cancel this request? You will be unable to schedule this request."
            if not validate.yes_or_no(prompt):
                self.refresh_self()
                return 0

            self.status = 0

            # Remove visit from patient's list
            patient = in_out.load_obj(classes.person.Patient, f"./data/Patient/{self._pat_id}")
            patient.visits.remove(self.id)
            patient.write_self()
            self.write_self()

            print("Visit successfully cancelled.")

            return 1

    @classmethod
    def evaluate_requests(cls):
        """Evaluates all Visits and marks them as no shows if they are past their expected date"""
        for instance in cls.tracked_instances:
            try:
                with open(f"./data/{cls.__qualname__}/{instance['id']}", "rb") as read_file:
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
