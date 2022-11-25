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

    # Distill visits into list of place_ids
    place_id_list = [visit.place_id for visit in visits]

    # Generate distance matrix
    dist_matrix = create_dist_matrix(place_id_list)


def create_dist_matrix(place_id_list):
    """
    Generates a distance matrix using place_ids.
    :param place_id_list: List of place_ids to convert into a distance matrix
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

    # Create a distance using Distance Matrix API - https://developers.google.com/maps/documentation/distance-matrix
    payload = {
        "origins": place_id_list,
        "key": google_api_key
    }


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


# def display_route_in_browser(coord_list, visit_list):
#     """
#     Uses Folium to display a route given a list of coordinates
#     This will be displayed in a browser using Flask.
#     :param coord_list: List of tuples containing coordinate information
#     :param visit_list: Ordered list of visit objects to use for generating markers and the tooltip
#     :return: Ordered list of appointment coordinates for optimal travel time
#     """
#     # Calculate central point to initialize map
#     center_coord = coord_average(coord_list)
#
#     # Initialize map and set boundaries.
#     geo_map = folium.Map(location=center_coord)
#     geo_map.fit_bounds(coord_list)
#
#     # Create colour list for loop
#     color_list = ['#440154', '#481a6c', '#472f7d', '#414487', '#39568c', '#31688e', '#2a788e', '#23888e', '#1f988b',
#                   '#22a884', '#35b779', '#54c568', '#7ad151', '#a5db36', '#d2e21b']
#
#     # Loop through each coord and create a new marker and tooltip
#     for index, visit in enumerate(visit_list):
#         tooltip = f"<center><h2>{index}</h2></center>" \
#                   f"<b><i>{visit.patient_name}</i></b>" \
#                 f"<i>{visit.address}<i>" \
#                 f"{visit.coord}"
#
#         folium.Marker(
#             visit.coord,
#             tooltip=tooltip,
#             icon=folium.Icon(color='white', icon_color='white'),
#             markerColor=color_list[index],
#         ).add_to(geo_map)
#
#         folium.Marker(
#             visit.coord,
#             tooltip=tooltip,
#             icon=num_icon(color_list[index], index)
#         ).add_to(geo_map)
#
#     return geo_map._repr_html_()


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


# def num_icon(color, number):
#     """
#     Create a 'numbered' icon for plotting in Folium
#     :return: A numbered icon to put on the map
#     """
#     icon = folium.features.DivIcon(
#         icon_size=(150, 36),
#         icon_anchor=(14, 40),
#         html="""<span class="fa-stack " style="font-size: 12pt" >>
#                     <!-- The icon that will wrap the number -->
#                     <span class="fa fa-circle-o fa-stack-2x" style="color : {:s}"></span>
#                     <!-- a strong element with the custom content, in this case a number -->
#                     <strong class="fa-stack-1x">
#                          {:02d}
#                     </strong>
#                 </span>""".format(color, number)
#     )
#     return icon
