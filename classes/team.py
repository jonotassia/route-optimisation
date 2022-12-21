# This file contains the Visit class to be used in the route optimisation tool.
import itertools
from sqlalchemy import Column, String, Integer, PickleType, Table, ForeignKey
from sqlalchemy.ext.mutable import MutableList, MutableDict
from data_manager import DataManagerMixin
import geolocation
import validate
import in_out
import classes
import navigation


@DataManagerMixin.mapper_registry.mapped
class Team(DataManagerMixin):
    __table__ = Table(
        "Team",
        DataManagerMixin.mapper_registry.metadata,
        Column("_id", Integer, primary_key=True, unique=True),
        Column("_pat_id", MutableList.as_mutable(PickleType), ForeignKey("Patient._id"), nullable=True),
        Column("_clin_id", MutableList.as_mutable(PickleType), ForeignKey("Clinician._id"), nullable=True),
        Column("_status", String, nullable=True),
        Column("_address", MutableDict.as_mutable(PickleType), nullable=True)
    )

    _id_iter = itertools.count(10000)  # Create a counter to assign new value each time a new obj is created
    _tracked_instances = {}

    def __init__(self, status=1, name=None, address=None, **kwargs):
        """Initializes a new request and links with pat_id. It contains the following attributes:
            req_id, pat_id, name, status, address, the earliest time, latest time, sched status, and cancel_reason"""
        super().__init__()

        self._id = next(self._id_iter)
        self._name = name
        self.status = status
        self._pat_id = []
        self._clin_id = []
        self.address = address

        # Update all attributes from passed dict if provided
        self.__dict__.update(kwargs)

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
                raise ValueError

        except ValueError:
            print("Status can only be 0 or 1.")

    @property
    def team_size(self):
        return len(self._clin_id)

    @property
    def pat_load(self):
        return len(self._pat_id)

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

    def update_self(self):
        """
        Allows the user to update team information, including name, address
        """
        navigation.clear()
        print(f"ID: {self.id}".ljust(10), f"Name: {self._name}\n".rjust(10))

        while True:
            selection = validate.qu_input("What would you like to do:\n"
                                          "     1. Update Name\n"
                                          "     2. Update Address\n"
                                          "     3. Optimize Route\n"
                                          "     4. Display Route\n"
                                          "     5. Inactivate Record\n"
                                          "\n"
                                          "Selection: ")

            if not selection:
                return 0

            # Update request date and time
            elif selection == "1":
                self.update_name()

            # Update request address
            elif selection == "2":
                self.update_address()

            # Optimize route
            elif selection == "3":
                self.optimize_route()

            # display route
            elif selection == "4":
                self.display_route()

            # Inactivate record
            elif selection == "5":
                self.inactivate_self()
                return 0

            else:
                print("Invalid selection.")

    def update_name(self):
        """
        Update name of team.
        :return: 1 if successful
        """
        while True:
            attr_list = [
                {
                    "term": f"Name. Previous: {self._name}",
                    "attr": "name"
                }
            ]

            # Update all attributes from above. Quit if user quits during any attribute
            if not validate.get_info(self, attr_list):
                self.refresh_self()
                return 0

            detail_dict = {
                "Name": self._name
            }

            # If user does not confirm info, changes will be reverted.
            if not validate.confirm_info(self, detail_dict):
                self.refresh_self()
                return 0

            self.write_obj()
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

        self.write_obj()
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
                "term": "Name",
                "attr": "_name"
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
            "Name": obj._name,
            "Address": obj.address
        }

        # If user confirms information is correct, a new object is created, written, and added to _tracked_instances
        if not validate.confirm_info(obj, detail_dict):
            print("Record not created.")
            return 0

        obj.write_self()
        return obj

    @classmethod
    def load_tracked_instances(cls):
        in_out.load_tracked_obj(cls)

    def inactivate_self(self):
        """
        This method sets the status of a team to inactive.
        If patients and clinicians are currently linked, prompt user to quit or unlink.
        """

        # Checks if request is already inactive.
        if self.status == 0:
            print("This record is already inactive.")
            return 0

        # Checks if the team has active patients or clinicians linked to it and prompt user to cancel or quit.
        elif self._pat_id or self._clin_id:
            prompt = ("This team is linked to at least one patient or clinician.\n"
                      "Proceeding will unlink all patients and clinicians.\n"
                      "Are you sure you want to continue?\n")

            if not validate.yes_or_no(prompt):
                return 0

        else:
            prompt = "Are you sure you want to inactivate this record?"
            if not validate.yes_or_no(prompt):
                return 0

        self.status = 0

        # Remove team from patients and clinicians
        if self._pat_id:
            for pat_id in self._pat_id:
                pat = classes.person.Patient.load_obj(pat_id)

                # If any linked patients fail to load, refresh and cancel action.
                if not pat:
                    print("Unable to load linked patient.")
                    self.refresh_self()
                    return 0

                pat.team_id = None
                pat.write_obj()

        if self._clin_id:
            for clin_id in self._clin_id:
                clin = classes.person.Clinician.load_obj(clin_id)

                # If any linked clinicians fail to load, refresh and cancel action.
                if not clin:
                    print("Unable to load linked clinician.")
                    self.refresh_self()
                    return 0

                clin.team_id = None
                clin.write_obj()

        self.write_obj()
        print("Record successfully inactivated.")

        return 1

    def optimize_route(self):
        """Calculates the estimated route for all clinicians on the team."""
        geolocation.optimize_route(self.id)

    def display_route(self):
        """Displays the route for all clinicians on the team."""
        geolocation.display_route(self.id)
    # TODO: Add a class method to reactivate a record
