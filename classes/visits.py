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
    _instance_by_date = {}
    _c_sched_status = ("unassigned", "assigned", "no show", "cancelled")
    _c_cancel_reason = ("clinician unavailable", "patient unavailable", "no longer needed", "expired", "system action")

    def __init__(self, pat_id, status=1, address="", sched_status="unscheduled", time_earliest="", time_latest="", exp_date=""):
        """Initializes a new request and links with pat_id. It contains the following attributes:
            req_id, pat_id, name, status, the earliest time, latest time, sched status, and cancel_reason"""
        self._id = next(self._id_iter)
        self._pat_id = pat_id
        self._clin_id = None
        self._address = address
        self._name = "Visit" + str(self._id)
        self._status = status
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
    def patient_name(self):
        if self._pat_id:
            name = classes.person.Patient._tracked_instances[self._pat_id]["name"]
            return f"{name[0]}, {name[1]} {name[2] if name[2] else None}"

        else:
            return None

    @property
    def clinician_name(self):
        if self._clin_id:
            name = classes.person.Clinician._tracked_instances[self._clin_id]["name"]
            return f"{name[0]}, {name[1]} {name[2] if name[2] else None}"

        else:
            return None

    @property
    def address(self):
        """
        Displays an address parsed using USAddress. Loops through values in dictionary to output human-readable address.
        :return: Human-readable address
        """
        pat = in_out.load_obj(classes.person.Patient, f"./data/Patient/{self._pat_id}.pkl")
        return pat.address

    @property
    def zip_code(self):
        pat = in_out.load_obj(classes.person.Patient, f"./data/Patient/{self._pat_id}.pkl")
        return pat.zip_code

    @property
    def building(self):
        pat = in_out.load_obj(classes.person.Patient, f"./data/Patient/{self._pat_id}.pkl")
        return pat.building

    @property
    def coord(self):
        pat = in_out.load_obj(classes.person.Patient, f"./data/Patient/{self._pat_id}.pkl")
        return pat.coord

    @property
    def plus_code(self):
        pat = in_out.load_obj(classes.person.Patient, f"./data/Patient/{self._pat_id}.pkl")
        return pat.plus_code

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
                                          "     2. Assign Visit\n"
                                          "     3. Inactivate Record\n"
                                          "\n"
                                          "Selection: ")

            if not selection:
                return 0

            # Update request date and time
            elif selection == "1":
                self.update_date_time()

            elif selection == "2":
                self.manual_assign_visit()

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

        # Save old date for searching and updating instances_by_date index
        old_date = self._exp_date

        detail_dict = {
            "Expected Date": self.exp_date,
            "Time Window": f"{self.time_earliest} - {self.time_latest}"
        }

        # If user does not confirm info, changes will be reverted.
        if not validate.confirm_info(self, detail_dict):
            self.refresh_self()
            return 0

        # Remove visit from instances_by_date index
        self._instance_by_date[old_date].remove(self.id)

        # Save and update instance lists
        self.write_self()

        return 1

    def manual_assign_visit(self):
        """
        Manually assigns a visit to a clinician, in contrast to running the team optimiser algorithm.
        This updates the status of the visit to scheduled and updates the clinician's visits list.
        This will not be available if the visit is inactive or scheduled.
        :return: 1 if successful
        """
        # Check if visit is inactive. If so, quit.
        if self.status == 0:
            print("This visit is inactive.")
            return 0

        # Check if visit is assigned already. If so, prompt user about re-assigning.
        elif self.sched_status == self._c_sched_status[1]:
            print("This visit is already assigned. See the details below:\n")
            # Display visit details to user
            self.show_visit_details()

            while True:
                selection = validate.qu_input('What would you like to do:\n'
                                              '1. Unassign the visit\n'
                                              '2. Reassign the visit to another clinician\n')

                if not selection:
                    return 0

                # if unassign visit, unassign from clinician in clin_id
                elif selection == "1":
                    self.unassign_visit()
                    return 1

                # If reassign visit, just continue with function
                elif selection == "2":
                    break

                else:
                    print("Invalid selection.")

        # If neither of the above conditions are true, allow user to reassign visit by selecting a clinician.
        if self.assign_to_clinician():
            return 1

    def assign_to_clinician(self):
        """
        Assigns the visit to a clinician.
        :return: 1 if successful
        """
        print("Please select a clinician to assign this visit.")
        clin = classes.person.Clinician.load_self()

        if not clin:
            return 0

        # Create or add to the visit by date list for clinician
        try:
            clin.visits[self.exp_date].append(self.id)

        except KeyError:
            clin.visits[self._exp_date] = [self.id]

        self._clin_id = clin.id
        self._sched_status = self._c_sched_status[1]

        # Write changes to file, or back out if fails to save
        if clin.write_self():
            self.write_self()
            return 1

        else:
            self.refresh_self()
            return 0

    def unassign_visit(self):
        """
        Assigns the visit to a clinician.
        :return: 1 if successful
        """
        # Remove visit from assigned clinician
        clin = in_out.load_obj(classes.person.Clinician, f"./data/Clinician/{self._clin_id}.pkl")

        # If linked clinician fails to load, refresh and cancel action.
        if not clin:
            print("Unable to load linked clinician.")
            self.refresh_self()
            return 0

        # Remove visit from clinician and unassign clinician to visit
        clin.visits[self.exp_date].remove(self.id)
        clin.write_self()

        self._clin_id = ""
        self.write_self()

        return 1

    def show_visit_details(self):
        """
        Displays details of current visit, including patient, clinician, and status.
        :return: 1 if successful
        """
        # Output linked visit details
        detail_dict = {
            "Visit ID": self.id,
            "Patient": self.patient_name,
            "Clinician": self.clinician_name,
            "Visit Address": self.address,
            "Expected Date": self.exp_date,
            "Time Window": f"{self.time_earliest} - {self.time_latest}"
        }

        for k, v in detail_dict.items():
            print(f"{k}: {v}")

        print("\n")

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
            "Patient": obj.patient_name,
            "Visit ID": obj.id,
            "Visit Address": obj.address,
            "Expected Date": obj.exp_date,
            "Time Window": f"{obj.time_earliest} - {obj.time_latest}"
        }

        # If user confirms information is correct, a new object is created, written, and added to _tracked_instances
        if not validate.confirm_info(obj, detail_dict):
            print("Record not created.")
            return 0

        # Save each item if successful
        if obj.write_self():
            # Create or add to the search by date list for visits
            try:
                pat.visits[obj.exp_date].append(obj.id)

            except KeyError:
                pat.visits[obj._exp_date] = [obj.id]

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

            # If any linked patient fails to load, refresh and cancel action.
            if not patient:
                print("Unable to load linked patient.")
                self.refresh_self()
                return 0

            patient.visits[self.exp_date].remove(self.id)
            patient.write_self()

            # Remove visit from assigned clinician
            clin = in_out.load_obj(classes.person.Clinician, f"./data/Clinician/{self._clin_id}.pkl")

            # If linked clinician fails to load, refresh and cancel action.
            if not clin:
                print("Unable to load linked clinician.")
                self.refresh_self()
                return 0

            clin.visits[self.exp_date].remove(self.id)
            clin.write_self()

            # Cancel visit
            self.write_self()
            print("Visit successfully cancelled.")

            return 1

    @classmethod
    def evaluate_requests(cls):
        """Evaluates all Visits and marks them as no shows if they are past their expected date"""
        for instance in cls._tracked_instances:
            try:
                with open(f"./data/{cls.__qualname__}/{instance['id']}", "rb") as read_file:
                    visit = pickle.load(read_file)

                    # Evaluate date against current date and mark as expired if due before current date
                    if datetime.strptime(visit.exp_date, '%d-%m-%Y').date() < date.today():
                        visit.status = 0
                        visit.cancel_reason = cls._c_cancel_reason[3]

                        # Remove visit from patient's list
                        patient = in_out.load_obj(classes.person.Patient, f"./data/Patient/{visit._pat_id}.pkl")

                        # If any linked patient fails to load, refresh and cancel action.
                        if not patient:
                            print("Unable to load linked patient.")
                            visit.refresh_self()
                            return 0

                        patient.visits[visit.exp_date].remove(visit.id)
                        patient.write_self()

                        # Remove visit from assigned clinician
                        clin = in_out.load_obj(classes.person.Clinician, f"./data/Clinician/{visit._clin_id}.pkl")

                        # If linked clinician fails to load, refresh and cancel action.
                        if not clin:
                            print("Unable to load linked clinician.")
                            visit.refresh_self()
                            return 0

                        clin.visits[visit.exp_date].remove(visit.id)
                        clin.write_self()

                        cls.write_self(visit)

            except FileNotFoundError as err:
                print("File could not be found.")
                return err

    # TODO: Add a class method to reactivate a record
    # TODO: Add a method to find all visits today without a clinician
