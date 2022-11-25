# This programme will use a feed from a geolocation API to determine the ideal route for Clinician to Patient homes
# based on a geographic data, patient preferences, and clinician availability.
# It will use geocoding from Nominatim: https://nominatim.org/
import navigation
from classes.person import Patient, Clinician
from classes.visits import Visit
from classes.team import Team


"""
Primary stream - sequence of events:
- Generate list of Clinician
- Generate list of Patient
- Generate list of Visits each day (networked to a patient and clinician via ID)
- Generate list of Team each day (networked to a patient and clinician via ID)
- Calculate real distances between Clinician and Visits
- Evaluate all permutations of routes and select optimal route

Secondary actions available:
- Update user, patient, visit, or team details
- Cancel Visit
- Audit logging
"""

# TODO: Determine how to create an audit log
# TODO: Investigate how to create a database
# TODO: Investigate how to automatically batch and run nightly
# TODO: Determine how to deploy to a server

if __name__ == "__main__":
    # Initialize a list of all classes and loop to populate instance tracking lists
    _class_list = (Patient, Clinician, Visit, Team)

    for cls in _class_list:
        cls.load_tracked_instances()

    navigation.main_menu(_class_list)
