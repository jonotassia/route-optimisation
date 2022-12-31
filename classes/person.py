# This file contains classes to be used in the route optimisation tool.
import itertools
import geolocation
import navigation
import validate
import classes
from data_manager import DataManagerMixin
from sqlalchemy import Column, String, Date, Time, Integer, PickleType, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.mutable import MutableList, MutableDict
from time import sleep


# TODO: Determine best way to generate Visits that are not tied to a date, but relative to days of week


class Human(DataManagerMixin):
    _c_sex_options = ("male", "female", "not specified")

    def __init__(self, status=1, name="", dob="", sex="", address="{}", **kwargs):
        """Initiates a human objects with the following attributes:
        id, first name, last name, middle name, date of birth, sex, and address."""
        super().__init__()

        self._status = status
        self.name = name
        self.dob = dob
        self.sex = sex
        self.address = address

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        """Checks values of sex before assigning"""
        try:
            if value == 1 or value == 0:
                self._status = value

            else:
                raise ValueError("Status can only be 0 or 1.")

        except ValueError as err:
            print(err)

    @property
    def name(self):
        # Parse middle name to confirm it exists, else return None
        return self._name

    @name.setter
    def name(self, value):
        if not value:
            self._name = None
            self._last_name = None
            self._first_name = None
            self._middle_name = None

        else:
            name = validate.valid_name(value)

            if not isinstance(name, Exception):
                self._last_name = name[0]
                self._first_name = name[1]

                try:
                    self._middle_name = name[2]

                except TypeError:
                    self._middle_name = None

                self._name = f"{self._last_name}, {self._first_name} {self._middle_name}"

            else:
                raise ValueError("Please provide a valid name in the format LAST, FIRST MIDDLE")

    @property
    def dob(self):
        return self._dob.strftime("%d/%m/%Y")

    @dob.setter
    def dob(self, value):
        """Checks values of date of birth before assigning"""
        if not value:
            self._dob = None

        else:
            dob = validate.valid_date(value)

            if not isinstance(dob, Exception):
                self._dob = dob

            else:
                raise ValueError("Please enter a valid date in the format DD/MM/YYYY.\n")

    @property
    def sex(self):
        return self._sex

    @sex.setter
    def sex(self, value):
        """Checks values of sex before assigning"""
        if not value:
            self._sex = None

        else:
            sex = validate.valid_cat_list(value, self._c_sex_options)

            if not isinstance(sex, Exception):
                self._sex = sex

            else:
                raise ValueError(f"Invalid selection. Value not in {self._c_sex_options}")

    @property
    def address(self):
        """
        Displays an address parsed using USAddress. Loops through values in dictionary to output human-readable address.
        :return: Human-readable address
        """
        return self._address

    @address.setter
    def address(self, value):
        """Checks values of address before assigning"""
        if not value:
            self._address = None

        else:
            address = validate.valid_address(value)

            if not isinstance(address, Exception):
                self._address = address["address"]
                self._lat = address["coord"][0]
                self._lng = address["coord"][1]
                self._zip_code = address["zip_code"]
                try:
                    self._building = address["building"]
                except KeyError:
                    self._building = None
                try:
                    self._plus_code = address["plus_code"]
                except KeyError:
                    self._plus_code = self._address

            else:
                raise ValueError("Please enter a complete and valid address.\n")

    @property
    def coord(self):
        return self._lat, self._lng

    @classmethod
    def create_self(cls, session):
        """
        Loops through each detail and assigns to the object.
        If any response is blank, the user will be prompted to quit or continue.
        If they continue, they will begin at the element that the quit out of
        Once details are completed, the user is prompted to review information and complete creation.
        :param session: Session for querying database
        :return:
            1 if the user completes initialization
            0 if the user does not
        """
        obj = cls()

        attr_list = [
            {
                "term": "Name (LAST, FIRST MIDDLE)",
                "attr": "name"
            },
            {
                "term": "Date of Birth",
                "attr": "dob"
            },
            {
                "term": "Sex",
                "attr": "sex",
                "cat_list": obj._c_sex_options
            },
            {
                "term": "Address",
                "attr": "address"
            }
        ]

        # Update all attributes from above. Quit if user quits during any attribute
        if not validate.get_info(obj, attr_list):
            return 0

        detail_dict = {
            "ID": obj.id,
            "Name": obj.name,
            "Date of Birth": obj.dob,
            "Sex": obj.sex,
            "Address": obj.address
        }

        # If user confirms information is correct, a new object is created and written
        if not validate.confirm_info(obj, detail_dict):
            print("Record not created.")
            session.rollback()
            return 0

        obj.write_obj(session)
        return obj

    def modify_visits(self):
        """
        Searches database for linked visits and displays key information, including:
            scheduling_status
            date
            time
            address
        Prompts user to update visit details.
        :return: 1 if successful
        """
        # TODO: Hide inactive visits
        # Prompt user for date to view visits
        while True:
            inp_date = validate.qu_input("Please select a date to view visits: ")

            if not inp_date:
                return 0

            try:
                val_date = validate.valid_date(inp_date).date()

            except AttributeError:
                print("Invalid date format.")
                continue

            if val_date:
                break

        try:
            visits_by_date = [visit for visit in self.visits if visit._exp_date == val_date]

        except KeyError:
            print("There are no visits assigned on this date. Returning...")
            sleep(1.5)
            return 0

        # Initialize all visits and add to list for display
        visit_list = []

        if not visits_by_date:
            print("There are no visits assigned on this date. Returning...")
            sleep(1.5)
            return 0

        # Display list of requests linked to patient.
        for count, visit in enumerate(visits_by_date):
            print(f"{count + 1}) Visit ID: {visit.id}"
                  f"    Patient: {visit.pat._name}"
                  f"    Scheduling Status: {visit.sched_status.capitalize()}"
                  f"    Expected Date: {visit.exp_date}"
                  f"    Time Window: {visit.time_earliest} - {visit.time_latest}")

        # Validate that user input ID of a linked visit, then open visit for modification.
        while True:
            selection = validate.qu_input("Which visit would you like to modify? ")

            if not selection:
                return 0

            # Raise error if not in list
            try:
                selection = int(selection)

            except TypeError:
                print("Invalid selection.")
                continue

            if 0 < selection < len(visits_by_date):
                visit = visits_by_date[selection]
                visit.update_self()
                return 1

            else:
                print("Invalid selection")

    def assign_team(self):
        """
        Assigns the clinician or patient to a team so that they can be considered in that team's route calculation
        """
        # Allow user to select team either by name or id, then load to an object
        print(f"Select a team to add to this {self.__class__.__name__}. "
              f"Current: {self.team._name if self.team._name else 'None'}")

        team = classes.team.Team.get_obj(self.session)

        if not team:
            sleep(1)
            return 0

        # Add team to clinician
        self.team_id = team.id

        detail_dict = {
            "Team ID": self.team.id,
            "Team Name": self.team._name
        }

        # If user does not confirm info, changes will be reverted.
        if not validate.confirm_info(self, detail_dict):
            self.refresh_self(self.session)
            return 0

        self.write_obj(self.session)
        return 1

    # TODO: Add a class method to reactivate a record


class Patient(Human, DataManagerMixin.Base):
    # Initialise table details
    __tablename__ = "Patient"
    _id = Column(Integer, primary_key=True, unique=True)
    _name = Column(String)
    _last_name = Column(String)
    _first_name = Column(String)
    _middle_name = Column(String)
    _status = Column(String, nullable=True)
    _dob = Column(Date)
    _sex = Column(String)
    _address = Column(String, nullable=True)
    _zip_code = Column(String, nullable=True)
    _building = Column(String, nullable=True)
    _lat = Column(Integer, nullable=True)
    _lng = Column(Integer, nullable=True)
    _plus_code = Column(String, nullable=True)
    _team_id = Column(Integer, ForeignKey("Team._id"), nullable=True)
    team = relationship("Team", back_populates="pats")
    visits = relationship("Visit", back_populates="pat")
    _death_date = Column(Date, nullable=True)
    _death_time = Column(Time, nullable=True)
    _inactive_reason = Column(String, nullable=True)

    _id_iter = itertools.count(10000)  # Create a counter to assign new value each time a new obj is created
    _c_inactive_reason = ("no longer under care", "expired", "added in error")

    def __init__(self, id=None, status=1, name="", dob="", sex="", address="", team="", **kwargs):
        """
        Initiates and writes-to-file a patient with the following attributes:
        id, first name, last name, middle name, date of birth, sex, and address.
        Additionally, initializes a list of Visits linked to the patient
        """
        # Inherit from top level class
        super().__init__(status, name, dob, sex, address)

        self._id = id if id else next(Patient._id_iter)
        self.team_id = team
        self._death_date = None
        self._death_time = None
        self._inactive_reason = None

        # Update all attributes from passed dict if provided
        self.__dict__.update(kwargs)

    @property
    def id(self):
        return self._id

    @property
    def inactive_reason(self):
        return self._inactive_reason

    @inactive_reason.setter
    def inactive_reason(self, value):
        """Checks values of inactive reason before assigning"""
        if not value:
            self._inactive_reason = None

        else:
            reason = validate.valid_cat_list(value, self._c_inactive_reason)

            if reason:
                self._inactive_reason = reason

            else:
                raise ValueError(f"Invalid selection. Value not in {self._c_inactive_reason}")

    @property
    def death_date(self):
        return self._death_date.date().strftime("%d/%m/%Y")

    @death_date.setter
    def death_date(self, value):
        """Checks values of date of death before assigning"""
        if not value:
            self._death_date = None

        else:
            date = validate.valid_date(value)

            if date:
                self._death_date = date

            else:
                raise ValueError("Please enter a valid date in the format DD/MM/YYYY.\n")

    @property
    def death_time(self):
        return self._death_time.strftime("%H%M")

    @death_time.setter
    def death_time(self, value):
        """Checks values of date of time before assigning"""
        if not value:
            self._death_time = None

        else:
            time = validate.valid_time(value)

            if time:
                self._death_time = time

            else:
                raise ValueError("Please enter a valid time in the format HHMM.\n")

    @property
    def team_id(self):
        return self._team_id

    @team_id.setter
    def team_id(self, value):
        """
        ID of linked team.
        """
        if not value:
            self._team_id = None

        else:
            if classes.team.Team.load_obj(self.session, value):
                self._team_id = value

            else:
                raise ValueError("This is not a valid team ID.\n")

    def update_self(self):
        """
        Groups all update methods for user selection. This will be called when modifying record in navigation.py
        """
        navigation.clear()
        while True:
            print(f"ID: {self.id} Name: {self.name}\n")

            selection = validate.qu_input("What would you like to do:\n"
                                          "     1. View or Modify Pending/Scheduled Visits\n"
                                          "     2. Create Visit\n"
                                          "     3. Modify Address\n"
                                          "     4. Modify Visit Preferences\n"
                                          "     5. Assign Team\n"
                                          "     6. Inactivate Record\n"
                                          "\n"
                                          "Selection: "
                                          )

            if not selection:
                return 0

            elif selection == "1":
                with self.session_scope():
                    self.modify_visits()

            # Generate a new visit
            elif selection == "2":
                with self.session_scope():
                    classes.visits.Visit.create_self(self.session, pat_id=self.id)

            # Update address
            elif selection == "3":
                with self.session_scope():
                    self.update_address()

            # Update preferences, including skill requirements, gender, and times
            elif selection == "4":
                with self.session_scope():
                    self.update_skill_pref()

            # Assign responsible team to patient
            elif selection == "5":
                with self.session_scope():
                    self.assign_team()

            # Inactivate patient
            elif selection == "6":
                with self.session_scope():
                    self.inactivate_self()
                return 0

            else:
                print("Invalid selection.")

    def update_address(self):
        """
        Updates address for the request.
        :return: 1 if successful.
        """
        attr_list = [
            {
                "term": f"\nPrevious Address: {self.address if self.address else 'None'}. \nAddress",
                "attr": "address"
            }
        ]

        # Update all attributes from above. Quit if user quits during any attribute
        if not validate.get_info(self, attr_list):
            self.refresh_self(self.session)
            return 0

        detail_dict = {
            "Address": self.address
        }

        # If user does not confirm info, changes will be reverted.
        if not validate.confirm_info(self, detail_dict):
            self.refresh_self(self.session)
            return 0

        self.write_obj(self.session)
        return 1

    def update_skill_pref(self):
        """Updates the patient's visit preferences"""
        # TODO: Define list of preferences required for patient per instance. This should be inherited by visit.
        pass

    def inactivate_self(self):
        """
        This method sets the status of a patient to inactive.
        Prompts the user for an inactive reason from c_inactive_reason and files back to self.inactive_reason.
        If expired is selected, user will be prompted for a date and time of death.
        The user will be prompted if the patient has visits associated with them.
        If so, they will be prompted to either quit or cancel all visits.
        """
        # Checks if request is already inactive.
        if self.status == 0:
            print("This record is already inactive.")
            return 0

        # Checks if the patient has active visits associated with them and prompt user to cancel or quit.
        if self.visits:
            prompt = """This patient has active appointments. 
                        Proceeding will cancel all requests. 
                        Are you sure you want to continue?"""

            if not validate.yes_or_no(prompt):
                return 0

        attr_list = [
            {
                "term": "Inactivation Reason: ",
                "attr": "inactive_reason",
                "cat_list": self._c_inactive_reason
            }
        ]

        if not validate.get_info(self, attr_list):
            self.refresh_self(self.session)
            return 0

        # If reason is death, request death date and time, but don't assign until user confirms inactivation.
        if self.inactive_reason == self._c_inactive_reason[1]:
            print("Please enter a death date and time.\n")

            attr_list = [
                {
                    "term": "Death Date: ",
                    "attr": "death_date"
                },
                {
                    "term": "Death Time",
                    "attr": "death_time"
                }
            ]

            # Update all attributes from above. Quit if user quits during any attribute
            if not validate.get_info(self, attr_list):
                self.refresh_self(self.session)
                return 0

        prompt = "Are you sure you want to inactivate this record?"
        if validate.yes_or_no(prompt):
            self.status = 0
            # Cancel linked visit requests with a reason of system action. This occurs here rather than above to
            # give user the opportunity to back out changes before cancelling visits.
            if self.visits:
                try:
                    for visit in self.visits:
                        # If any linked visits fail to load, refresh and cancel action.
                        if not visit:
                            print("Unable to load linked visits.")
                            self.refresh_self(self.session)
                            return 0

                        visit.pat_id = None
                        visit.status = 0
                        visit.cancel_reason = visit._c_cancel_reason[4]

                except AttributeError:
                    print("Unable to load linked visits.")

            # Remove from team
            self.team_id = None

            self.write_obj(self.session)
            print("Record successfully inactivated.")

            return 1

        else:
            self.refresh_self(self.session)
            return 0


class Clinician(Human, DataManagerMixin.Base):
    # Initialise table details
    __tablename__ = "Clinician"
    _id = Column(Integer, primary_key=True, unique=True)
    _name = Column(String)
    _last_name = Column(String)
    _first_name = Column(String)
    _middle_name = Column(String)
    _status = Column(String, nullable=True)
    _dob = Column(Date)
    _sex = Column(String)
    _address = Column(String, nullable=True)
    _zip_code = Column(String, nullable=True)
    _building = Column(String, nullable=True)
    _lat = Column(Integer, nullable=True)
    _lng = Column(Integer, nullable=True)
    _plus_code = Column(String, nullable=True)
    _start_address = Column(String, nullable=True)
    _start_zip_code = Column(String, nullable=True)
    _start_building = Column(String, nullable=True)
    _start_lat = Column(Integer, nullable=True)
    _start_lng = Column(Integer, nullable=True)
    _start_plus_code = Column(String, nullable=True)
    _end_address = Column(String, nullable=True)
    _end_zip_code = Column(String, nullable=True)
    _end_building = Column(String, nullable=True)
    _end_lat = Column(Integer, nullable=True)
    _end_lng = Column(Integer, nullable=True)
    _end_plus_code = Column(String, nullable=True)
    _start_time = Column(Time)
    _end_time = Column(Time)
    _team_id = Column(Integer, ForeignKey("Team._id"), nullable=True)
    team = relationship("Team", back_populates="clins")
    _discipline = Column(String, nullable=True)
    _skill_list = Column(MutableList.as_mutable(PickleType), nullable=True)
    visits = relationship("Visit", back_populates="clin")
    _inactive_reason = Column(String, nullable=True)

    # Class Attributes
    _id_iter = itertools.count(10000)  # Create a counter to assign new value each time a new obj is created
    _c_inactive_reason = ("no longer works here", "switched roles", "added in error")
    _c_skill_list = ("med administration", "specimen collection", "domestic tasks", "physical assessment")
    _c_discipline = ("doctor", "nurse", "physical therapist", "occupational Therapist", "medical assistant")

    def __init__(self, id=None, status=1, name="", dob="", sex="", address="",
                 team="", start_time="800", end_time="1700", discipline=None,
                 skill_list=[], **kwargs):
        """Initiates and writes-to-file a clinician with the following attributes:
        id, first name, last name, middle name, date of birth, sex, and address
        Assumes standard shift time for start and end time, and inherits address for start/end address.
        These will be updated by a different function called update_start_end"""
        # Inherit from superclass
        super().__init__(status, name, dob, sex, address)

        self._id = id if id else next(Clinician._id_iter)
        self.start_address = address
        self.end_address = address
        self.start_time = start_time
        self.end_time = end_time
        self.team_id = team
        self.discipline = discipline
        self.skill_list = skill_list
        self._inactive_reason = None

        # Update all attributes from passed dict if provided
        self.__dict__.update(kwargs)

    @property
    def id(self):
        return self._id

    @property
    def start_address(self):
        """
        Displays an address parsed using USAddress. Loops through values in dictionary to output human-readable address.
        :return: Human-readable address
        """
        try:
            return self._start_address
        except AttributeError:
            return self.address

    @start_address.setter
    def start_address(self, value):
        """Checks values of address before assigning"""
        if not value:
            self._start_address = None

        else:
            address = validate.valid_address(value)

            if not isinstance(address, Exception):
                self._start_address = address["address"]
                self._start_lat = address["coord"][0]
                self._start_lng = address["coord"][1]
                self._start_zip_code = address["zip_code"]
                try:
                    self._start_building = address["building"]
                except KeyError:
                    self._start_building = None
                try:
                    self._start_plus_code = address["plus_code"]
                except KeyError:
                    self._start_plus_code = self._start_address

            else:
                raise ValueError("Please enter a complete and valid address.\n")

    @property
    def start_coord(self):
        return self._start_lat, self._start_lng

    @property
    def end_address(self):
        """
        Displays an address parsed using USAddress.
        :return: Human-readable address
        """
        try:
            return self._end_address
        except AttributeError:
            return self.address

    @end_address.setter
    def end_address(self, value):
        """Checks values of address before assigning"""
        if not value:
            self._end_address = None

        else:
            address = validate.valid_address(value)

            if not isinstance(address, Exception):
                self._end_address = address["address"]
                self._end_lat = address["coord"][0]
                self._end_lng = address["coord"][1]
                self._end_zip_code = address["zip_code"]
                try:
                    self._end_building = address["building"]
                except KeyError:
                    self._end_building = None
                try:
                    self._end_plus_code = address["plus_code"]
                except KeyError:
                    self._end_plus_code = self._end_address

            else:
                raise ValueError("Please enter a complete and valid address.\n")

    @property
    def end_coord(self):
        return self._end_lat, self._end_lng

    @property
    def start_time(self):
        return self._start_time.strftime("%H%M")

    @start_time.setter
    def start_time(self, value):
        """Checks values of start time before assigning"""
        if not value:
            self._start_time = None

        else:
            time = validate.valid_time(value)

            if time:
                self._start_time = time

            else:
                raise ValueError("Please enter a valid time in the format HHMM.\n")

    @property
    def end_time(self):
        return self._end_time.strftime("%H%M")

    @end_time.setter
    def end_time(self, value):
        """Checks values of end time before assigning"""
        if not value:
            self._end_time = None

        else:
            time = validate.valid_time(value)

            if time:
                self._end_time = time

            else:
                raise ValueError("Please enter a valid time in the format HHMM.\n")

    @property
    def team_id(self):
        return self._team_id

    @team_id.setter
    def team_id(self, value):
        """
        ID of linked team.
        """
        if not value:
            self._team_id = None

        else:
            if classes.team.Team.load_obj(self.session, value):
                self._team_id = value

            else:
                raise ValueError("This is not a valid team ID.\n")

    @property
    def team_name(self):
        if self.team_id:
            return classes.team.Team.load_obj(self.session, self.team_id).name

        else:
            return None

    @property
    def capacity(self):
        """
        Maximum weight of visits a clinician can undertake. This is based on the assumption that in an 8 hour day,
        a clinician can complete a maximum of 5 complex visits (weight 3). Therefore, an 8 hour day has capacity 15.
        """
        shift_lng = (self._end_time.hour - self._start_time.hour) * 60 + self._end_time.minute - self._start_time.minute
        return int(shift_lng / 32)

    @property
    def discipline(self):
        return self._discipline.capitalize()

    @discipline.setter
    def discipline(self, value):
        if not value:
            self._discipline = "none"

        else:
            discipline = validate.valid_cat_list(value, self._c_discipline)

            if discipline:
                self._discipline = discipline

            else:
                raise ValueError(f"{value.capitalize()} is not a valid discipline.")

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
    def inactive_reason(self):
        return self._inactive_reason

    @inactive_reason.setter
    def inactive_reason(self, value):
        """Checks values of inactive reason before assigning"""
        if not value:
            self._inactive_reason = None

        else:
            reason = validate.valid_cat_list(value, self._c_inactive_reason)

            if reason:
                self._inactive_reason = reason

            else:
                raise ValueError(f"Invalid selection. Value not in {self._c_inactive_reason}")

    def update_self(self):
        """
        Groups all update methods for user selection. This will be called when modifying record in navigation.py
        """
        navigation.clear()
        while True:
            print(f"ID: {self.id}".ljust(10), f"Name: {self.name}\n".rjust(10))

            selection = validate.qu_input("What would you like to do:\n"
                                          "     1. View/Modify Scheduled Visit\n"
                                          "     2. Update Start/End Times and Addresses\n"
                                          "     3. Modify Personal Address\n"
                                          "     4. Modify Discipline\n"
                                          "     5. Modify Skills\n"
                                          "     6. Assign Team\n"
                                          "     7. Optimize Route\n"
                                          "     8. Display Route\n"
                                          "     9. Inactivate Record\n"
                                          "\n"
                                          "Selection: ")

            if not selection:
                return 0

            # View/modify scheduled visits
            elif selection == "1":
                with self.session_scope():
                    self.modify_visits()

            # Update start/end time and address
            elif selection == "2":
                with self.session_scope():
                    self.update_start_end()

            # Update address
            elif selection == "3":
                with self.session_scope():
                    self.update_address()

            # Modify discipline
            elif selection == "4":
                with self.session_scope():
                    self.modify_discipline()

            # Modify clinical skills
            elif selection == "5":
                with self.session_scope():
                    self.modify_skills()

            # Assign team
            elif selection == "6":
                with self.session_scope():
                    self.assign_team()

            # Optimize route
            elif selection == "7":
                self.optimize_route()

            # display route
            elif selection == "8":
                self.display_route()

            # Inactivate record
            elif selection == "9":
                with self.session_scope():
                    self.inactivate_self()
                    return 0

            else:
                print("Invalid selection.")

    def update_start_end(self):
        """Sets the starting and ending time/geocoded address for the clinician
            Updates self.start_time, self.start_address, self.end_time, and self.end_address. Writes updates to file.
            Returns 0 on successful update."""

        attr_list = [
            {
                "term": f"Start Time (HHMM). Previous: {self.start_time if self.start_time else 'None'}",
                "attr": "start_time"
            },
            {
                "term": f"Start Address. Previous: {self.start_address if self.start_address else 'None'}",
                "attr": "start_address"
            },
            {
                "term": f"End Time (HHMM). Previous: {self.end_time if self.end_time else 'None'}",
                "attr": "end_time"
            },
            {
                "term": f"End Address. Previous: {self.end_address if self.end_address else 'None'}",
                "attr": "end_address"
            }
        ]

        # Update all attributes from above. Quit if user quits during any attribute
        if not validate.get_info(self, attr_list):
            self.refresh_self(self.session)
            return 0

        detail_dict = {
            "Start Time": self.start_time,
            "Start Address": self.start_address,
            "End Time": self.end_time,
            "End Address": self.end_address
        }

        # If user does not confirm info, changes will be reverted.
        if not validate.confirm_info(self, detail_dict):
            self.refresh_self(self.session)
            return 0

        self.write_obj(self.session)

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
            self.refresh_self(self.session)
            return 0

        detail_dict = {
            "Address": self.address
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
                "cat_list": self._c_discipline,
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

    def modify_skills(self):
        """
        Updates clinician skills list based on clinical registration. Used for validation to drive scheduling for
        patients based on their needs.
        :return: 1 if successful
        """

        attr_list = [
            {
                "term": f"Skill Proficiency. Previous: {self.skill_list if self.skill_list else 'None'}",
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
            "Skill Proficiencies": self.skill_list,
        }

        # If user does not confirm info, changes will be reverted.
        if not validate.confirm_info(self, detail_dict):
            self.refresh_self(self.session)
            return 0

        self.write_obj(self.session)
        return 1

    def optimize_route(self):
        """
        Calculates the estimated trip route for the clinician.
        """
        geolocation.optimize_route(self)

    def display_route(self):
        """
        Displays the route for the clinician.
        """
        geolocation.display_route(self)

    def assign_team(self):
        """
        Assigns the clinician or patient to a team so that they can be considered in that team's route calculation
        """
        # Allow user to select team either by name or id, then load to an object
        try:
            print(f"Select a team to add to this {self.__class__.__name__}. "
                  f"Current: {self.team._name}")

        except AttributeError:
            print(f"Select a team to add to this {self.__class__.__name__}. "
                  f"Current: None")

        team = classes.team.Team.get_obj(self.session)

        if not team:
            sleep(1)
            return 0

        # Add team to clinician
        self.team_id = team.id

        detail_dict = {
            "Team ID": team.id,
            "Team Name": team._name
        }

        # If user does not confirm info, changes will be reverted.
        if not validate.confirm_info(self, detail_dict):
            self.refresh_self(self.session)
            return 0

        self.write_obj(self.session)
        return 1

    def inactivate_self(self):
        """
        This method sets the status of a clinician to inactive.
        Prompts the user for an inactive reason from c_inactive_reason and files back to self.inactive_reason.
        """
        # Checks if request is already inactive.
        if self.status == 0:
            print("This record is already inactive.")
            return 0

        # Checks if the clinician has active visits associated with them and prompt user to cancel or quit.
        if self.visits:
            prompt = """This clinician has assigned visits. 
                        Proceeding will remove the clinician from all requests. 
                        Are you sure you want to continue?"""

            if not validate.yes_or_no(prompt):
                return 0

        attr_list = [
            {
                "term": "Inactivation Reason: ",
                "attr": "inactive_reason",
                "cat_list": self._c_inactive_reason
            }
        ]

        if not validate.get_info(self, attr_list):
            self.refresh_self(self.session)
            return 0

        prompt = "Are you sure you want to inactivate this record?"
        if validate.yes_or_no(prompt):
            self.status = 0

            try:
                for visit in self.visits:
                    # If any linked visits fail to load, refresh and cancel action.
                    if not visit:
                        print("Unable to load linked visits.")
                        self.refresh_self(self.session)
                        return 0

                    visit.clin_id = None

            except AttributeError:
                print("Unable to load linked visits.")

            self.team_id = None
            self.write_obj(self.session)
            print("Record successfully inactivated.")

            return 1
