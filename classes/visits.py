# This file contains the Visit class to be used in the route optimisation tool.
import pickle
import itertools
import validate
import in_out
import classes
import navigation
from datetime import datetime, date


class Visit:
    _id_iter = itertools.count(10000)  # Create a counter to assign new value each time a new obj is created
    _tracked_instances = {}
    _c_sched_status = ("unscheduled", "scheduled", "no show", "cancelled")
    _c_cancel_reason = ("clinician unavailable", "patient unavailable", "no longer needed", "expired", "system action")

    def __init__(self, pat_id, status=1, sched_status="unscheduled", address="", time_earliest="", time_latest="", exp_date=""):
        """Initializes a new request and links with pat_id. It contains the following attributes:
            req_id, pat_id, name, status, address, the earliest time, latest time, sched status, and cancel_reason"""
        self._id = next(self._id_iter)
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
        return "Visit " + str(self._id)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        """Checks values of status before assigning"""
        try:
            if value == 1 or value == 0:
                self._status = value

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

        if not isinstance(address, Exception):
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

        if not isinstance(time, Exception):
            self._time_earliest = time

        else:
            raise ValueError("Please enter a valid time in the format HHMM.\n")

    @property
    def time_latest(self):
        return self._time_latest

    @time_latest.setter
    def time_latest(self, value):
        """Checks values of time window end before assigning"""
        # TODO: Figure out how to handle the midnight instance in time window and scheduling
        time = validate.valid_time(value)

        if not isinstance(time, Exception):
            # If there is no start time window (unlikely), allow end time window to be set.
            if not self.time_earliest:
                self._time_latest = time

            # If there is a start time window and it is before the start time, allow it to be set.
            if self.time_earliest and time > self.time_earliest:
                self._time_latest = time

            else:
                raise ValueError("End time cannot be before start time.")
        else:
            raise ValueError("Please enter a valid time in the format HHMM.\n")

    @property
    def cancel_reason(self):
        return self._cancel_reason

    @cancel_reason.setter
    def cancel_reason(self, value):
        """Checks values of cancel reason before assigning"""
        reason = validate.valid_cat_list(value, self._c_cancel_reason)

        if not isinstance(reason, Exception):
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

        if not isinstance(reason, Exception):
            self._sched_status = reason

        else:
            raise ValueError(f"Invalid selection. Value not in {self._c_sched_status}")

    @property
    def exp_date(self):
        return self._exp_date.strftime("%d/%m/%Y")

    @exp_date.setter
    def exp_date(self, value):
        """Checks values of expected date before assigning"""
        date = validate.valid_date(value)

        if isinstance(date, Exception):
            raise ValueError("Please enter a valid date in the format DD/MM/YYYY.\n")

        elif date < date.today():
            raise ValueError("Date cannot be before today.\n")

        else:
            self._exp_date = date

    def update_self(self):
        """Allows the user to update visit information, including date/time window or address.
            Returns 0 on successful update."""
        navigation.clear()
        print(f"ID: {self.id}".ljust(10), f"Name: {self.name}\n".rjust(10))

        while True:
            selection = validate.qu_input("What would you like to do:\n"
                                          "     1. Modify Visit Date and Time\n"
                                          "     2. Modify Visit Address\n"
                                          "     3. Inactivate Record\n"
                                          "\n"
                                          "Selection: ")

            if not selection:
                return 0

            # Update request date and time
            elif selection == "1":
                self.update_date_time()

            # Update request address
            elif selection == "2":
                self.update_address()

            elif selection == "3":
                self.inactivate_self()
                return 0

            else:
                print("Invalid selection.")

    def update_date_time(self):
        """
        Updates self.date, self.time_earliest, and self.time_latest. Writes updates to file.
        :return: 1 if successful.
        """
        attr_list = [
            {
                "term": f"Expected Date (DD/MM/YYYY). Previous: {self.exp_date if self.exp_date else 'None'}",
                "attr": "exp_date"
            },
            {
                "term": f"Start Time Window. Previous: {self.time_earliest if self.time_earliest else 'None'}",
                "attr": "time_earliest"
            },
            {
                "term": f"End Time Window. Previous: {self.time_latest if self.time_latest else 'None'}",
                "attr": "time_latest"
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

    def update_address(self):
        """
        Updates address for the request.
        :return: 1 if successful.
        """
        attr_list = [
            {
                "term": f"Address. Previous: {self.address if self.address else 'None'}",
                "attr": "address"
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
        """Writes the object to file as a .pkl using the pickle module"""
        if in_out.write_obj(self):
            return 1

    @classmethod
    def create_self(cls, pat_id=""):
        """
        Object initialized from patient and adds to pat._visits.
        Loops through each detail and assigns to the object.
        If any response is blank, the user will be prompted to quit or continue.
        If they continue, they will begin at the element that the quit out of
        Once details are completed, the user is prompted to review information and complete creation.
        :return:
            obj if the user completes initialization
            0 if the user does not
        """
        # Load a patient to generate and attach the visit. If id is passed through, do not prompt for ID.
        if pat_id:
            pat = in_out.load_obj(classes.person.Patient, f"./data/Patient/{pat_id}.pkl")

        else:
            print("Please select a patient to create a visit request.")
            pat = classes.person.Patient.load_self()

        if not pat:
            return 0

        obj = cls(pat.id)

        attr_list = [
            {
                "term": "Address",
                "attr": "address"
            },
            {
                "term": "Expected Date",
                "attr": "exp_date"
            },
            {
                "term": "Window Start Time",
                "attr": "time_earliest",
            },
            {
                "term": "Window End Time",
                "attr": "time_latest"
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

        # Save each item if successful
        if obj.write_self():
            pat.visits.append(obj._id)
            pat.write_self()

        return 1

    def refresh_self(self):
        """Refreshes an existing object from file in the in case users need to backout changes. Returns the object"""
        print("Reverting changes...")
        in_out.load_obj(type(self), f"./data/{self.__class__.__name__}/{self.id}.pkl")

    @classmethod
    def load_self(cls):
        """Class method to initialise the object from file. Returns the object"""
        obj = in_out.get_obj(cls)

        if not obj:
            return 0

        else:
            return obj

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
                    "term": "Cancel Reason",
                    "attr": "cancel_reason",
                    "cat_list": self._c_cancel_reason
                }
            ]

            # Update all attributes from above. Quit if user quits during any attribute
            if not validate.get_info(self, attr_list):
                self.refresh_self()
                return 0

            prompt = "Are you sure you want to cancel this request? You will be unable to schedule this request. "
            if not validate.yes_or_no(prompt):
                self.refresh_self()
                return 0

            self.status = 0

            # Remove visit from patient's list
            patient = in_out.load_obj(classes.person.Patient, f"./data/Patient/{self._pat_id}.pkl")

            # If any linked patients fail to load, refresh and cancel action.
            if not patient:
                print("Unable to load linked patient.")
                self.refresh_self()
                return 0

            patient.visits.remove(self.id)
            patient.write_self()
            self.write_self()

            print("Visit successfully cancelled.")

            return 1

    @classmethod
    def evaluate_requests(cls):
        """Evaluates all Visits and marks them as no shows if they are past their expected date"""
        for instance in cls._tracked_instances:
            try:
                with open(f"./data/{cls.__qualname__}/{instance['id']}", "rb") as read_file:
                    request = pickle.load(read_file)

                    # Evaluate date against current date and mark as expired if due before current date
                    if datetime.strptime(request.exp_date, '%d-%m-%Y').date() < date.today():
                        request.status = 0
                        request.cancel_reason = cls._c_cancel_reason[3]
                        cls.write_self(request)

            except FileNotFoundError as err:
                print("File could not be found.")
                return err

    # TODO: Add a class method to reactivate a record
