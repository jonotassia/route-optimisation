# This file contains the Visit class to be used in the route optimisation tool.
import itertools
import validate
import classes
import navigation
from sqlalchemy import Column, String, Date, Time, Integer, PickleType, ForeignKey
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import relationship
from data_manager import DataManagerMixin
from datetime import datetime, date


class Visit(DataManagerMixin, DataManagerMixin.Base):
    # Initialise table details
    __tablename__ = "Visit"
    _id = Column(Integer, primary_key=True, unique=True)
    _status = Column(String, nullable=True)
    _pat_id = Column(Integer, ForeignKey("Patient._id"))
    pat = relationship("Patient", back_populates="visits")
    _clin_id = Column(Integer, ForeignKey("Clinician._id"), nullable=True)
    clin = relationship("Clinician", back_populates="visits")
    _exp_date = Column(Date, nullable=True)
    _time_earliest = Column(Time, nullable=True)
    _time_latest = Column(Time, nullable=True)
    _visit_priority = Column(String, nullable=True)
    _visit_complexity = Column( String, nullable=True)
    _skill_list = Column(MutableList.as_mutable(PickleType), nullable=True)
    _discipline = Column(String, nullable=True)
    _cancel_reason = Column(String, nullable=True)
    _sched_status = Column(String, nullable=True)

    # Class Attributes
    _id_iter = itertools.count(10000)  # Create a counter to assign new value each time a new obj is created
    _c_visit_complexity = ("simple", "routine", "complex")
    _c_visit_priority = ("green", "amber", "red")
    _c_skill_list = classes.person.Clinician._c_skill_list
    _c_discipline = classes.person.Clinician._c_discipline
    _c_sched_status = ("unassigned", "assigned", "no show", "cancelled")
    _c_cancel_reason = ("clinician unavailable", "patient unavailable", "no longer needed", "expired", "system action")

    def __init__(self, pat_id, id=None, clin_id=None, status=1, sched_status="unscheduled", time_earliest="", time_latest="",
                 exp_date="", visit_complexity=_c_visit_complexity[1], visit_priority=_c_visit_priority[0],
                 skill_list=[], discipline="", **kwargs):
        """Initializes a new request and links with pat_id. It contains the following attributes:
            req_id, pat_id, name, status, the earliest time, latest time, sched status, and cancel_reason"""
        super().__init__()

        self._id = id if id else next(Visit._id_iter)
        self.exp_date = exp_date
        self.pat_id = pat_id
        self.clin_id = clin_id
        self._name = "Visit" + str(self._id)
        self.status = status
        self.time_earliest = time_earliest
        self.time_latest = time_latest
        self.visit_priority = visit_priority
        self.visit_complexity = visit_complexity
        self.skill_list = skill_list
        self.discipline = discipline
        self._cancel_reason = None
        self._sched_status = sched_status

        # Update all attributes from passed dict if provided
        self.__dict__.update(kwargs)

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
    def pat_id(self):
        return self._pat_id

    @pat_id.setter
    def pat_id(self, value):
        # Check valid ID and oad patient and create or add to the search by date list for visits
        if classes.person.Patient.load_obj(self.session, value):
            self._pat_id = value

        else:
            raise ValueError("This is not a valid patient ID.\n")

    @property
    def clin_id(self):
        return self._clin_id

    @clin_id.setter
    def clin_id(self, value):
        # Check valid ID
        if not value:
            self._clin_id = None

        # If clin exists, add to visit
        elif classes.person.Clinician.load_obj(self.session, value):
            self._clin_id = value
            self.sched_status = "assigned"

        else:
            raise ValueError("This is not a valid clinician ID.\n")

    @property
    def address(self):
        """
        Displays an address parsed using USAddress. Loops through values in dictionary to output human-readable address.
        :return: Human-readable address
        """
        return self.pat._address

    @property
    def zip_code(self):
        return self.pat._zip_code

    @property
    def building(self):
        return self.pat._building

    @property
    def coord(self):
        return self.pat.coord

    @property
    def plus_code(self):
        return self.pat._plus_code

    @property
    def exp_date(self):
        return str(self._exp_date.strftime("%d/%m/%Y"))

    @exp_date.setter
    def exp_date(self, value):
        """Checks values of expected date before assigning"""
        if not value:
            self._exp_date = None

        else:
            date = validate.valid_date(value)

            if isinstance(date, Exception):
                raise ValueError("Please enter a valid date in the format DD/MM/YYYY.\n")

            elif date.date() < date.today().date():
                raise ValueError("Date cannot be before today.\n")

            else:
                self._exp_date = date

    @property
    def time_earliest(self):
        return str(self._time_earliest.strftime("%H%M"))

    @time_earliest.setter
    def time_earliest(self, value):
        """Checks values of time window start before assigning"""
        if not value:
            self._time_earliest = None

        else:
            time = validate.valid_time(value)

            if not isinstance(time, Exception):
                self._time_earliest = time

            else:
                raise ValueError("Please enter a valid time in the format HHMM.\n")

    @property
    def time_latest(self):
        return str(self._time_latest.strftime("%H%M"))

    @time_latest.setter
    def time_latest(self, value):
        """Checks values of time window end before assigning"""
        # TODO: Figure out how to handle the midnight instance in time window and scheduling (try using instants)
        if not value:
            self._time_latest = None

        else:
            time = validate.valid_time(value)

            if not isinstance(time, Exception):
                # If there is no start time window (unlikely), allow end time window to be set.
                if not self.time_earliest:
                    self._time_latest = time

                # If there is a start time window and it is before the start time, allow it to be set.
                if self.time_earliest and time > self._time_earliest:
                    self._time_latest = time

                else:
                    raise ValueError("End time cannot be before start time.")
            else:
                raise ValueError("Please enter a valid time in the format HHMM.\n")

    @property
    def visit_complexity(self):
        try:
            return self._visit_complexity.capitalize()

        except AttributeError:
            return None

    @visit_complexity.setter
    def visit_complexity(self, value):
        complexity = validate.valid_cat_list(value, self._c_visit_complexity)

        if complexity:
            self._visit_complexity = complexity

        else:
            raise ValueError(f"{value.capitalize()} is not a valid visit complexity.")

    @property
    def visit_priority(self):
        try:
            return self._visit_priority.capitalize()

        except AttributeError:
            return None

    @visit_priority.setter
    def visit_priority(self, value):
        priority = validate.valid_cat_list(value, self._c_visit_priority)

        if priority:
            self._visit_priority = priority

        else:
            raise ValueError(f"{value.capitalize()} is not a valid visit priority.")

    @property
    def skill_list(self):
        try:
            return ", ".join(self._skill_list).capitalize()

        except TypeError:
            return None

    @skill_list.setter
    def skill_list(self, value: list):
        if not value:
            self._skill_list = None

        else:
            skill_list = []

            # Confirm data type of passed in value. Make sure it can handle both strings and lists
            if isinstance(value, str):
                value = value.replace("\n", ", ").split(", ")

            for skill in value:
                skill = validate.valid_cat_list(skill, self._c_skill_list)

                if skill:
                    skill_list.append(skill)

                else:
                    raise ValueError(f"{skill.capitalize()} is not a valid skill.")

            self._skill_list = skill_list

    @property
    def discipline(self):
        return self._discipline.capitalize()

    @discipline.setter
    def discipline(self, value):
        if not value:
            self._discipline = "any"

        else:
            discipline = validate.valid_cat_list(value, self._c_discipline)

            if discipline:
                self._discipline = discipline

            else:
                raise ValueError(f"{value.capitalize()} is not a valid discipline.")

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

    def update_self(self):
        """Allows the user to update visit information, including date/time window or address.
            Returns 0 on successful update."""
        navigation.clear()
        print(f"ID: {self.id}".ljust(10), f"Name: {self.name}\n".rjust(10))

        while True:
            selection = validate.qu_input("What would you like to do:\n"
                                          "     1. Modify Visit Date and Time\n"
                                          "     2. Assign Visit\n"
                                          "     3. Modify Skills\n"
                                          "     4. Modify Discipline\n"
                                          "     5. Modify Priority and Complexity\n"
                                          "     6. Inactivate Record\n"
                                          "\n"
                                          "Selection: ")

            if not selection:
                return 0

            # Update request date and time
            elif selection == "1":
                with self.session_scope():
                    self.update_date_time()

            elif selection == "2":
                with self.session_scope():
                    self.manual_assign_visit()

            elif selection == "3":
                with self.session_scope():
                    self.modify_skills()

            elif selection == "4":
                with self.session_scope():
                    self.modify_discipline()

            elif selection == "5":
                with self.session_scope():
                    self.modify_priority_complexity()

            elif selection == "6":
                with self.session_scope():
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
            self.refresh_self(self.session)
            return 0

        # Save old date for searching and updating instances_by_date index
        old_date = self._exp_date

        detail_dict = {
            "Expected Date": self.exp_date,
            "Time Window": f"{self.time_earliest} - {self.time_latest}"
        }

        # If user does not confirm info, changes will be reverted.
        if not validate.confirm_info(self, detail_dict):
            self.refresh_self(self.session)
            return 0

        # Save and update instance lists
        self.write_obj(self.session)

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
        clin = classes.person.Clinician.get_obj(self.session)

        if not clin:
            return 0

        # Assign clinician to visit. This will also assign the visit to the clinician.
        self._clin_id = clin.id
        self._sched_status = self._c_sched_status[1]

        # Write changes to file
        self.write_obj(self.session)
        return 1

    def unassign_visit(self):
        """
        Assigns the visit to a clinician.
        :return: 1 if successful
        """
        # If linked clinician fails to load, refresh and cancel action.
        if not self._clin_id:
            print("This patient does not have an assigned clinician.")
            return 0

        self._clin_id = ""
        self.write_obj(self.session)

        return 1

    def show_visit_details(self):
        """
        Displays details of current visit, including patient, clinician, and status.
        :return: 1 if successful
        """
        # Output linked visit details
        detail_dict = {
            "Visit ID": self.id,
            "Patient": self.pat._name,
            "Clinician": self.clin._name,
            "Visit Address": self.address,
            "Expected Date": self.exp_date,
            "Time Window": f"{self.time_earliest} - {self.time_latest}"
        }

        for k, v in detail_dict.items():
            print(f"{k}: {v}")

        print("\n")

    def modify_skills(self):
        """
        Updates visit skill requirements list based on clinical registration. Used for validation to drive scheduling for
        patients based on their needs.
        :return: 1 if successful
        """

        attr_list = [
            {
                "term": f"Skill Requirement. Previous: {self.skill_list if self.skill_list else 'None'}",
                "attr": "skill_list",
                "cat_list": self._c_skill_list,
                "multiselect": True
            }
        ]

        # Update all attributes from above. Quit if user quits during any attribute
        if not validate.get_info(self, attr_list):
            self.refresh_self(self.session)
            return 0

        detail_dict = {
            "Skill Requirements": self.skill_list,
        }

        # If user does not confirm info, changes will be reverted.
        if not validate.confirm_info(self, detail_dict):
            self.refresh_self(self.session)
            return 0

        self.write_obj(self.session)
        return 1

    def modify_discipline(self):
        """
        Updates clinician discipline.
        :return: 1 if successful
        """
        attr_list = [
            {
                "term": f"Discipline. Previous: {self.discipline if self.discipline else 'None'}",
                "attr": "discipline",
                "cat_list": self._c_discipline
            },
        ]

        # Update all attributes from above. Quit if user quits during any attribute
        if not validate.get_info(self, attr_list):
            self.refresh_self(self.session)
            return 0

        detail_dict = {
            "Discipline": self.discipline,
        }

        # If user does not confirm info, changes will be reverted.
        if not validate.confirm_info(self, detail_dict):
            self.refresh_self(self.session)
            return 0

        self.write_obj(self.session)
        return 1

    def modify_priority_complexity(self):
        """
        Updates priority and complexity of a visit. Writes updates to file.
        :return: 1 if successful.
        """
        attr_list = [
            {
                "term": f"Priority. Previous: {self.visit_priority if self.visit_priority else 'None'}",
                "attr": "visit_priority",
                "cat_list": self._c_visit_priority
            },
            {
                "term": f"Complexity. Previous: {self.visit_complexity if self.visit_complexity else 'None'}",
                "attr": "visit_complexity",
                "cat_list": self._c_visit_complexity
            }
        ]

        # Update all attributes from above. Quit if user quits during any attribute
        if not validate.get_info(self, attr_list):
            self.refresh_self(self.session)
            return 0

        detail_dict = {
            "Visit Priority": self.visit_priority,
            "Visit Complexity": self.visit_complexity
        }

        # If user does not confirm info, changes will be reverted.
        if not validate.confirm_info(self, detail_dict):
            self.refresh_self(self.session)
            return 0

        # Save and update instance lists
        self.write_obj(self.session)
        return 1

    @classmethod
    def create_self(cls, session, pat_id=""):
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
            pat = classes.person.Patient.load_obj(session, pat_id)

        else:
            print("Please select a patient to create a visit request.")
            pat = classes.person.Patient.get_obj(session)

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
            "Patient": pat.name,
            "Visit ID": obj.id,
            "Visit Address": pat.address,
            "Expected Date": obj.exp_date,
            "Time Window": f"{obj.time_earliest} - {obj.time_latest}"
        }

        # If user confirms information is correct, a new object is created and written to database
        if not validate.confirm_info(obj, detail_dict):
            print("Record not created.")
            return 0

        obj.write_obj(session)

        return 1

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
                self.refresh_self(self.session)
                return 0

            prompt = "Are you sure you want to cancel this request? You will be unable to schedule this request. "
            if not validate.yes_or_no(prompt):
                self.refresh_self(self.session)
                return 0

            self.status = 0

            # Cancel visit
            self.write_obj(self.session)
            print("Visit successfully cancelled.")

            return 1

    @classmethod
    def evaluate_requests(cls):
        """Evaluates all Visits and marks them as no shows if they are past their expected date"""
        with cls.class_session_scope() as session:
            for visit in session.query(Visit).distinct().all():
                # Evaluate date against current date and mark as expired if due before current date
                if datetime.strptime(visit.exp_date, '%d-%m-%Y').date() < date.today():
                    visit.status = 0
                    visit.cancel_reason = cls._c_cancel_reason[3]

                    visit.write_obj(session)

    # TODO: Add a class method to reactivate a record
    # TODO: Add a method to find all visits today without a clinician
