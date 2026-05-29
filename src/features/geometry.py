import math

import numpy as np
import pandas as pd


GOAL_X = 120
GOAL_CENTER_Y = 40
GOAL_POST_Y_LOW = 36
GOAL_POST_Y_HIGH = 44


def _has_missing_value(*values) -> bool:
    return any(pd.isna(value) for value in values)


def calculate_distance_to_goal(x, y):
    """Calculate Euclidean distance from a shot to the goal center.

    StatsBomb uses a 120 by 80 pitch. The attacking goal center is at
    x=120, y=40. This function treats the shot location and goal center
    as two points on a flat coordinate plane and applies the Pythagorean
    distance formula: sqrt((goal_x - shot_x)^2 + (goal_y - shot_y)^2).
    """
    if _has_missing_value(x, y):
        return np.nan

    return math.sqrt((GOAL_X - x) ** 2 + (GOAL_CENTER_Y - y) ** 2)


def calculate_angle_to_goal(x, y, degrees: bool = False):
    """Calculate the visible angle between the goalposts from a shot.

    The two goalposts are modeled as points at x=120, y=36 and x=120,
    y=44. From the shot location, we draw one line to each post. The
    angle between those two lines is the visible shooting angle: wider
    angles usually mean the player can see more of the goal, while narrow
    angles usually mean the shot is harder.
    """
    if _has_missing_value(x, y):
        return np.nan

    vector_low = np.array([GOAL_X - x, GOAL_POST_Y_LOW - y], dtype=float)
    vector_high = np.array([GOAL_X - x, GOAL_POST_Y_HIGH - y], dtype=float)

    norm_low = np.linalg.norm(vector_low)
    norm_high = np.linalg.norm(vector_high)

    if norm_low == 0 or norm_high == 0:
        angle = math.pi / 2
    else:
        cosine_angle = np.dot(vector_low, vector_high) / (norm_low * norm_high)
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
        angle = math.acos(cosine_angle)

    if degrees:
        return math.degrees(angle)

    return angle


if __name__ == "__main__":
    sample_shots = [
        {"description": "Central close shot", "x": 108, "y": 40},
        {"description": "Central long shot", "x": 90, "y": 40},
        {"description": "Wide angle shot", "x": 108, "y": 20},
        {"description": "Missing location", "x": None, "y": 40},
    ]

    for shot in sample_shots:
        distance = calculate_distance_to_goal(shot["x"], shot["y"])
        angle_radians = calculate_angle_to_goal(shot["x"], shot["y"])
        angle_degrees = calculate_angle_to_goal(shot["x"], shot["y"], degrees=True)

        print(shot["description"])
        print(f"  distance_to_goal: {distance}")
        print(f"  angle_to_goal_radians: {angle_radians}")
        print(f"  angle_to_goal_degrees: {angle_degrees}")
