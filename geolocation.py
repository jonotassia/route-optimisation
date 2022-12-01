# Contains functions related to geolocation using Placekey and mlrose
import in_out
import classes
import numpy as np
import validate
import navigation
import boto3
import requests
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import googlemaps


def optimize_trip(clin_id=""):
    """
    Optimizes a single clinician's schedule for the day based on distance traveled for all assigned visits on that day.
    If called via a clinician method, it will automatically pass in the clinician id.
    Otherwise, the user will be prompted for a clinician id or name.
    This uses a combination of Google's distance matrix API and Google OR tools.
    :param clin_id: ID of clinician (if in clinician context)
    :return: List of tuples of appointment coordinates for optimal travel time
    """
    # Load a clinician to optimize. If id is passed through, do not prompt for ID.
    if clin_id:
        clin = in_out.load_obj(classes.person.Clinician, f"./data/Clinician/{clin_id}.pkl")

    else:
        print("Please select a clinician for whom you would like to optimize the route.")
        clin = classes.person.Clinician.load_self()

        if not clin:
            return 0

    # Prompt user for date for optimization and validate format
    while True:
        inp_date = validate.qu_input("Please select a date to optimize the route: ")

        if not inp_date:
            return 0

        val_date = validate.valid_date(inp_date)

        if val_date:
            break

    # Create a list of visits by loading all visits attached to the clinician only if they are scheduled for input date.
    visits = [in_out.load_obj(classes.visits.Visit, f"./data/Visit/{visit_id}.pkl") for visit_id in
              clin.visits['val_date']]

    # Distill visits into list of place_ids and add the clinician's start and end address
    plus_code_list = clin.start_plus_code + [visit.plus_code for visit in visits] + clin.end_plus_code

    # Generate distance matrix
    dist_matrix = create_dist_matrix(plus_code_list)

    # Calculate optimal route - this returns a list of lists per clinician, so can safely assume we want index 0
    manager, routing, solution = route_optimizer(dist_matrix, num_clinicians=1, start_list=0, end_list=(len(dist_matrix) - 1))

    print_solution(1, clin, visits, 1, manager, routing, solution)
    route_order = return_solution(1, manager, routing, solution)

    # Resequence clinician visits for future use, but cut off start and end address.
    clin.visits[val_date] = [clin.visits[val_date][i].id for i in route_order[1:-1]]
    clin.write_self()

    # Save route as coordinates. JavaScript API only works using coordinates
    ordered_route_coords = [visits[i].coord for i in route_order]

    # Plot coords on map
    map_features(route=ordered_route_coords)

    # TODO: Add constraints for start and end time


def optimize_team(team_id=""):
    """
    Optimizes all clinicians' schedules within a team by day based on distance traveled.
    This calculation is based on visits associated with patients that belong to the team.
    If called via a team method, it will automatically pass in the team id.
    Otherwise, the user will be prompted for a team id or name.
    :param team_id: ID of clinician (if in clinician context)
    :return: Dictionary of list of tuples of appointment coordinates by clinician for optimal travel time
    """
    # Load a clinician to optimize. If id is passed through, do not prompt for ID.
    if team_id:
        team = in_out.load_obj(classes.team.Team, f"./data/Team/{team_id}.pkl")

    else:
        print("Please select a team for which you would like to optimize all clinician routes.")
        team = classes.team.Team.load_self()

    pats = [in_out.load_obj(classes.person.Patient, f"./data/Patient/{pat_id}.pkl") for pat_id in team._pat_id]

    # Prompt user for date for optimization and validate format
    while True:
        inp_date = validate.qu_input("Please select a date to optimize the route: ")

        if not inp_date:
            return 0

        val_date = validate.valid_date(inp_date)

        if val_date:
            break

    # Grab all visits across all patients in team, then unpack for single list of team visits
    team_visits = [
        in_out.load_obj(classes.visits.Visit, f"./data/Visit/{visit_id}.pkl")
        for pat in pats for visit_id in pat.visits[val_date]
        ]

    team_plus_codes = [visit.plus_code for visit in team_visits]

    # Load all clinicians in team and populate list of start and end plus codes
    clins = [in_out.load_obj(classes.person.Clinician, f"./data/Clinician/{clin_id}.pkl") for clin_id in team._clin_id]
    start_list = [clin.start_plus_code for clin in clins]
    end_list = [clin.end_plus_code for clin in clins]

    # Combine clinician and patient addresses together
    plus_code_list = start_list + team_plus_codes + end_list

    # calculate distance matrix
    dist_matrix = create_dist_matrix(plus_code_list)

    # Pass through start and end list (last N indices of plus code list) as indices of distance matrix
    start_indices = [num for num in range(len(start_list))]
    end_indices = [num for num in range(len(plus_code_list[-len(end_list):]))]

    # Optimize routes
    manager, routing, solution = route_optimizer(dist_matrix, team.team_size, start_indices, end_indices)

    # Create optimal route order and assign to each clinician
    for i, clin in enumerate(clins):
        print_solution(i, clin, team_visits, len(start_list), manager, routing, solution)
        route_order = return_solution(i, manager, routing, solution)
        # Remove the start and end locations of each address and subtract length of start index list from each index
        clin_visits = [team_visits[index-len(start_list)] for index in route_order[1:-1]]
        clin.visits[val_date] = [visit.id for visit in clin_visits]

        # Assign clinician to visit and save
        for visit in clin_visits:
            visit._clin_id = clin.id
            visit.write_self()

        # Save clinician
        clin.write_self()

    # TODO: Add constraints for already assigned visits
    # TODO: Make sure this assigns the visits to clinicians


def route_optimizer(dist_matrix, num_clinicians, start_list, end_list):
    """
    Passes locations through route optimizer to generate optimal route solution.
    :param dist_matrix:
    :param num_clinicians: Number of clinicians to consider in calculation
    :param start_list: List of starting location indexes for each clinician
    :param end_list: List of ending location indexes for each clinician
    :return: Optimized solution
    """
    # Create index/routing manager - location number corresponds to index in distance matrix (0 = start, last = end)
    manager = pywrapcp.RoutingIndexManager(len(dist_matrix), num_clinicians, start_list, end_list)
    routing = pywrapcp.RoutingModel(manager)

    def transit_callback(from_index, to_index):
        """
        Accepts a from and to index and returns the corresponding part of the distance matrix
        :param from_index: index of departure location
        :param to_index: index of arrival location
        :return: travel time between 2
        """
        # Convert from routing variable Index to distance matrix NodeIndex
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return dist_matrix[from_node][to_node]

    # Create a callback index using the transit time callback nested function
    transit_callback_index = routing.RegisterTransitCallback(transit_callback)

    # Enable the routing function to use this transit time as its arc cost measurement
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Set the search parameters and a heuristic for initial solution (prioritize cheapest arc - ie least transit time)
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

    # Solve the problem and print the solution
    solution = routing.SolveWithParameters(search_parameters)

    return manager, routing, solution


def create_dist_matrix(plus_code_list):
    """
    Generates a distance matrix using place_ids.
    :param clin: clinician used to extract start and end address
    :param plus_code_list: List of plus codes to calculate into a distance matrix
    :return: distance matrix
    """
    # Initiate AWS SSM integration for secrets storage
    ssm = boto3.client('ssm')

    # Grab api key from AWS and authenticate with google
    google_api_key = ssm.get_parameter(Name="GOOGLE_CLOUD_API_KEY", WithDecryption=True)["Parameter"]["Value"]

    # Prompt user for desired mode of transit
    while True:
        navigation.clear()

        mode_list = ["driving", "walking", "bicycling", "transit"]
        validate.print_cat_value(mode_list, "Please select a transportation mode.")
        inp_mode = validate.qu_input("Mode: ")

        if not inp_mode:
            return 0

        mode = validate.valid_cat_list(inp_mode, mode_list)

        if mode:
            break

    # Define constraints for creating distance matrix - maximum 100 elements per query based on num origins and dests
    max_elements = 100
    num_addresses = len(plus_code_list)
    rows_per_send = max_elements // num_addresses

    # Evaluate number of queries required
    num_queries, remaining_rows = divmod(num_addresses, rows_per_send)

    # Create distance matrix with Distance Matrix API - https://developers.google.com/maps/documentation/distance-matrix
    distance_matrix = np.empty((num_addresses, num_addresses), dtype="int")

    # Send sets of addresses in chunks equal to num_queries
    for i in range(num_queries):
        origin_addresses = plus_code_list[i * rows_per_send: (i + 1) * rows_per_send]

        # Prepare URL for GET request
        url = "https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial"
        origins = "|".join(origin_addresses).replace(" ", "%20B").replace("+", "%2B")
        destinations = "|".join(plus_code_list).replace(" ", "%20B").replace("+", "%2B")

        url = url + '&origins=' + origins + '&destinations=' + destinations + '&mode=' + mode + '&key=' + google_api_key

        response = query_dist_matrix(url)

        if not response:
            return 0

        distance_matrix[i * rows_per_send: (i + 1) * rows_per_send] = build_dist_matrix(response)

    # Send remaining rows
    for i in range(remaining_rows):
        origin_addresses = plus_code_list[rows_per_send * num_queries: rows_per_send * num_queries + remaining_rows]

        # Prepare URL for GET request
        url = "https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial"
        origins = "|".join(origin_addresses).replace(" ", "%20B").replace("+", "%2B")
        destinations = "|".join(plus_code_list).replace(" ", "%20B").replace("+", "%2B")

        url = url + '&origins=' + origins + '&destinations=' + destinations + '&mode=' + mode + '&key=' + google_api_key

        response = query_dist_matrix(url)

        if not response:
            return 0

        distance_matrix[rows_per_send * num_queries: rows_per_send * num_queries + remaining_rows] = build_dist_matrix(
            response)

    return distance_matrix


def query_dist_matrix(url):
    """
    Queries google's distance matrix API
    :param url: Contains url and parameters for query
    :return: dist matrix values as list if successful
    """

    try:
        response = requests.request("GET", url)

    except requests.exceptions.RequestException:
        print("Unable to validate address. Please try again.")
        return 0

    return response


def build_dist_matrix(response):
    """
    Takes response from distance matrix API to add rows to the distance matrix. We will use travel time rather than
    distance.
    :param response: response from Google's distance matrix API
    :param num_addresses: Number of addresses to set array size for columns
    :param rows: Number of rows being included in response
    :return: row for distance matrix
    """
    distance_matrix = []

    for row in response['rows']:
        # Loop through each element in the rows of the response and populate a list of each value
        row_list = [int(row['elements'][i]['duration']['value']) for i in range(len(row["elements"]))]

        # Add row list to the array
        distance_matrix.append(row_list)

    return distance_matrix


def print_solution(clin_index,  clin, visits, n_start_list, manager, routing, solution):
    """
    Prints the solution to the route optimisation problem to the console.
    :param clin_index: Index of the clinician whose route is being optimized
    :param clin: Clinician whose route is being optimized
    :param visits: List of visits in optimisation problem
    :param n_start_list: number of starting locations in address list
    :param manager: Index manager - parses details from distance matrix
    :param routing: Routing Model - sets parameters for solution
    :param solution: Solution from routing model
    :return: None
    """
    print(f"Objective: {solution.ObjectiveValue()} minutes.")

    index = routing.Start(clin_index)
    plan_output = f"Optimal route for {clin.name}: \n"
    route_time = 0

    # Start routing but output
    plan_output += f'  {clin.start_address} ->'
    previous_index = index
    index = solution.Value(routing.NextVar(index))
    route_time += routing.GetArcCostForVehicle(previous_index, index, 0)

    # Add each index to plan_output
    while not routing.IsEnd(index):
        # Subtract number of items in start list from node to match with visits in visit list
        plan_output += f'  {visits[manager.IndexToNode(index)-n_start_list].patient_name} ->'
        previous_index = index
        index = solution.Value(routing.NextVar(index))
        route_time += routing.GetArcCostForVehicle(previous_index, index, 0)

    # Add final index
    plan_output += f' {clin.end_address}'
    plan_output += f'Route distance: {route_time} minutes.'

    print(plan_output)


def return_solution(clin_index, manager, routing, solution):
    """
    Returns the solution to the route optimisation problem to the console.
    :param clin_index: Index of the clinician whose route is being optimized
    :param manager: Index manager - parses details from distance matrix
    :param routing: Routing Model - sets parameters for solution
    :param solution: Solution from routing model
    :return: solution as a list of indices as a list per clinician with the start and end locations removed
    """
    index = routing.Start(clin_index)
    route_order = []

    # Add each index to plan_output
    while not routing.IsEnd(index):
        route_order.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))

    # Add final index
    route_order.append(manager.IndexToNode(index))

    return route_order


def coord_average(coord_list):
    """
    Finds the average point between all coordinates in the coordinate list in order to center the map.
    :param coord_list: List of tuples containing coordinate information
    :return: Tuple of average longitude and latitude
    """
    # Split latitude and longitude
    lat_list = np.array([coord[0] for coord in coord_list])
    long_list = np.array([coord[1] for coord in coord_list])

    # Average latitude and longitude
    mean_lat = lat_list.mean()
    mean_long = long_list.mean()

    return mean_lat, mean_long


def map_features(route=None):
    """
    Menu for mapping functions
    :param route: Optional - If passed, this will be used as the route rather than reloading from clin.visits
    :return: 0 if nothing is selected
    """
    # TODO: Create an attribute to flag if a day has been optimized
    # Load a clinician to pull their route if no route passed
    if not route:
        print("Please select a clinician for whom you would like to optimize the route.")
        clin = classes.person.Clinician.load_self()

        if not clin:
            return 0

        # Prompt user for date for optimization and validate format
        while True:
            inp_date = validate.qu_input("Please select a date to view: ")

            if not inp_date:
                return 0

            val_date = validate.valid_date(inp_date)

            if val_date:
                break

        # Create a list of coords by loading all visits attached to the clinician only if they are scheduled for date.
        route = [in_out.load_obj(classes.visits.Visit, f"./data/Visit/{visit_id}.pkl").coord for visit_id
                 in clin.visits['val_date']]

        # Append start and end address
        route = clin._start_coord + route + clin._end_coord

    center = coord_average(route)

    # Initiate AWS SSM integration for secrets storage
    ssm = boto3.client('ssm')

    # Grab api key from AWS and authenticate with google
    google_api_key = ssm.get_parameter(Name="GOOGLE_CLOUD_API_KEY", WithDecryption=True)["Parameter"]["Value"]

    # Initialize googlemaps API
    gmaps = googlemaps.Client(key=google_api_key)

    result_map = gmaps.static_map(
        center=center,
        scale=2,
        zoom=12,
        size=[640, 640],
        format="jpg",
        maptype="roadmap",
        markers=route,
        path="color:0x0000ff|weight:2|" + "|".join()
    )
