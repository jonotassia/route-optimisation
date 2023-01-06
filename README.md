# Clinician Route Optimiser

This is a project to allow teams of home-visiting clinicians optimize their patient caseloads on a given day and ensure that clinicians are spending the least amount of time in transit and more time providing patient care.

## Data Structure
The data contained in this programme is broken down into 4 main classes:
* Patient (subclass of human)
* Clinician (subclass of human)
* Visit
* Team

Each of these classes are importable from CSV or can be generated manually. There are a number of pointers via ID from one type of class to another. For example, Patients and Clinicians both store a pointer to Visit ID.

Each class instance is also a member of the DataManager class, which manages reading and writing to a SQLite database using SQLAlchemy ORM.

## Geolocation and Optimization Functions
Each object has address attributes that are geocoded using Google's Geocoding API. A team manager can opt to generate an optimized route for the whole team or a single clinician. When run, the optimizer uses Google's OR tools to find the ideal route for the clinician(s).

Steps to optimize route:
1. Data subset is generated, including: visits, clinicians, list of addresses/plus codes, clinician capacities, visit weights, and visit priorities
2. The geocodes for each visit and clinician are passed to Google's Distance Matrix API to generate a travel time matrix for the requested mode of transit. Each value is the time it takes to travel one location to the corresponding destination.
3. Google's OR tools takes the resulting output and attempts to find a global optimum based on the following constraints:
    1. Minimize route time for all clinicians
    2. Clinicians have a maximum amount of visit complexity they can complete (estimated 15 weight equivalents for a standard 8 hour day)
    3. If a visit must be missed due to resource constraints, the algorithm MUST prioritise any visits that are rated as a "Red" (AKA urgent) visit
4. The system saves the sequenced routes to each clinician and outputs to screen or file, based on user input.

![image](https://user-images.githubusercontent.com/24849659/207723170-d5ad772b-34bc-46ed-8089-375ce298b238.png)

## Visualisation
Once a route has been optimized, users can plot the output using Folium. The shortest route between each OpenStreetMaps node is calculated using OSMNX and NetworkX.

Users can choose to visualize the route in two different ways:
* Routes: Calculated from node-to-node from OpenStreetMaps
* Markers: Numbered by the order in which patients should be seen

Each clinician's route is displayed in a different color, and each clinician's route/markers are hidden behind Folium layers so that they can be turned on or off. As with the route optimizer, routes can be generated by individual clinician or for all clinicians on a single team.

![image](https://user-images.githubusercontent.com/24849659/207722262-3b9ef354-5145-4009-8531-eb324099dffc.png)



## Upcoming Changes
Future scope includes:
* Change clinician availability to be a dictionary by date, rather than a static start/stop time across all days.
* Adding additional constraints, including: preferred clinicians, specimen drop-off or admin tasks
* Android application for clinicians to view schedule real-time

## Known Issues
Below is a list of known issues:
1. When searching for an object, inactive objects are not currently filtered out even if the user indicates they do not want to see them.
2. Route optimisation currently prompts the user for a travel mode (driving, walking, etc) rather than using a preferred mode for each clinician.
3. Performance is slow in route optimisation for large teams and in route visualisation when showing the full route due to the recent SQLAlchemy ORM transition.
4. Some routes visualized using OSMNx have Polylines that do not perfectly follow paths due to completeness of mapping data.
