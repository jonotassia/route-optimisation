# This file contains the Visit class to be used in the route optimisation tool.
import itertools
import validate
import in_out
import classes


class Team:
    team_id_iter = itertools.count(10000)  # Create a counter to assign new value each time a new obj is created
    tracked_instances = {}

    def __init__(self, status=1, name=None, address=None):
        """Initializes a new request and links with pat_id. It contains the following attributes:
            req_id, pat_id, name, status, address, the earliest time, latest time, sched status, and cancel_reason"""
        self._id = next(self.team_id_iter)
        self.name = name
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
            if value == 1 or 0:
                self.status = value

            else:
                raise ValueError

        except ValueError:
            print("Status can only be 0 or 1.")

    @property
    def size(self):
        return len(self._clin_id)

    @property
    def pat_load(self):
        return len(self._pat_id)

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

    def update_self(self):
        """Allows the user to update team information"""
        pass

    def write_self(self):
        """Writes the object to file as a JSON using the pickle module"""
        in_out.write_obj(self)

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

        while True:
            # Assign name
            name = input("Name: ")

            if name:
                obj.name = name

            else:
                if not validate.yes_or_no("You have left this information blank. Would you like to quit?"):
                    break

            # Assign address
            address = validate.get_address()

            if address:
                obj.address = address

            else:
                if not validate.yes_or_no("You have left this information blank. Would you like to quit?"):
                    break

            detail_dict = {
                "First Name": obj.name,
                "Address": obj.address
            }

            # If user confirms information is correct, a new object is created, written, and added to _tracked_instances
            if validate.confirm_info(obj, detail_dict):
                return obj

    @classmethod
    def load_self(cls):
        """Class method to initialise the object from file. Returns the object"""
        in_out.get_obj(cls)

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
            prompt = """This team is linked to at least one patient or clinician. 
                        Proceeding will unlink all patients and clinicians. 
                        Are you sure you want to continue?"""

            if not validate.yes_or_no(prompt):
                return 0

        else:
            prompt = "Are you sure you want to inactivate this record?"

            if validate.yes_or_no(prompt):
                self.status = 0

                # Remove team from patients and clinicians
                if self._pat_id:
                    for pat_id in self._pat_id:
                        pat = in_out.load_obj(classes.person.Patient, f"./data/Patient/{pat_id}")
                        pat.team = None
                        pat.write_self()

                if self._clin_id:
                    for clin_id in self._clin_id:
                        clin = in_out.load_obj(classes.person.Clinician, f"./data/Clinician/{clin_id}")
                        clin.team = None
                        clin.write_self()

                self.write_self()
                print("Record successfully inactivated.")

                return 1

    def assign_routes(self):
        """Considers availability of all Patient and number of Visit to book and allocates appropriately"""
        pass

    # TODO: Add a class method to reactivate a record
