# This programme will use a feed from a geolocation API to determine the ideal route for clinicians to patients homes
# based on a geographic data, patient preferences, and clinician availability.
# It will use geocoding from Nominatim: https://nominatim.org/

import lib_func
import geopy             # See details here: https://pypi.org/project/geopy/

"""
Primary stream - sequence of events:
- Generate list of clinicians
- Generate list of patients
- Generate list of requests each day (networked to a patient via ID)
- Calculate real distances between clinicians and requests
- Evaluate all permutations of routes and select optimal route

Secondary actions available:
- Update user, patient, or request details
- Cancel requests
- Audit logging
"""

# TODO: Determine how to create an audit log
# TODO: Investigate how to create a database
# TODO: Investigate how to automatically batch and run nightly
# TODO: Determine how to deploy to a server
# TODO: Determine how to do completion matching on addresses by country

if __name__ == "__main__":
    pass
