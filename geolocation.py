# Contains functions related to geolocation using Placekey and mlrose
import in_out
import classes
import numpy as np
import validate
import navigation
import boto3
import requests

# TODO: Complete some hyperparameter tuning in jupyter notebook


def optimize_trip(clin_id=""):
    """
    Optimizes a single clinician's schedule for the day based on distance traveled for all assigned visits on that day.
    If called via a clinician method, it will automatically pass in the clinician id.
    Otherwise, the user will be prompted for a clinician id or name.
    This uses a combination of Google's distance matrix API and Google OR tools.
    :param clin_id: ID of clinician (if in clinician context)
    :return: List of tuples of appointment coordinates for optimal travel time
    """
    # TODO: Figure out how to enforce clinician start and end locations and time window. Consider CustomFitness
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
    visits = [in_out.load_obj(classes.visits.Visit, f"./data/Visit/{visit_id}.pkl") for visit_id in clin.visits
              if visit_id in classes.visits.Visit._instance_by_date[val_date]]

    # Distill visits into list of place_ids and add the clinician's start and end address
    plus_code_list = clin.start_plus_code + [visit.plus_code for visit in visits] + clin.end_plus_code

    # Generate distance matrix
    dist_matrix = create_dist_matrix(plus_code_list)


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