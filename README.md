# Clinician Route Optimiser

This is a project to allow teams of home-visiting clinicians optimize their patient caseloads on a given day and ensure that clinicians are spending the least amount of time in transit and more time providing patient care.

## Data Structure
The data contained in this programme is broken down into 4 main classes:
* Patient (subclass of human)
* Clinician (subclass of human)
* Visit
* Team

Each of these classes are importable from CSV or can be generated manually. There are a number of pointers via ID from one type of class to another. For example, Patients and Clinicians both store a pointer to Visit ID.

Class instances are tracked using a tracked instance class attribute, which is populated at start up and appended when new objects are created and written.

## Geolocation and Optimization Functions
Each object has address attributes that are geocoded using Google's Geocoding API. A team manager can opt to generate an optimized route for the whole team or a single clinician. When run, the optimizer uses Google's OR tools to find the ideal route for the clinician(s).

Steps to optimize route:
1. Data subset is generated, including: visits, clinicians, list of addresses/plus codes, clinician capacities, visit weights, and visit priorities
2. The geocodes for each visit and clinician are passed to Google's Distance Matrix API to generate a travel time matrix for the requested mode of transit. Each value is the time it takes to travel one location to the corresponding destination.
3. Google's OR tools takes the resulting output and attempts to find a global optimum based on the following constraints:
  3.1. Minimize route time for all clinicians
  3.2. Clinicians have a maximum amount of visit complexity they can complete (estimated 15 weight equivalents for a standard 8 hour day)
  3.3. If a visit must be missed due to resource constraints, the algorithm MUST prioritise any visits that are rated as a "Red" (AKA urgent) visit
4. The system saves the sequenced routes to each clinician and outputs to screen or file, based on user input.

![image](https://user-images.githubusercontent.com/24849659/206609866-7df57930-bcee-41e7-9533-c9be50e37d9d.png)

## Upcoming Changes
Future scope includes:
* Adding additional constraints, including: Skills/disciplines, preferred clinicians, specimen drop-off or admin tasks
* Visualisation on website deployed via Flask
* Android application for clinicians to view schedule real-time

## Known Issues
Below is a list of known issues:
1. When searching for an object, inactive objects are not currently filtered out even if the user indicates they do not want to see them.
2. ID generation is currently entirely system assigned through an iterator that is set at startup and incremented each time a new object is written, and imports do not match on ID (ie imports create records, not modify)
3. Imports do not handle invalid responses and the programme errors out.
4. If no solution is found by Google OR tools, right now the application just quits.
