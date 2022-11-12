# This file contains the Visit class to be used in the route optimisation tool.
import pickle
import itertools
import validate
import in_out
from datetime import datetime, date
import asyncio
import aiofiles


class Visit:
    visit_id_iter = itertools.count()  # Create a counter to assign new value each time a new obj is created
    tracked_instances = {}
    c_sched_status = ("Unscheduled", "Scheduled", "No Show", "Cancelled")
    c_cancel_reason = ("Clinician unavailable", "Patient Unavailable", "No longer needed", "Expired")

    def __init__(self, pat_id, status=1, sched_status="", address="", time_earliest="", time_latest="", exp_date=""):
        """Initializes a new request and links with pat_id. It contains the following attributes:
            req_id, pat_id, status, address, the earliest time, latest time, sched status, and cancel_reason"""
        self.id = next(self.visit_id_iter)
        self.pat_id = pat_id
        self.status = status
        self.address = address
        self.time_earliest = time_earliest
        self.time_latest = time_latest
        self.exp_date = exp_date
        self.cancel_reason = None
        self.sched_status = sched_status

        self.write_self()

    def cancel_visit(self):
        """This method sets the status of a request to inactive and the sched status to "cancelled".
        Prompts the user for a cancel reason and files back to self.cancel_reason
        It will not be cancelled if the request meets any of the below criteria:
        - The request is in the past
        - The request has already been scheduled
        - the request has already been deleted
        """

        # Checks if request is already inactive
        if self.status == 0:
            print("This request is already inactive.")
            return 0

        # Checks that sched status is scheduled using the schedule category list
        elif self.sched_status == self.c_sched_status[1]:
            print("This request is already scheduled. Please cancel the appointment instead.")
            return 0

        else:
            reason = validate.get_cat_value(self.c_cancel_reason, "Select a cancel reason. ")

            prompt = "Are you sure you want to cancel this request? You will be unable to schedule this request."
            if validate.yes_or_no(prompt):
                self.cancel_reason = reason
                self.status = 0

            self.write_self()

            return 1

    def update_visit(self):
        """Allows the user to update request information, including date/time window or address
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
    def read_self(cls):
        """Class method to initialise the object from file. Returns the object"""
        in_out.read_obj(cls)

    @classmethod
    def load_tracked_instances(cls):
        in_out.load_tracked_obj(cls)

    @classmethod
    async def evaluate_requests(cls):
        """Evaluates all Visits and marks them as no shows if they are past their expected date"""
        for instance in cls.tracked_instances:
            try:
                async with open(f"./data/{type(cls).__name__}/{instance['id']}", "rb") as read_file:
                    request = pickle.load(read_file)

                    # Evaluate date against current date and mark as expired if due before current date
                    if datetime.strptime(request.exp_date, '%m-%d-%Y').date() < date.today():
                        request.status = 0
                        request.cancel_reason = cls.c_cancel_reason[3]
                        cls.write_self(request)

            except FileNotFoundError as err:
                print("File could not be found.")
                return err
