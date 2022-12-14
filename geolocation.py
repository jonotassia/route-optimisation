# Contains functions related to geolocation using Google OR tools and map APIs. Folium for visualisation.
import folium
from folium import plugins
import osmnx as ox
import networkx as nx
import pandas as pd
import numpy as np
import validate
import navigation
import classes
import boto3
import requests
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import datetime
from time import sleep


def optimize_route(obj):
    """
    Optimizes a single or team of clinicians' schedule for the day based on distance traveled for all assigned visits on
    that day. This uses a combination of Google's distance matrix API and Google OR tools.
    :param obj: Clinician or team to optimize
    :return: List of tuples of appointment addresses for optimal travel time
    """
    # Get date to optimise
    while True:
        inp_date = validate.qu_input("Please select a date to optimize the route: ")

        if not inp_date:
            return 0

        try:
            val_date = validate.valid_date(inp_date).date()

        except AttributeError:
            print("Invalid date format.")
            continue

        if val_date:
            break

    # If team, load list of all linked clinicians
    if isinstance(obj, classes.team.Team):
        # Cancel if team is empty
        if not obj.pats:
            print("This team does not have any patients associated with it. Returning...")
            sleep(1.5)
            return 0

        if not obj.clins:
            print("This team does not have any clinicians associated with it. Returning...")
            sleep(1.5)
            return 0

        clins = obj.clins

        # Grab patients linked to team
        pats = obj.pats

        # Grab all visits across all patients in team, then unpack for single list of team visits
        visits = [visit for pat in pats for visit in pat.visits if visit._exp_date == val_date]

        if not visits:
            print("There are no visits assigned on this date. Returning...")
            sleep(1.5)
            return 0

    # If clin, put clin into list for consistent handling
    elif isinstance(obj, classes.person.Clinician):
        clins = [obj]

        visits = [visit for visit in obj.visits if visit._exp_date == val_date]

        if not visits:
            print("There are no visits assigned on this date. Returning...")
            sleep(1.5)
            return 0

    # Generate data for optimisation problem. Pass clinician as a list top proper handling.
    data_dict = generate_data(visits, clins)

    # Generate distance matrix
    dist_matrix = create_dist_matrix(data_dict["plus_code_list"])

    if not dist_matrix.any():
        return 0

    # Calculate optimal route - this returns a list of lists per clinician, so can safely assume we want index 0
    manager, routing, solution = route_optimizer(dist_matrix, len(clins), data_dict["start_list"],
                                                 data_dict["end_list"], data_dict["time_windows"],
                                                 data_dict["capacities"], data_dict["weights"],
                                                 data_dict["priorities"], data_dict["skills"],
                                                 data_dict["disc"])

    if not solution:
        print("No solution found. Returning...")
        sleep(2)
        return 0

    # Find all nodes that could not be visited and their penalties
    dropped_nodes = {}

    for node in range(routing.Size()):
        if solution.Value(routing.NextVar(node)) == node and not routing.IsStart(node) and not routing.IsEnd(node):
            dropped_nodes[node] = "Skill/Discipline Mismatch" if routing.GetDisjunctionMaxCardinality(
                node) <= 1 else "Time Window Mismatch"

    # Open session to commit changes before prompting route display
    with obj.session_scope():
        # Create optimal route order and assign to each clinician. Pass clin as list for proper handling.
        return_solution(clins, visits, len(data_dict["start_list"]), dropped_nodes, manager, routing, solution)

    # Prompt user for which type of map to load
    confirm = validate.yes_or_no("View route on map?: ")

    if not confirm:
        return 0

    display_route(obj, val_date=val_date)
    return 1


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
    start_list = [clin._start_plus_code for clin in clins]
    end_list = [clin._end_plus_code for clin in clins]

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
    visit_priorities = [(visit._c_visit_priority.index(visit._visit_priority) + 3) ** 4 for visit in visits]
    priorities = [0] * len(start_list) + visit_priorities + [0] * len(end_list)

    # Get clinician and visit skills
    clin_skills = [clin._skill_list for clin in clins]
    visit_skills = [visit._skill_list for visit in visits]
    skills = clin_skills + visit_skills

    # Get disciplines for visit
    clin_disc = [clin._discipline for clin in clins]
    visit_disc = [visit._discipline for visit in visits]
    disc = clin_disc + visit_disc

    data_dict = {
        "plus_code_list": plus_code_list,
        "start_list": start_indices,
        "end_list": end_indices,
        "time_windows": time_windows,
        "capacities": capacities,
        "weights": weights,
        "priorities": priorities,
        "skills": skills,
        "disc": disc
    }

    return data_dict


def route_optimizer(dist_matrix, num_clinicians, start_list, end_list,
                    time_windows, capacities, weights, priorities,
                    skills, discipline):
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
    :param skills: Skills posessed by clinicians and skills required for visits
    :param discipline: The discipline of the clinician and the discipline required for visits
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

    # Establish counting dimension to track number of nodes visited (used for fair breakdown of visits)
    routing.AddConstantDimension(
        1,
        len(weights),  # Analog for total number of visits
        True,
        "count"
    )

    # Set minimum threshold for number of visits so that every clinician must see patients
    count_dimension = routing.GetDimensionOrDie("count")
    for clin in range(num_clinicians):
        index_end = routing.End(clin)
        count_dimension.SetCumulVarSoftLowerBound(index_end, int(0.8 * num_clinicians // len(priorities)), 100)

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

    # Set limits on weight per day. Minimum is 80% of max constraints
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

    # Set up disjunction list for visits whose skills do not match with any clinicians.
    # Each number is the number of the NODE that will be disjuncted
    skill_disj_list = []

    # Set up discipline and skill constraints. Loop over visit portion of list.
    for location_index, visit_skill_disc in enumerate(list(zip(skills, discipline))[num_clinicians:]):
        # Adjust index based on number of clinicians to only be visit locations. Initialize allowed vehicle list
        location_index = location_index + num_clinicians
        allow_list = []
        # Loop over clinician skills and discs. If skills and disciplines match visit or are none/any, add to allow list
        for clin_index, clin_skill_disc in enumerate(list(zip(skills, discipline))[:num_clinicians]):
            # If the discipline or the skills are not specified in the visit, add to list
            if not visit_skill_disc[0] and visit_skill_disc[1] == "any":
                allow_list.append(clin_index)
            # If the discipline matches and the clinician isn't missing any skills for the visit, add to list
            elif visit_skill_disc[1] == clin_skill_disc[1] or visit_skill_disc[1] == "any":
                if visit_skill_disc[0]:
                    for skill in visit_skill_disc[0]:
                        if skill not in clin_skill_disc[0]:
                            break
                        # If skill is final index of list, add to the allow list
                        elif skill == visit_skill_disc[0][-1]:
                            allow_list.append(clin_index)
                else:
                    allow_list.append(clin_index)
        # Set the location index as allowed for anything in the allow list
        if allow_list:
            routing.SetAllowedVehiclesForIndex(allow_list, manager.NodeToIndex(location_index))
        else:
            skill_disj_list.append(location_index)

    # Add a mandatory disjunctions to skip any visit that does not have matching skills or disc
    routing.AddDisjunction([manager.NodeToIndex(node) for node in skill_disj_list], -1, 1)

    # Set the search parameters and a heuristic for initial solution (prioritize cheapest arc - ie least transit time)
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.log_search = True  # to get some logs
    search_parameters.time_limit.seconds = 1

    # Solve the problem and print the solution
    solution = routing.SolveWithParameters(search_parameters)

    return manager, routing, solution


def create_dist_matrix(plus_code_list):
    """
    Generates a distance matrix using place_ids.
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
    max_cols = 25
    num_addresses = len(plus_code_list)
    rows_per_send = max_elements // num_addresses

    # Evaluate number of queries required.
    num_row_query, remaining_rows = divmod(num_addresses, rows_per_send)
    num_column_query, remaining_cols = divmod(num_addresses, max_cols)

    # Create distance matrix with Distance Matrix API - https://developers.google.com/maps/documentation/distance-matrix
    distance_matrix = np.empty((num_addresses, num_addresses), dtype="int")

    # Send sets of addresses in chunks equal to num_queries
    for i in range(num_row_query):
        origin_addresses = plus_code_list[i * rows_per_send: (i + 1) * rows_per_send]
        # Maximum number of columns is 25, so split up queries by column as well. These will be merged into a single
        # dictionary before passing to dist matrix builder function
        comb_response = {
            "destination_addresses": [],
            "origin_addresses": [],
            "rows": []
        }
        for j in range(num_column_query):
            destination_addresses = plus_code_list[j * max_cols:(j + 1) * max_cols]
            # Prepare URL for GET request
            url = "https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial"
            origins = "|".join(origin_addresses).replace(" ", "%20B").replace("+", "%2B")
            destinations = "|".join(destination_addresses).replace(" ", "%20B").replace("+", "%2B")

            url = url + '&origins=' + origins + '&destinations=' + destinations + '&mode=' + mode + '&key=' + google_api_key

            response = query_dist_matrix(url)

            if not response:
                return 0

            # Perform dict comprehension to pass a single dictionary to builder function
            comb_response = {key: comb_response[key] + response.json()[key] for key in comb_response}

        # Send remaining columns
        if remaining_cols > 0:
            destination_addresses = plus_code_list[
                                    num_column_query * max_cols:num_column_query * max_cols + remaining_cols]
            # Prepare URL for GET request
            url = "https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial"
            origins = "|".join(origin_addresses).replace(" ", "%20B").replace("+", "%2B")
            destinations = "|".join(destination_addresses).replace(" ", "%20B").replace("+", "%2B")

            url = url + '&origins=' + origins + '&destinations=' + destinations + '&mode=' + mode + '&key=' + google_api_key

            response = query_dist_matrix(url)

            if not response:
                return 0

            # Perform dict comprehension to pass a single dictionary to builder function
            comb_response = {key: comb_response[key] + response.json()[key] for key in comb_response}

        # Consolidate rows from remainder with rows from num_col_query
        if num_column_query:
            # Hold index constant, then consolidate every nth column into the same row of the response,
            # where i is denominations of rows_per_send up to rows_per_send * column query + index
            # Example: If you have 3 different rows generated from num_column_query + remaining_cols,
            # Index 0 should be row 0 + row 3, index 1 should be row 1 + row 4, and so on
            for index in range(rows_per_send):
                for step_index in range(index + rows_per_send,
                                        rows_per_send * num_column_query + index + rows_per_send,
                                        rows_per_send):
                    comb_response["rows"][index]["elements"] += comb_response["rows"][step_index]["elements"]

            # Delete excess rows
            del comb_response["rows"][rows_per_send:]

        distance_matrix[i * rows_per_send: (i + 1) * rows_per_send] = build_dist_matrix(comb_response)

    # Send remaining rows
    if remaining_rows > 0:
        origin_addresses = plus_code_list[rows_per_send * num_row_query: rows_per_send * num_row_query + remaining_rows]
        # Send remaining columns for rows
        comb_response = {
            "destination_addresses": [],
            "origin_addresses": [],
            "rows": []
        }
        for j in range(num_column_query):
            destination_addresses = plus_code_list[j * max_cols:(j + 1) * max_cols]

            # Prepare URL for GET request
            url = "https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial"
            origins = "|".join(origin_addresses).replace(" ", "%20B").replace("+", "%2B")
            destinations = "|".join(destination_addresses).replace(" ", "%20B").replace("+", "%2B")

            url = url + '&origins=' + origins + '&destinations=' + destinations + '&mode=' + mode + '&key=' + google_api_key

            response = query_dist_matrix(url)

            if not response:
                return 0

            comb_response = {key: comb_response[key] + response.json()[key] for key in comb_response}

        # Send remaining columns
        if remaining_cols > 0:
            destination_addresses = plus_code_list[
                                    num_column_query * max_cols:num_column_query * max_cols + remaining_cols]
            # Prepare URL for GET request
            url = "https://maps.googleapis.com/maps/api/distancematrix/json?units=imperial"
            origins = "|".join(origin_addresses).replace(" ", "%20B").replace("+", "%2B")
            destinations = "|".join(destination_addresses).replace(" ", "%20B").replace("+", "%2B")

            url = url + '&origins=' + origins + '&destinations=' + destinations + '&mode=' + mode + '&key=' + google_api_key

            response = query_dist_matrix(url)

            if not response:
                return 0

            comb_response = {key: comb_response[key] + response.json()[key] for key in comb_response}

        # Consolidate rows from remainder with rows from num_col_query
        for index in range(remaining_rows):
            for step_index in range(index + remaining_rows,
                                    remaining_rows * num_column_query + index + remaining_rows,
                                    remaining_rows):
                comb_response["rows"][index]["elements"] += comb_response["rows"][step_index]["elements"]

        # Delete excess rows
        del comb_response["rows"][remaining_rows:]

        distance_matrix[
        rows_per_send * num_row_query: rows_per_send * num_row_query + remaining_rows] = build_dist_matrix(
            comb_response)

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
    :return: row for distance matrix
    """
    distance_matrix = []

    for row in response['rows']:
        # Loop through each element in the rows of the response and populate a list of each value
        row_list = [int(row["elements"][i]['duration']['value'] / 60) for i in range(len(row["elements"]))]

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
            disj_reason = dropped_nodes[node]
            node = node - n_start_list
            print(
                f"{node}) {visits[node].pat._name}: {visits[node].time_earliest} - {visits[node].time_latest}, "
                f"Priority: {visits[node].visit_priority}, Complexity: {visits[node].visit_complexity}, "
                f"Disjunction Reason: {disj_reason}")

        for clin_index, clin in enumerate(clins):
            print_to_screen(clin_index, clin, visits, n_start_list, manager, routing, solution)

            # Define route order for assignment to clinician
            route_order = return_route(clin_index, manager, routing, solution)

            # Remove the start and end locations of each address and subtract length of start index list from each index
            clin_visits = [visits[index - n_start_list] for index in route_order[1:-1]]

            # Assign clinician to visit (which assigns the visit to the clinician as well) and save
            for index, visit in enumerate(clin_visits):
                visit.clin_id = clin.id
                visit._order = index
                visit.sched_status = "assigned"
                visit.write_obj(visit.session)

        return None

    # Print to screen as dataframe
    if selection == "2" or "3":
        # Generate a dict of all visits that could not be undertaken for this team
        dropped_nodes_dict = {}
        for node in dropped_nodes:
            disj_reason = dropped_nodes[node]
            node = node - n_start_list
            dropped_nodes_dict[visits[node].id] = {
                "Clinician": "UNASSIGNED",
                "Patient Name": visits[node].pat._name,
                "Start By": visits[node].time_earliest,
                "Leave By": visits[node].time_latest,
                "Priority": visits[node].visit_priority,
                "Complexity": visits[node].visit_complexity,
                "Skills Required": visits[node].skill_list,
                "Discipline Requested": visits[node].discipline,
                "Address": visits[node].address,
                "Driving Time": "N/A",
                "Disjunction Reason": disj_reason
            }
        # Convert and display dropped nodes dataframe
        dropped_nodes_df = pd.DataFrame.from_dict(dropped_nodes_dict, orient="index")

        # Initialize a solutions dataframe and add dropped nodes to it
        solution_df = pd.DataFrame(columns=["Clinician", "Patient Name", "Start By", "Leave By", "Priority",
                                                "Complexity", "Skills Required", "Discipline Requested", "Address",
                                                "Driving Time", "Disjunction Reason"])
        solution_df = pd.concat([solution_df, dropped_nodes_df])

        for clin_index, clin in enumerate(clins):
            # Generate a solution dictionary for each clinician, then batch visits to assign to clinician
            rt_detail = print_to_table(clin_index, clin, visits, n_start_list, manager, routing, solution)

            # Define route order for assignment to clinician
            route_order = return_route(clin_index, manager, routing, solution)

            # Remove the start and end locations of each address and subtract length of start index list from each index
            clin_visits = [visits[index - n_start_list] for index in route_order[1:-1]]

            # Assign clinician to visit (which assigns the visit to the clinician as well) and save
            for index, visit in enumerate(clin_visits):
                visit.clin_id = clin.id
                visit._order = index
                visit.sched_status = "assigned"
                visit.write_obj(visit.session)

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
        start_hours, start_min = divmod(solution.Min(time_var), 60)
        end_hours, end_min = divmod(solution.Max(time_var), 60)
        plan_output += f'  {visit.pat._name} ' \
                       f'(Start by: {datetime.time(hour=start_hours, minute=start_min).strftime("%H%M")}, ' \
                       f'Leave by: {datetime.time(hour=end_hours, minute=end_min).strftime("%H%M")}) ->'
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
        start_hours, start_min = divmod(solution.Min(time_var), 60)
        end_hours, end_min = divmod(solution.Max(time_var), 60)
        solutions_dict[visit.id] = {
            "Clinician": clin.name,
            "Patient Name": visit.pat._name,
            "Start By": datetime.time(hour=start_hours, minute=start_min).strftime("%H%M"),
            "Leave By": datetime.time(hour=end_hours, minute=end_min).strftime("%H%M"),
            "Priority": visit.visit_priority,
            "Complexity": visit.visit_complexity,
            "Skills Required": visit.skill_list,
            "Discipline Requested": visit.discipline,
            "Address": visit.address,
            "Driving Time": int(solution.Min(time_var) / 60),
            "Disjunction Reason": "N/A"
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
    lats = [coord[0] for coord_group in coord_list for coord in coord_group]
    lngs = [coord[1] for coord_group in coord_list for coord in coord_group]

    if not lats or not lngs:
        return 0

    lat_list = np.array(lats)
    long_list = np.array(lngs)

    # Average latitude and longitude
    mean_lat = lat_list.mean()
    mean_long = long_list.mean()

    return mean_lat, mean_long


def number_icon(color, number):
    """
    Create a 'numbered' icon for use with Folium
    :param color: Color of marker
    :param number: Number of marker
    :return: Marker icon
    """
    icon = folium.features.DivIcon(
        icon_size=(150, 36),
        icon_anchor=(18, 38),
        html="""<span class="fa-stack" style="font-size: 12pt">
                    <!-- The icon that will wrap the number -->
                    <span class="fa fa-circle-o fa-stack-2x" style="color:{:s}"></span>
                    <!-- a strong element with the custom content, in this case a number -->
                    <strong class="fa-stack-1x">{:02d}</strong>
                </span>""".format(color, number)
    )
    return icon


def display_route(obj, val_date=None):
    """
    Menu for mapping functions
    :param obj: The object from which to gather the route (Team or Clinician only!)
    :param val_date: The date to optimize the route for. If passed through, user is not prompted.
    :return: 0 if nothing is selected
    """
    # TODO: Create an attribute to flag if a day has been optimized
    # Prompt user for date for optimization and validate format
    if not val_date:
        while True:
            inp_date = validate.qu_input("Please select a date to view the route: ")

            if not inp_date:
                return 0

            try:
                val_date = validate.valid_date(inp_date).date()

            except AttributeError:
                print("Invalid date format.")
                continue

            if val_date:
                break

    # If team, load list of all linked clinicians
    if isinstance(obj, classes.team.Team):
        clins = obj.clins

    # If clin, put clin into list for consistent handling
    elif isinstance(obj, classes.person.Clinician):
        clins = [obj]

    else:
        print("Invalid object. Returning...")
        return 0

    # Load list of visits for each clinician as a list of lists. Sort by optmized order.
    visits = [[visit for visit in clin.visits if visit._exp_date == val_date] for clin in clins]
    visits = [sorted(visit_group, key=lambda x: x._order) for visit_group in visits]

    # Verify that all visits have been given an order. Else: prompt to optimize or quit.
    visits_missing_order = [visit for visit_group in visits for visit in visit_group if not visit._order]

    if not visits_missing_order:
        selection = validate.qu_input("These visits are not yet optimized. Would you like to optimize now?")

        if not selection:
            return 0

        else:
            optimize_route(obj)
            return 1

    # Prompt user for which type of map to load
    print("Please select how you would like to view the route:\n"
          "     1) Map Markers Only (Quick)\n"
          "     2) Map with Full Route Info\n")

    selection = -1
    while selection not in ["1", "2"]:
        selection = validate.qu_input("Selection: ")

        if not selection:
            return 0

    if selection == "1":
        map_markers_only(clins, visits)

    if selection == "2":
        map_markers_and_polyline(clins, visits)

    return 1


def map_markers_only(clins, visits):
    """
    Generates a Folium map with markers for each patient. This does not show route details.
    :param clins: Clinicians on the route
    :param visits: Visits for each clinician on the route
    :return: 1 if successful
    """
    # Load coordinates for each visit and start and end coords for each clinician
    visit_locations = [[visit.coord for visit in visit_group] for visit_group in visits]
    center_coord = coord_average(visit_locations)

    if not center_coord:
        print("No visits assigned on this date. Returning...")
        return 0

    # Initialize map and set boundaries.
    route_map = folium.Map(location=center_coord)
    route_map.fit_bounds(visit_locations)

    color_list = (
        'darkblue', 'purple', 'orange', 'green', 'beige', 'lightgreen', 'blue', 'pink', 'lightred', 'red', 'lightgray')

    # Loop through each coord group by clinician and create a new marker and tooltip, assorted by color for each clinician
    for clin_index, clin in enumerate(clins):
        if not clin.visits:
            continue

        # Add feature group for each clinician so they can be turned on or off
        feature_group = folium.FeatureGroup(name=f"{clin.name}").add_to(route_map)

        # Create tooltip for clinician end location
        clin_tooltip = f"""
                    <center><h4>Clinician: {clin.name}</h4></center>
                    <p><b>Address</b>: {clin.address}</p>
                    <p><b>Time Window</b>: {clin.start_time} - {clin.end_time}</p>
                    <p><b>Capacity</b>: {clin.capacity}</p>
                    <p><b>Discipline</b>: {clin.discipline}</p>
                    <p><b>Skills Required</b>: {clin.skill_list}</p>
                    """

        # Create marker image for start location
        feature_group.add_child(
            folium.Marker(
                clin.start_coord,
                tooltip=clin_tooltip,
                icon=folium.Icon(icon_color='white', icon="glyphicon-home", color=color_list[clin_index]),
            ))

        # Loop through visit coordinates and mark on map
        for visit_index, coord in enumerate(visit_locations[clin_index]):
            visit_tooltip = f"""
                        <center><h4>{visit_index + 1}. {visits[clin_index][visit_index].pat._name}</h4></center>
                        <p><b>Address</b>: {visits[clin_index][visit_index].address}</p>
                        <p><b>Time Window</b>: {visits[clin_index][visit_index].time_earliest} - {visits[clin_index][visit_index].time_latest}</p>
                        <p><b>Priority</b>: {visits[clin_index][visit_index].visit_priority}</p>
                        <p><b>Complexity</b>: {visits[clin_index][visit_index].visit_complexity}</p>
                        <p><b>Skills Required</b>: {visits[clin_index][visit_index].skill_list}</p>
                        <p><b>Discipline Requested</b>: {visits[clin_index][visit_index].discipline}</p>
                        """

            # Create marker image
            feature_group.add_child(
                folium.Marker(
                    coord,
                    tooltip=visit_tooltip,
                    icon=folium.Icon(icon_color='white', color=color_list[clin_index]),
                ))

            # Add number to marker
            feature_group.add_child(
                folium.Marker(
                    coord,
                    tooltip=visit_tooltip,
                    icon=number_icon(color_list[clin_index], visit_index + 1)
                ))

        # Create marker image for end location
        feature_group.add_child(
            folium.Marker(
                clin.end_coord,
                tooltip=clin_tooltip,
                icon=folium.Icon(icon_color='white', icon="glyphicon-home", color=color_list[clin_index]),
            ))

    # Add layer control to map and display in browser
    folium.LayerControl().add_to(route_map)
    route_map.show_in_browser()


def find_shortest_route(graph, start_coord, end_coord):
    """
    Finds the shortest route between two coordinates using nodes from OpenStreetMaps
    :param graph: NetworkX Graph providing nodes and edges
    :param start_coord: Starting coordinates
    :param end_coord: Ending coordinates
    :return:
    """
    # find the nearest node to the start location
    orig_node = ox.nearest_nodes(graph, start_coord[1], start_coord[0])
    # find the nearest node to the end location
    dest_node = ox.nearest_nodes(graph, end_coord[1], end_coord[0])
    #  find the shortest path
    shortest_route = nx.shortest_path(graph,
                                      orig_node,
                                      dest_node,
                                      weight='time')

    return shortest_route


def map_markers_and_polyline(clins, visits):
    """
    Generates a Folium map with markers for each patient and a Polyline outlining the route.
    Route is calculated via NetworkX using nodes from OpenStreetMaps.
    :param clins: Clinicians on the route
    :param visits: Visits for each clinician on the route
    :return: 1 if successful
    """
    # Load coordinates for each visit and start and end coords for each clinician
    visit_locations = [[visit.coord for visit in visit_group] for visit_group in visits]
    # Calculate central point to initialize map
    center_coord = coord_average(visit_locations)

    if not center_coord:
        print("No visits assigned on this date. Returning...")
        return 0

    # Get coordinates for bounding box
    start_locations = [clin.start_coord for clin in clins]
    end_locations = [clin.end_coord for clin in clins]
    all_locations = start_locations + [visit.coord for visit_group in visits for visit in visit_group] + end_locations

    all_lat = np.array([coord[0] for coord in all_locations])
    all_lng = np.array([coord[1] for coord in all_locations])
    north_bbox_lim = np.max(all_lat)
    south_bbox_lim = np.min(all_lat)
    east_bbox_lim = np.max(all_lng)
    west_bbox_lim = np.min(all_lng)

    # TODO: Add a preferred travel mode by clinician
    # Set mode of transit and define optmisation method
    mode = 'drive'  # "all_private", "all", "bike", "drive", "drive_service", "walk"
    graph = ox.graph_from_bbox(north_bbox_lim, south_bbox_lim, east_bbox_lim, west_bbox_lim, network_type=mode)



    # Initialize map and set boundaries.
    route_map = folium.Map(location=center_coord)

    # Create feature groups and add to map as layers
    marker_group = folium.FeatureGroup(name=f"Markers").add_to(route_map)
    route_group = folium.FeatureGroup(name=f"Routes").add_to(route_map)

    color_list = (
        'darkblue', 'purple', 'orange', 'green', 'beige', 'lightgreen', 'blue', 'pink', 'lightred', 'red', 'lightgray')

    for clin_index, clin in enumerate(clins):
        # Create subgroups for each clinician in group
        if not clin.visits:
            continue

        sub_marker_group = plugins.FeatureGroupSubGroup(marker_group,
                                                               name=f"Markers - {clins[clin_index].name}").add_to(
            route_map)
        sub_route_group = plugins.FeatureGroupSubGroup(route_group,
                                                              name=f"Route - {clins[clin_index].name}").add_to(
            route_map)

        # Create tooltip for clinician end location
        clin_tooltip = f"""
                    <center><h4>Clinician: {clin.name}</h4></center>
                    <p><b>Address</b>: {clin.address}</p>
                    <p><b>Time Window</b>: {clin.start_time} - {clin.end_time}</p>
                    <p><b>Capacity</b>: {clin.capacity}</p>
                    <p><b>Discipline</b>: {clin.discipline}</p>
                    <p><b>Skills Required</b>: {clin.skill_list}</p>
                    """

        # Create marker image for start location
        sub_marker_group.add_child(
            folium.Marker(
                clin.start_coord,
                tooltip=clin_tooltip,
                icon=folium.Icon(icon_color='white', icon="glyphicon-home", color=color_list[clin_index]),
            ))

        shortest_route = find_shortest_route(graph, clin.start_coord, visits[clin_index][0].coord)

        # Add route to map. Each coordinate is a node and is a point at which directions will change
        coords = [(graph.nodes[node]["y"], graph.nodes[node]["x"]) for node in shortest_route]
        sub_route_group.add_child(folium.PolyLine(coords, weight=3, color=color_list[clin_index]))

        # Create routes for each visit for the clinician
        for visit_index, visit in enumerate(visits[clin_index]):
            # Find the shortest route between coordinates
            if visit_index != len(visits[clin_index])-1:
                shortest_route = find_shortest_route(graph,
                                                     visit_locations[clin_index][visit_index],
                                                     visit_locations[clin_index][visit_index+1])
            # Add route to map
            if shortest_route:
                coords = [(graph.nodes[node]["y"], graph.nodes[node]["x"]) for node in shortest_route]
                sub_route_group.add_child(folium.PolyLine(coords, weight=3, color=color_list[clin_index]))

                visit_tooltip = f"""
                            <center><h4>{visit_index + 1}. {visit.pat._name}</h4></center>
                            <p><b>Address</b>: {visit.address}</p>
                            <p><b>Time Window</b>: {visit.time_earliest} - {visit.time_latest}</p>
                            <p><b>Priority</b>: {visit.visit_priority}</p>
                            <p><b>Complexity</b>: {visit.visit_complexity}</p>
                            <p><b>Skills Required</b>: {visit.skill_list}</p>
                            <p><b>Discipline Requested</b>: {visit.discipline}</p>
                            """

                # Create marker image
                sub_marker_group.add_child(
                    folium.Marker(
                        visit.coord,
                        tooltip=visit_tooltip,
                        icon=folium.Icon(icon_color='white', color=color_list[clin_index]),
                    ))

                # Add number to marker
                sub_marker_group.add_child(
                    folium.Marker(
                        visit.coord,
                        tooltip=visit_tooltip,
                        icon=number_icon(color_list[clin_index], visit_index + 1)
                    ))

        # Add Polyline for end coordinates
        shortest_route = find_shortest_route(graph, visits[clin_index][len(visits[clin_index])-1].coord, clin.end_coord)

        # Add route to map. Each coordinate is a node and is a point at which directions will change
        coords = [(graph.nodes[node]["y"], graph.nodes[node]["x"]) for node in shortest_route]
        sub_route_group.add_child(folium.PolyLine(coords, weight=3, color=color_list[clin_index]))

        # Create marker image for end location
        sub_marker_group.add_child(
            folium.Marker(
                clin.end_coord,
                tooltip=clin_tooltip,
                icon=folium.Icon(icon_color='white', icon="glyphicon-home", color=color_list[clin_index]),
            ))

    folium.LayerControl().add_to(route_map)
    route_map.show_in_browser()
