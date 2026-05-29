import math
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.features.geometry import (
    calculate_angle_to_goal,
    calculate_distance_to_goal,
)


def test_distance_to_goal_is_smaller_for_closer_shots():
    close_shot = calculate_distance_to_goal(110, 40)
    far_shot = calculate_distance_to_goal(80, 40)

    assert close_shot < far_shot


def test_distance_to_goal_is_zero_at_goal_center():
    distance = calculate_distance_to_goal(120, 40)

    assert distance == 0


def test_angle_to_goal_is_larger_for_central_close_shot_than_wide_far_shot():
    central_close_angle = calculate_angle_to_goal(108, 40)
    wide_far_angle = calculate_angle_to_goal(80, 10)

    assert central_close_angle > wide_far_angle


def test_geometry_functions_handle_missing_values():
    distance = calculate_distance_to_goal(None, 40)
    angle = calculate_angle_to_goal(None, 40)

    assert math.isnan(distance)
    assert math.isnan(angle)
