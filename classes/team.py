# This file contains the Visit class to be used in the route optimisation tool.
import itertools
import validate
import in_out
import classes
import navigation


class Team:
    _id_iter = itertools.count(10000)  # Create a counter to assign new value each time a new obj is created
    _tracked_instances = {}

    def __init__(self, status=1, name=None, address=None):
        """Initializes a new request and links with pat_id. It contains the following attributes:
            req_id, pat_id, name, status, address, the earliest time, latest time, sched status, and cancel_reason"""
        self._id = next(self._id_iter)
        self._name = name
        self._status = status
        self._pat_id = []
        self._clin_id = []
        self.address = address

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
    def place_id(self):
        return self._address["place_id"]

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
                                          "     3. Inactivate Record\n"
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

            # Inactivate record
            elif selection == "3":
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

    def write_self(self):
        """Writes the object to file as a .pkl using the pickle module"""
        if in_out.write_obj(self):
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

    def refresh_self(self):
        """Refreshes an existing object from file in the in case users need to back out changes. Returns the object"""
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
                pat = in_out.load_obj(classes.person.Patient, f"./data/Patient/{pat_id}.pkl")

                # If any linked patients fail to load, refresh and cancel action.
                if not pat:
                    print("Unable to load linked patient.")
                    self.refresh_self()
                    return 0

                pat.team_id = None
                pat.write_self()

        if self._clin_id:
            for clin_id in self._clin_id:
                clin = in_out.load_obj(classes.person.Clinician, f"./data/Clinician/{clin_id}.pkl")

                # If any linked clinicians fail to load, refresh and cancel action.
                if not clin:
                    print("Unable to load linked clinician.")
                    self.refresh_self()
                    return 0

                clin.team_id = None
                clin.write_self()

        self.write_self()
        print("Record successfully inactivated.")

        return 1

    def assign_routes(self):
        """Considers availability of all Patient and number of Visit to book and allocates appropriately"""
        pass

    # TODO: Add a class method to reactivate a record
