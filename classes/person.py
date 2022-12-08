# This file contains classes to be used in the route optimisation tool.
import itertools

import geolocation
import navigation
import validate
import in_out
import classes
import datetime
from time import sleep

# TODO: Determine best way to generate Visits that are not tied to a date, but relative to days of week


class Human:
    _id_iter = itertools.count(10000)  # Create a counter to assign new value each time a new obj is created
    _tracked_instances = {}
    _c_sex_options = ("male", "female", "not specified")

    def __init__(self, status=1, name="", dob="", sex="", address="{}", team="", **kwargs):
        """Initiates a human objects with the following attributes:
        id, first name, last name, middle name, date of birth, sex, and address."""
        self._placekey = None
        self._id = next(self._id_iter)
        self._status = status
        self.name = name
        self.dob = dob
        self.sex = sex
        self.address = address
        self._team_id = team
        self._team_name = None

    @property
    def id(self):
        return self._id

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
        try:
            middle_name = self._name[2]

        except TypeError:
            middle_name = None

        name = f"{self._name[0]}, {self._name[1]} {middle_name}"
        return name

    @name.setter
    def name(self, value):
        name = validate.valid_name(value)

        if not isinstance(name, Exception):
            self._name = name

        else:
            raise ValueError("Please provide a valid name in the format LAST, FIRST MIDDLE")

    @property
    def last_name(self):
        return self._name[0]

    @property
    def first_name(self):
        return self._name[1]

    @property
    def middle_name(self):
        return self._name[2]

    @property
    def dob(self):
        return self._dob.strftime("%d/%m/%Y")

    @dob.setter
    def dob(self, value):
        """Checks values of date of birth before assigning"""
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
        return self._address["address"]

    @address.setter
    def address(self, value):
        """Checks values of address before assigning"""
        address = validate.valid_address(value)

        if not isinstance(address, Exception):
            self._address = address

        else:
            raise ValueError("Please enter a complete and valid address.\n")

    @property
    def zip_code(self):
        return self._address["zip_code"]

    @property
    def building(self):
        return self._address["building"]

    @property
    def coord(self):
        return self._address["coord"]

    @property
    def plus_code(self):
        return self._address["plus_code"]

    @property
    def team_id(self):
        return self._team_id

    @team_id.setter
    def team_id(self, value):
        """
        ID of linked team.
        """
        if value in classes.team.Team._tracked_instances:
            old_team_id = self._team_id

            # Inverse link team to person
            team = in_out.load_obj(classes.team.Team, f"./data/Team/{value}.pkl")

            if isinstance(self, Patient):
                team._pat_id.append(self.id)

                # Remove from old team
                if old_team_id:
                    old_team = in_out.load_obj(classes.team.Team, f"./data/Team/{old_team_id}.pkl")
                    old_team._pat_id.remove(self.id)

            if isinstance(self, Clinician):
                team._clin_id.append(self.id)

                # Remove from old team
                if old_team_id:
                    old_team = in_out.load_obj(classes.team.Team, f"./data/Team/{old_team_id}.pkl")
                    old_team._clin_id.remove(self.id)
                    old_team.write_self()

            team.write_self()

            self._team_id = value

        else:
            raise ValueError("This is not a valid team ID.\n")

    @team_id.deleter
    def team_id(self):
        # Load patient and create or add to the search by date list for visits
        team = in_out.load_obj(classes.team.Team, f"./data/Team/{self.team_id}.pkl")

        if isinstance(self, Patient):
            team._pat_id.remove(self.id)

        if isinstance(self, Clinician):
            team._clin_id.remove(self.id)

        team.write_self()

    @property
    def team_name(self):
        if self.team_id:
            return classes.team.Team._tracked_instances[self.team_id]["name"]

        else:
            return None

    def assign_team(self):
        """
        Assigns the clinician or patient to a team so that they can be considered in that team's route calculation
        """
        # Allow user to select team either by name or id, then load to an object
        print(f"Select a team to add to this {self.__class__.__name__}. Current: {self.team_name if self.team_name else 'None'}")

        team = in_out.get_obj(classes.team.Team)

        if not team:
            sleep(1)
            return 0

        # Add team to placeholder. Only add to clinician when confirmed
        team_id = team.id
        team_name = team._name

        detail_dict = {
            "Team ID": team_id,
            "Team Name": team_name
        }

        # If user does not confirm info, changes will be reverted.
        if not validate.confirm_info(self, detail_dict):
            self.refresh_self()
            return 0

        self.team_id = team_id
        self.write_self()
        return 1

    @classmethod
    def create_self(cls):
        """
        Loops through each detail and assigns to the object.
        If any response is blank, the user will be prompted to quit or continue.
        If they continue, they will begin at the element that the quit out of
        Once details are completed, the user is prompted to review information and complete creation.
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

        # If user confirms information is correct, a new object is created, written, and added to _tracked_instances
        if not validate.confirm_info(obj, detail_dict):
            print("Record not created.")
            return 0

        obj.write_self()
        return obj

    def write_self(self):
        """Writes the object to file as a .pkl using the pickle module"""
        if in_out.write_obj(self):
            return 1

    def refresh_self(self):
        """Refreshes an existing object from file in the in case users need to backout changes."""
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

    # TODO: Add a class method to reactivate a record


class Patient(Human):
    _id_iter = itertools.count(10000)  # Create a counter to assign new value each time a new obj is created
    _tracked_instances = {}
    _c_inactive_reason = ("no longer under care", "expired", "added in error")

    def __init__(self, status=1, name="", dob="", sex="", address="", team="", **kwargs):
        """
        Initiates and writes-to-file a patient with the following attributes:
        id, first name, last name, middle name, date of birth, sex, and address.
        Additionally, initializes a list of Visits linked to the patient
        """
        # Inherit from top level class
        super().__init__(status, name, dob, sex, address, team)

        self._id = next(self._id_iter)
        self._inactive_reason = None
        self.visits = {}
        self._death_date = None
        self._death_time = None

        # Update all attributes from passed dict if provided
        self.__dict__.update(kwargs)

    @property
    def inactive_reason(self):
        return self._inactive_reason

    @inactive_reason.setter
    def inactive_reason(self, value):
        """Checks values of inactive reason before assigning"""
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
        time = validate.valid_time(value)

        if time:
            self._death_time = time

        else:
            raise ValueError("Please enter a valid time in the format HHMM.\n")

    def update_self(self):
        """
        Groups all update methods for user selection. This will be called when modifying record in navigation.py
        """
        navigation.clear()
        while True:
            print(f"ID: {self.id}\n",
                  f"Name: {self.name}\n")

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
                self.get_requests()

            # Generate a new visit
            elif selection == "2":
                classes.visits.Visit.create_self(pat_id=self.id)

            # Update address
            elif selection == "3":
                self.update_address()

            # Update preferences, including skill requirements, gender, and times
            elif selection == "4":
                self.update_skill_pref()

            # Assign responsible team to patient
            elif selection == "5":
                self.assign_team()

            # Inactivate patient
            elif selection == "6":
                self.inactivate_self()
                return 0

            else:
                print("Invalid selection.")

    def get_requests(self):
        """
        Networks to visits in the self.visits list and displays key information, including:
            scheduling_status
            date
            time
            address
        Sorts visits in order of expected date and time.
        :return: 1 if successful
        """
        # TODO: Hide inactive visits
        # Prompt user for date to view and validate format
        while True:
            inp_date = validate.qu_input("Please select a date to view: ")

            if not inp_date:
                return 0

            try:
                val_date = validate.valid_date(inp_date).date().strftime("%d/%m/%Y")

            except AttributeError:
                print("Invalid date format.")
                continue

            if val_date:
                break

        try:
            visits_by_date = self.visits[val_date]

        except KeyError:
            print("There are no visits assigned on this date. Returning...")
            sleep(1.5)
            return 0

        if not self.visits:
            print("This patient does not have any linked visits.")
            sleep(1.5)
            return 0

        # Display list of requests linked to patient.
        for count, visit_id in enumerate(visits_by_date):
            visit = in_out.load_obj(classes.visits.Visit, f"./data/Visit/{visit_id}.pkl")

            print(f"{count + 1}) Visit ID: {visit.id}"
                  f"    Scheduling Status: {visit.sched_status.capitalize()}"
                  f"    Expected Date: {visit.exp_date}"
                  f"    Visit Start Window: {visit.time_earliest}"
                  f"    Visit End Window: {visit.time_latest}")

        # Validate that user input ID of a linked visit, then open visit for modification.
        while True:
            selection = validate.qu_input("Which visit would you like to modify? ")

            if not selection:
                return 0

            # Raise error if not in list
            visit_id = validate.valid_cat_list(selection, visits_by_date)

            if isinstance(visit_id, Exception):
                print("Invalid selection.")
                continue

            visit = in_out.load_obj(classes.visits.Visit, f"./data/Visit/{visit_id}.pkl")
            visit.update_self()

            return 1

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
            self.refresh_self()
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
                self.refresh_self()
                return 0

        prompt = "Are you sure you want to inactivate this record?"
        if validate.yes_or_no(prompt):
            self.status = 0
            # Cancel linked visit requests with a reason of system action. This occurs here rather than above to
            # give user the opportunity to back out changes before cancelling visits.
            if self.visits:
                for visit_list in self.visits.values():
                    for visit_id in visit_list:
                        visit = in_out.load_obj(classes.visits.Visit, f"./data/Visit/{visit_id}")

                        # If any linked visits fail to load, refresh and cancel action.
                        if not visit:
                            print("Unable to load linked visits.")
                            self.refresh_self()
                            return 0

                        visit.status = 0
                        visit.cancel_reason = visit._c_cancel_reason[4]

                        visit.write_self()

                        print("Visits successfully cancelled.")

            # Remove from team
            if self.team_id:
                team = in_out.load_obj(classes.team.Team, f"./data/Team/{self.team_id}")

                # If linked team fails to load, refresh and cancel action.
                if not team:
                    print("Unable to load linked team.")
                    self.refresh_self()
                    return 0

                team.pat_id.remove(self.id)
                team.write_self()

                print("Team successfully unlinked.")

            self.write_self()

            print("Record successfully inactivated.")

            return 1

        else:
            self.refresh_self()
            return 0


class Clinician(Human):
    _id_iter = itertools.count(10000)  # Create a counter to assign new value each time a new obj is created
    _tracked_instances = {}
    _c_inactive_reason = ("no longer works here", "switched roles", "added in error")
    _c_skill_list = ("med administration", "specimen collection", "domestic tasks", "physical assessment")
    _c_discipline = ("doctor", "nurse", "physical Therapist", "occupational Therapist", "medical assistant")

    def __init__(self, status=1, name="", dob="", sex="", address="",
                 team="", start_time="800", end_time="1700", discipline=None,
                 skill_list=[], **kwargs):
        """Initiates and writes-to-file a clinician with the following attributes:
        id, first name, last name, middle name, date of birth, sex, and address
        Assumes standard shift time for start and end time, and inherits address for start/end address.
        These will be updated by a different function called update_start_end"""
        # Inherit from superclass
        super().__init__(status, name, dob, sex, address, team)

        self._id = next(self._id_iter)
        self.start_address = address
        self.end_address = address
        self.start_time = start_time
        self.end_time = end_time
        self.discipline = discipline
        self.skill_list = skill_list
        self.visits = {}
        self._inactive_reason = None

        # Update all attributes from passed dict if provided
        self.__dict__.update(kwargs)

    @property
    def start_address(self):
        """
        Displays an address parsed using USAddress. Loops through values in dictionary to output human-readable address.
        :return: Human-readable address
        """
        return self._start_address["address"] if self._start_address else self.address["address"]

    @start_address.setter
    def start_address(self, value):
        """Checks values of address before assigning"""
        address = validate.valid_address(value)

        if not isinstance(address, Exception):
            self._start_address = address

        else:
            raise ValueError("Please enter a complete and valid address.\n")

    @property
    def start_zip_code(self):
        return self._start_address["zip_code"] if self._start_address else self.address["zip_code"]

    @property
    def start_building(self):
        return self._start_address["building"] if self._start_address else self.address["building"]

    @property
    def start_coord(self):
        return self._start_address["coord"] if self._start_address else self.address["coord"]

    @property
    def start_plus_code(self):
        return self._start_address["plus_code"] if self._start_address else self.address["plus_code"]

    @property
    def end_address(self):
        """
        Displays an address parsed using USAddress. Loops through values in dictionary to output human-readable address.
        :return: Human-readable address
        """
        return self._end_address["address"] if self._end_address else self.address["address"]

    @end_address.setter
    def end_address(self, value):
        """Checks values of address before assigning"""
        address = validate.valid_address(value)

        if not isinstance(address, Exception):
            self._end_address = address

        else:
            raise ValueError("Please enter a complete and valid address.\n")

    @property
    def end_zip_code(self):
        return self._end_address["zip_code"] if self._end_address else self.address["zip_code"]

    @property
    def end_building(self):
        return self._end_address["building"] if self._end_address else self.address["building"]

    @property
    def end_coord(self):
        return self._end_address["coord"] if self._end_address else self.address["coord"]

    @property
    def end_plus_code(self):
        return self._end_address["plus_code"] if self._end_address else self.address["plus_code"]

    @property
    def start_time(self):
        return self._start_time.strftime("%H%M")

    @start_time.setter
    def start_time(self, value):
        """Checks values of start time before assigning"""
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
        time = validate.valid_time(value)

        if time:
            self._end_time = time

        else:
            raise ValueError("Please enter a valid time in the format HHMM.\n")

    @property
    def capacity(self):
        """
        Maximum weight of visits a clinician can undertake. This is based on the assumption that in an 8 hour day,
        a clinician can complete a maximum of 5 complex visits (weight 3). Therefore, an 8 hour day has capacity 15.
        """
        shift_length = (self._end_time.hour - self._start_time.hour)*60 + self._end_time.minute - self._start_time.minute
        return int(shift_length / 32)

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
                                          "     7. Inactivate Record\n"
                                          "\n"
                                          "Selection: ")

            if not selection:
                return 0

            # View/modify scheduled visits
            elif selection == "1":
                self.assigned_visits()

            # Update start/end time and address
            elif selection == "2":
                self.update_start_end()

            # Update address
            elif selection == "3":
                self.update_address()

            # Modify discipline
            elif selection == "4":
                self.modify_discipline()

            # Modify clinical skills
            elif selection == "5":
                self.modify_skills()

            # Assign team
            elif selection == "6":
                self.assign_team()

            # Inactivate record
            elif selection == "7":
                self.inactivate_self()
                return 0

            else:
                print("Invalid selection.")

    def assigned_visits(self):
        """
        Grabs all visits from self.visits and displays schedule for user by day.
        :return: 1 if successful
        """
        # TODO: Hide inactive visits
        # Prompt user for date to view visits
        while True:
            inp_date = validate.qu_input("Please select a date to optimize the route: ")

            if not inp_date:
                return 0

            try:
                val_date = validate.valid_date(inp_date).date().strftime("%d/%m/%Y")

            except AttributeError:
                print("Invalid date format.")
                continue

            if val_date:
                break

        try:
            visits_by_date = self.visits[val_date]

        except KeyError:
            print("There are no visits assigned on this date. Returning...")
            sleep(1.5)
            return 0

        # Initialize all visits and add to list for display
        visit_list = []

        for index, visit_id in enumerate(visits_by_date):
            visit = in_out.load_obj(classes.visits.Visit, f"./data/Visit/{visit_id}.pkl")

            if not visit:
                continue

            print(f"{index+1}) ID: {visit.id}, Patient: {visit.patient_name}, Time Window: {visit.time_earliest} - {visit.time_latest}")
            visit_list.append(visit_id)

        if not visit_list:
            print("There are no visits scheduled for this date.")
            return 0

        # Prompt user for visit to modify and validate against visit list
        selection = validate.qu_input("Please select a visit by index or ID to modify: ")

        if not selection:
            return 0

        visit_id = validate.valid_cat_list(selection, visits_by_date)

        if not visit_id or isinstance(visit_id, Exception):
            return 0

        # Load visit if valid id and go to visit menu
        else:
            visit = in_out.load_obj(classes.visits.Visit, f"./data/Visit/{visit_id}.pkl")
            visit.update_self()
            return 1

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
            self.refresh_self()
            return 0

        detail_dict = {
            "Start Time": self.start_time,
            "Start Address": self.start_address,
            "End Time": self.end_time,
            "End Address": self.end_address
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
            self.refresh_self()
            return 0

        detail_dict = {
            "Discipline": self.discipline,
        }

        # If user does not confirm info, changes will be reverted.
        if not validate.confirm_info(self, detail_dict):
            self.refresh_self()
            return 0

        self.write_self()
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
            self.refresh_self()
            return 0

        detail_dict = {
            "Skill Proficiencies": self.skill_list,
        }

        # If user does not confirm info, changes will be reverted.
        if not validate.confirm_info(self, detail_dict):
            self.refresh_self()
            return 0

        self.write_self()
        return 1

    def optimize_clinician_trip(self):
        """Calculates the estimated trip route for the clinician."""
        geolocation.optimize_trip(clin_id=self.id)

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
            self.refresh_self()
            return 0

        prompt = "Are you sure you want to inactivate this record?"
        if validate.yes_or_no(prompt):
            self.status = 0

            # Remove clinician from linked visit. This occurs here rather than above to
            # give user the opportunity to back out changes before unassigning visits.
            if self.visits:
                for visit_list in self.visits.values():
                    for visit_id in visit_list:
                        visit = in_out.load_obj(classes.visits.Visit, f"./data/Visit/{visit_id}")

                        # If any linked visits fail to load, refresh and cancel action.
                        if not visit:
                            print("Unable to load linked visits.")
                            self.refresh_self()
                            return 0

                        # Remove clinician from visits and remove visits from clinician
                        visit._clin_id = None
                        self.visits = {}
                        visit.write_self()

                        print("Visits successfully unassigned.")

            # Remove from team
            team = in_out.load_obj(classes.team.Team, f"./data/Team/{self._team_id}")

            # If linked team fails to load, refresh and cancel action.
            if not team:
                print("Unable to load linked teams.")
                self.refresh_self()
                return 0

            team.clin_id.remove(self.id)
            team.write_self()

            print("Team successfully unlinked.")

            self.write_self()

            print("Record successfully inactivated.")

            return 1
