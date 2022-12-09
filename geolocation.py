# Contains functions related to geolocation using Placekey and mlrose
import pandas
import pandas as pd

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
import datetime
from time import sleep


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

        try:
            val_date = validate.valid_date(inp_date).date().strftime("%d/%m/%Y")

        except AttributeError:
            print("Invalid date format.")
            continue

        if val_date:
            break

    try:
        visits_by_date = clin.visits[val_date]

    except KeyError:
        print("There are no visits assigned on this date. Returning...")
        sleep(1.5)
        return 0

    # Create a list of visits by loading all visits attached to the clinician only if they are scheduled for input date.
    visits = [in_out.load_obj(classes.visits.Visit, f"./data/Visit/{visit_id}.pkl") for visit_id in visits_by_date]

    # Generate data for optimisation problem. Pass clinician as a list top proper handling.
    data_dict = generate_data(visits, [clin])

    # Generate distance matrix
    dist_matrix = create_dist_matrix(data_dict["plus_code_list"])

    # Calculate optimal route - this returns a list of lists per clinician, so can safely assume we want index 0
    manager, routing, solution = route_optimizer(dist_matrix, 1, data_dict["start_list"],
                                                 data_dict["end_list"], data_dict["time_windows"],
                                                 data_dict["capacities"], data_dict["weights"],
                                                 data_dict["priorities"])

    if not solution:
        print("No solution found. Returning...")
        sleep(2)
        return 0

    # Assign and print all nodes that could not be visited
    dropped_nodes = (node for node in range(routing.Size())
                     if solution.Value(routing.NextVar(node)) == node
                     and not routing.IsStart(node)
                     and not routing.IsEnd(node))

    # Create optimal route order and assign to each clinician. Pass clin as list for proper handling
    rt_detail = return_solution([clin], visits, len(data_dict["start_list"]),
                                dropped_nodes, manager, routing, solution)

    # # Save route as coordinates. JavaScript API only works using coordinates
    # ordered_route_coords = [clin.start_coord] + [visits[i-1].coord for i in route_order[1:-1]] + [clin.end_coord]

    # # Plot coords on map
    # map_features(route=ordered_route_coords)


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

    if not team:
        return 0

    # Cancel if team is empty
    if not team.pat_load:
        print("This team does not have any patients associated with it. Exiting...")
        sleep(1.5)
        return 0

    # Prompt user for date for optimization and validate format
    while True:
        inp_date = validate.qu_input("Please select a date to optimize the route: ")

        if not inp_date:
            return 0

        try:
            val_date = validate.valid_date(inp_date).date().strftime("%d/%m/%Y")

        except AttributeError:
            print("Invalid date format.")
            continue

        if val_date:
            break

    # Grab patients linked to team
    pats = [in_out.load_obj(classes.person.Patient, f"./data/Patient/{pat_id}.pkl") for pat_id in team._pat_id]

    # Grab all visits across all patients in team, then unpack for single list of team visits
    team_visits = []

    for pat in pats:
        # Handle key errors for patients who do not have visits on the designated day
        try:
            visits = pat.visits[val_date]
        except KeyError:
            continue

        for visit_id in visits:
            visit = in_out.load_obj(classes.visits.Visit, f"./data/Visit/{visit_id}.pkl")
            team_visits.append(visit)

    # Create list of all clinicians linked to team
    clins = [in_out.load_obj(classes.person.Clinician, f"./data/Clinician/{clin_id}.pkl") for clin_id in team._clin_id]

    # Generate data for optimisation problem.
    data_dict = generate_data(team_visits, clins)

    # calculate distance matrix
    dist_matrix = create_dist_matrix(data_dict["plus_code_list"])

    # Optimize routes
    manager, routing, solution = route_optimizer(dist_matrix, team.team_size, data_dict["start_list"],
                                                 data_dict["end_list"], data_dict["time_windows"],
                                                 data_dict["capacities"], data_dict["weights"],
                                                 data_dict["priorities"])

    if not solution:
        print("No solution found. Returning...")
        sleep(2)
        return 0

    # Find all nodes that could not be visited
    dropped_nodes = (node for node in range(routing.Size())
                     if solution.Value(routing.NextVar(node)) == node
                     and not routing.IsStart(node)
                     and not routing.IsEnd(node))

    # Create optimal route order and assign to each clinician
    rt_detail = return_solution(clins, team_visits, len(data_dict["start_list"]),
                                dropped_nodes, manager, routing, solution)

    return 1

    # TODO: Add constraints for already assigned visits


def generate_data(visits, clins):
    """
    Generates the relevant data for route optimization problems.
    :param visits: List of visits
    :param clins: List of clinicians
    :return: Dictionary with the following data:
        - List of starting locations for each clinician
        - List of end locations for each clinician
        - Time windows for each clinician and visit
        - Capacity for each clinician
        - Weights for each visit based on complexity
        - Priority for each visit
    """
    visit_plus_codes = [visit.plus_code for visit in visits]

    # Load all clinicians in team and populate list of start and end plus codes
    start_list = [clin.start_plus_code for clin in clins]
    end_list = [clin.end_plus_code for clin in clins]

    # Combine clinician and patient addresses together
    plus_code_list = start_list + visit_plus_codes + end_list

    # Pass through start and end list (last N indices of plus code list) as indices of distance matrix
    start_indices = [num for num in range(len(start_list))]
    end_indices = [num for num in range(len(start_list) + len(visit_plus_codes), len(plus_code_list))]

    def convert_to_min(_time):
        """
        Takes a datetime object (time) and outputs a total in minutes
        :param _time: Datetime object (time)
        :return: Total time in minutes
        """
        return _time.hour * 60 + _time.minute

    # Create time windows - use private variable for access to datetime value
    clin_window = [(convert_to_min(clin._start_time), convert_to_min(clin._end_time)) for clin in clins]
    visit_window = [(convert_to_min(visit._time_earliest), convert_to_min(visit._time_latest)) for visit in visits]
    time_windows = clin_window + visit_window

    # Get capacity information
    capacities = [clin.capacity for clin in clins]

    # Get weight information, which is numerically represented as complexity index plus 1 for each visit
    visit_weights = [visit._c_visit_complexity.index(visit._visit_complexity) + 1 for visit in visits]
    weights = [0] * len(start_list) + visit_weights + [0] * len(end_list)

    # Get priority information, which is numerically represented as priority index ^4 in order to significantly
    # punish for missing a "Red" visit
    visit_priorities = [(visit._c_visit_priority.index(visit._visit_priority) + 1) ** 4 for visit in visits]
    priorities = [0] * len(start_list) + visit_priorities + [0] * len(end_list)

    data_dict = {
        "plus_code_list": plus_code_list,
        "start_list": start_indices,
        "end_list": end_indices,
        "time_windows": time_windows,
        "capacities": capacities,
        "weights": weights,
        "priorities": priorities
    }

    return data_dict


def route_optimizer(dist_matrix, num_clinicians, start_list, end_list,
                    time_windows, capacities, weights, priorities):
    """
    Passes locations through route optimizer to generate optimal route solution.
    :param dist_matrix: A matrix outlining the amount of time required to transit to each location
    :param num_clinicians: Number of clinicians to consider in calculation
    :param start_list: List of starting location indexes for each clinician
    :param end_list: List of ending location indexes for each clinician
    :param time_windows: The time windows that each location should be visited
    :param capacities: A numeric representation of the max weight (AKA complexity) a clinician can complete in a day
    :param weights: The weight of a visit, derived from visit complexity
    :param priorities: A numeric representation of visit priority. Determines which visits should be dropped first
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

    # Add time window constraints https://developers.google.com/optimization/routing/vrptw
    routing.AddDimension(
        transit_callback_index,
        1410,
        1410,
        False,
        "Time"
    )

    time_dimension = routing.GetDimensionOrDie("Time")

    # Add time window constraint for each location except depot. Start at num_clins to skip start locations
    for location_index, window in enumerate(time_windows):
        if location_index in range(num_clinicians):
            continue
        index = manager.NodeToIndex(location_index)
        time_dimension.CumulVar(index).SetRange(window[0], window[1])

    # Add time window constraints for each vehicle
    for vehicle_id in range(num_clinicians):
        # Set start time constraint for vehicle (Routing always starts at their start time)
        start_index = routing.Start(vehicle_id)
        time_dimension.CumulVar(start_index).SetRange(time_windows[vehicle_id][0], time_windows[vehicle_id][0])
        # Set end time constraint for vehicle (Routing finishes anywhere between start time and end time)
        end_index = routing.End(vehicle_id)
        time_dimension.CumulVar(end_index).SetRange(time_windows[vehicle_id][0], time_windows[vehicle_id][1])
        # Ensure time window considered in solution
        routing.AddVariableMinimizedByFinalizer(time_dimension.CumulVar(routing.Start(vehicle_id)))
        routing.AddVariableMaximizedByFinalizer(time_dimension.CumulVar(routing.End(vehicle_id)))

    # Enable the routing function to use this transit time as its arc cost measurement
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        """
        Returns the demand of the node.
        :param from_index: Routing variable index
        :return: Index of demand node
        """
        # Convert the routing variable Index to weights NodeIndex (ie the demand for the visit)
        from_node = manager.IndexToNode(from_index)
        return weights[from_node]

    # Create a demand callback index to allow for dropping visits if capacities are reached
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,  # Add weight of visit to clinician's daily weight
        100,
        capacities,
        True,
        "Capacity"
    )

    # Set limits on weight per day. Minumum is 80% of max constraints
    # This will accumulate over each visit
    capacity_dimension = routing.GetDimensionOrDie(dimension_name="Capacity")
    for clin in range(num_clinicians):
        index = routing.End(clin)
        try:
            capacity_dimension.CumulVar(index).SetRange(int(capacities[clin] * 0.8), capacities[clin])
        except TypeError as err:
            raise err

    # Define penalties, which will be proportional to the value of the visit priority for each index
    # Penalty cost will only be added if the disjunction is missed (ie a higher value should be less desirable to skip)
    for node in range(len(start_list), len(dist_matrix) - len(end_list)):
        # Each node is made a disjunction so that it is an optional visit. "Red" visits will not be optional
        routing.AddDisjunction([manager.NodeToIndex(node)], priorities[node])

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

        distance_matrix[i * rows_per_send: (i + 1) * rows_per_send] = build_dist_matrix(response.json())

    # Send remaining rows
    if remaining_rows > 0:
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
            response.json())

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
        row_list = [int(row['elements'][i]['duration']['value'] / 60) for i in range(len(row["elements"]))]

        # Add row list to the array
        distance_matrix.append(row_list)

    return distance_matrix


def return_solution(clins, visits, n_start_list, dropped_nodes, manager, routing, solution):
    """
    Prompts the user whether they want to print route solution to screen or file
    :param clins: Clinician whose route is being optimized
    :param visits: List of visits in optimisation problem
    :param n_start_list: number of starting locations in address list
    :param dropped_nodes: Represents all visits that could not be seen as part of the solution
    :param manager: Index manager - parses details from distance matrix
    :param routing: Routing Model - sets parameters for solution
    :param solution: Solution from routing model
    :return: None
    """
    # Prompt user about whether to print to screen or csv
    print("Please select how you would like to view the route information:\n"
          "     1) Print to Screen (Quick)\n"
          "     2) Print to Screen (Table)\n"
          "     3) Print to File\n")

    selection = -1
    while selection not in ["1", "2", "3"]:
        selection = validate.qu_input("Selection: ")

        if not selection:
            return 0

    # Print to Screen in text
    if selection == "1":
        # Print dropped nodes
        print(f"The following patients could not be seen: ")
        for node in dropped_nodes:
            print(
                f"{node}) {visits[node].patient_name}: {visits[node].time_earliest} - {visits[node].time_latest}, "
                f"Priority: {visits[node].visit_priority}, Complexity: {visits[node].visit_complexity}")

        for clin_index, clin in enumerate(clins):
            print_to_screen(clin_index, clin, visits, n_start_list, manager, routing, solution)

            # Define route order for assignment to clinician
            route_order = return_route(clin_index, manager, routing, solution)

            # Remove the start and end locations of each address and subtract length of start index list from each index
            clin_visits = [visits[index - n_start_list] for index in route_order[1:-1]]

            # Assign clinician to visit (which assigns the visit to the clinician as well) and save
            for visit in clin_visits:
                visit.clin_id = clin.id
                visit.write_self()

        return None

    # Print to screen as dataframe
    if selection == "2" or "3":
        # Generate a dict of all visits that could not be undertaken for this team
        dropped_nodes_dict = {}
        for node in dropped_nodes:
            dropped_nodes_dict[visits[node].id] = {
                "Clinician": "UNASSIGNED",
                "Patient Name": visits[node].patient_name,
                "Start By": visits[node].time_earliest,
                "Leave By": visits[node].time_latest,
                "Priority": visits[node].visit_priority,
                "Complexity": visits[node].visit_complexity,
                "Skills Required": visits[node].skill_list,
                "Address": visits[node].address,
                "Driving Time": "N/A"
            }
        # Convert and display dropped nodes dataframe
        dropped_nodes_df = pd.DataFrame.from_dict(dropped_nodes_dict, orient="index")

        # Initialize a solutions dataframe and add dropped nodes to it
        solution_df = pandas.DataFrame(columns=["Clinician", "Patient Name", "Start By", "Leave By", "Priority",
                                                "Complexity", "Skills Required", "Address", "Driving Time"])
        solution_df = pd.concat([solution_df, dropped_nodes_df])

        for clin_index, clin in enumerate(clins):
            # Generate a solution dictionary for each clinician, then batch visits to assign to clinician
            rt_detail = print_to_table(clin_index, clin, visits, n_start_list, manager, routing, solution)

            # Define route order for assignment to clinician
            route_order = return_route(clin_index, manager, routing, solution)

            # Remove the start and end locations of each address and subtract length of start index list from each index
            clin_visits = [visits[index - n_start_list] for index in route_order[1:-1]]

            # Assign clinician to visit (which assigns the visit to the clinician as well) and save
            for visit in clin_visits:
                visit.clin_id = clin.id
                visit.write_self()

            # Convert rt_details to Pandas table and display
            rt_detail = pd.DataFrame.from_dict(rt_detail, orient="index")
            solution_df = pd.concat([solution_df, rt_detail])

        solution_df.index.name = "Visit ID"

        # Save file
        if selection == "3":
            while True:
                # Get file path from user
                path = validate.qu_input("File path to save (*.csv): ")

                # Prompt user if they want to continue if no path entered. If no, short circuit and print to screen
                if not path:
                    cont = validate.qu_input("No file path entered. Print to screen instead? ")
                    if cont:
                        break

                try:
                    solution_df.to_csv(path)

                except (FileNotFoundError, OSError):
                    print("Invalid path.")

                return solution_df

        # Display the full solution data frame. Occurs if a user selected 2 or did not provide a path for csv
        print(solution_df.to_markdown())
        return solution_df


def print_to_screen(clin_index, clin, visits, n_start_list, manager, routing, solution):
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

    # Get time dimension
    time_dimension = routing.GetDimensionOrDie('Time')

    # Start routing for clinician
    index = routing.Start(clin_index)
    plan_output = f"\nOptimal route for {clin.name}: \n"
    route_time = 0

    # Start routing output
    plan_output += f'  Start ->'
    previous_index = index
    index = solution.Value(routing.NextVar(index))
    route_time += routing.GetArcCostForVehicle(previous_index, index, 0)

    # Add each index to plan_output
    while not routing.IsEnd(index):
        # Subtract number of items in start list from node to match with visits in visit list
        visit = visits[manager.IndexToNode(index) - n_start_list]
        # Get time window for each location
        time_var = time_dimension.CumulVar(index)
        leave_by = datetime.timedelta(minutes=solution.Max(time_var))
        plan_output += f'  {visit.patient_name} ' \
                       f'(Start by: {visit._time_earliest.strftime("%H:%M")}, ' \
                       f'Leave by: {str(leave_by).rstrip(":")}) ->'
        index = solution.Value(routing.NextVar(index))

    # Add final index
    time_var = time_dimension.CumulVar(index)
    plan_output += f' Return'
    plan_output += f'\nRoute Time: {int(solution.Min(time_var) / 60)} minutes.'

    print(plan_output)


def print_to_table(clin_index, clin, visits, n_start_list, manager, routing, solution):
    """
    Prints the solution to the route optimisation problem to a table using Pandas.
    :param clin_index: Index of the clinician whose route is being optimized
    :param clin: Clinician whose route is being optimized
    :param visits: List of visits in optimisation problem
    :param n_start_list: number of starting locations in address list
    :param manager: Index manager - parses details from distance matrix
    :param routing: Routing Model - sets parameters for solution
    :param solution: Solution from routing model
    :return: None
    """
    # Create a solutions dict
    solutions_dict = {}

    # Get time dimension
    time_dimension = routing.GetDimensionOrDie('Time')

    # Start routing for clinician
    index = routing.Start(clin_index)
    route_time = 0

    # Start routing output
    previous_index = index
    index = solution.Value(routing.NextVar(index))
    route_time += routing.GetArcCostForVehicle(previous_index, index, 0)

    # Add each index to plan_output
    while not routing.IsEnd(index):
        # Subtract number of items in start list from node to match with visits in visit list
        visit = visits[manager.IndexToNode(index) - n_start_list]
        # Get time window for each location
        time_var = time_dimension.CumulVar(index)
        leave_by = datetime.timedelta(minutes=solution.Max(time_var))
        solutions_dict[visit.id] = {
            "Clinician": clin.name,
            "Patient Name": visit.patient_name,
            "Start By": visit.time_earliest,
            "Leave By": leave_by,
            "Priority": visit.visit_priority,
            "Complexity": visit.visit_complexity,
            "Skills Required": visit.skill_list,
            "Address": visit.address,
            "Driving Time": int(solution.Min(time_var) / 60)
        }
        index = solution.Value(routing.NextVar(index))

    return solutions_dict


def return_route(clin_index, manager, routing, solution):
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
