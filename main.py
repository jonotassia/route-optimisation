# This programme will use a feed from a geolocation API to determine the ideal route for Clinicians to Patient homes
# based on a geographic data, patient preferences, and clinician availability.
# It will use geocoding from Nominatim: https://nominatim.org/

import classes
import geopy             # See details here: https://pypi.org/project/geopy/
import PySimpleGUI as sg

"""
Primary stream - sequence of events:
- Generate list of Clinicians
- Generate list of Patient
- Generate list of Request each day (networked to a patient via ID)
- Calculate real distances between Clinicians and Request
- Evaluate all permutations of routes and select optimal route

Secondary actions available:
- Update user, patient, or request details
- Cancel Request
- Audit logging
"""

# TODO: Determine how to create an audit log
# TODO: Investigate how to create a database
# TODO: Investigate how to automatically batch and run nightly
# TODO: Determine how to deploy to a server
# TODO: Determine a file structure for saving Patient, Request, and Clinicians

if __name__ == "__main__":
    sg.Window(title="Route Planning", layout=[[]], margins=(100, 50)).read()
