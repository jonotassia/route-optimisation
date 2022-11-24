# Contains functions related to geolocation using Placekey and mlrose
import in_out
import classes
import mlrose
import numpy as np
import placekey as pk


# TODO: Complete some hyperparameter tuning in jupyter notebook

def optimize_trip(clin_id=""):
    """
    Optimizes a single clinician's schedule for the day based on distance traveled for all assigned visits on that day.
    If called via a clinician method, it will automatically pass in the clinician id.
    Otherwise, the user will be prompted for a clinician id or name.
    :param clin_id: ID of clinician (if in clinician context)
    :return: List of tuples of appointment coordinates for optimal travel time
    """
    # Load a clinician to optimize. If id is passed through, do not prompt for ID.
    if clin_id:
        clin = in_out.load_obj(classes.person.Clinician, f"./data/Clinician/{clin_id}.pkl")

    else:
        print("Please select a clinician for whom you would like to optimize the route.")
        clin = classes.person.Clinician.load_self()

    # Create a list of coordinates by loading all visits attached to the clinician and perforn a list comprehension
    coords = [in_out.load_obj(classes.visits.Visit, f"./data/Visit/{visit_id}.pkl").coord for visit_id in clin._visits]

    # Define the Fitness Fucntion object and Optimization Problem object
    fitness_coords = mlrose.TravellingSales(coords=coords)
    problem_fit = mlrose.TSPOpt(length=len(coords), fitness_fn=fitness_coords, maximize=False)

    # Pass through the genetic algorithm, which will output:
    #   Coord_order - index of coordinates of optimal route
    #   shortest_route - Shortest route the algorithm found across all visit locations
    coord_order, shortest_route = mlrose.genetic_alg(problem_fit, random_state=8)

    print(f"Shortest route will take {shortest_route} minutes.")
    display_route()

    return coord_order

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


def display_route(coord_list):
    """
    Uses Folium to display a route given a list of coordinates
    :param coord_list: List of tuples containing coordinate information
    :return: Ordered list of appointment coordinates for optimal travel time
    """
    pass
