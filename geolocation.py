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
import flask
from flask import Flask


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
    visits = [in_out.load_obj(classes.visits.Visit, f"./data/Visit/{visit_id}.pkl") for visit_id in clin.visits['val_date']]

    # Distill visits into list of place_ids and add the clinician's start and end address
    plus_code_list = clin.start_plus_code + [visit.plus_code for visit in visits] + clin.end_plus_code

    # Generate distance matrix
    dist_matrix = create_dist_matrix(plus_code_list)

    # Calculate optimal route
    route_order = route_optimizer(dist_matrix, num_clinicians=1, start_list=0, end_list=(len(dist_matrix)-1))

    # Resequence as coordinates. JavaScript API only works using coordinates
    ordered_route_coords = [visits[i].coord for i in route_order]

    # Plot coords on map
    plot_coords(ordered_route_coords)

    # TODO: Add constraints for start and end time


def route_optimizer(dist_matrix, num_clinicians, start_list, end_list):
    """
    Passes locations through route optimizer to generate optimal route solution.
    :param dist_matrix:
    :param num_clinicians: Number of clinicians to consider in calculation
    :param start_list: List of starting location indexes for each clinician
    :param end_list: List of ending location indexes for each clinician
    :return: List of indices ordered by most efficient route
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

    if solution:
        print_solution(manager, routing, solution)
        route_order = return_solution(manager, routing, solution)
        return route_order


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

        distance_matrix[rows_per_send * num_queries: rows_per_send * num_queries + remaining_rows] = build_dist_matrix(response)

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


def print_solution(manager, routing, solution):
    """
    Prints the solution to the route optimisation problem to the console.
    :param manager: Index manager - parses details from distance matrix
    :param routing: Routing Model - sets parameters for solution
    :param solution: Solution from routing model
    :return: None
    """
    print(f"Objective: {solution.ObjectiveValue()} minutes.")
    index = routing.Start(0)
    plan_output = "Optimal route for clinician: \n"
    route_time = 0

    # Add each index to plan_output
    while not routing.IsEnd(index):
        plan_output += f'  {manager.IndexToNode(index)} ->'
        previous_index = index
        index = solution.Value(routing.NextVar(index))
        route_time += routing.GetArcCostForVehicle(previous_index, index, 0)

    # Add final index
    plan_output += f' {manager.IndexToNode(index)}'
    print(plan_output)
    plan_output += f'Route distance: {route_time} minutes.'


def return_solution(manager, routing, solution):
    """
    Returns the solution to the route optimisation problem to the console.
    :param manager: Index manager - parses details from distance matrix
    :param routing: Routing Model - sets parameters for solution
    :param solution: Solution from routing model
    :return: solution as a list of indices
    """
    print(f"Objective: {solution.ObjectiveValue()} minutes.")
    index = routing.Start(0)
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


def plot_coords(route):
    """
    Uses Google Maps JavaScript API and Flask to display a map on a webpage with markers for each location.
    :param route: Ordered list of coordinates to plot
    :return: None
    """
    app = Flask(__name__)

    center = coord_average(route)

    @app.route("/")
    def index():
        return flask.render_template('map.html', geocode=route, center=center)

    app.run(host='0.0.0.0', port=8080, debug=True)


def show_route(route):
    """
    Uses Google Maps JavaScript API and Flask to display a map on a webpage with the calculated route for each visit.
    :param route: Ordered list of coordinates to map
    :return: None
    """
    app = Flask(__name__)

    center = coord_average(route)

    @app.route("/")
    def index():
        return flask.render_template('route.html', geocode=route, center=center)

    app.run(host='0.0.0.0', port=8080, debug=True)


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

    pass

    # TODO: Add constraints for already assigned visits
    # TODO: Make sure this assigns the visits to clinicians

