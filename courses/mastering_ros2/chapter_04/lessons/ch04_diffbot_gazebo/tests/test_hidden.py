"""Hidden test for the final submission: a distance and speed you have not seen."""

import math
import random

from test_drive import drive_run


def test_hidden_custom_distance_and_speed(ros, evidence):
    """drive_forward honours its 'distance' and 'speed' parameters"""
    distance = round(random.uniform(0.5, 0.8), 2)
    speed = round(random.uniform(0.25, 0.3), 2)
    r = drive_run(ros, "--ros-args", "-p", f"distance:={distance}", "-p", f"speed:={speed}")
    assert r["ready"], "simulation not ready"
    g0, g1, _ = r["g"]
    d = math.hypot(g1[0] - g0[0], g1[1] - g0[1])
    evidence(expected="travelled distance within ±12 % of the requested distance",
             suggestion="Read 'distance' and 'speed' with declare_parameter and use them.")
    assert abs(d - distance) <= 0.12 * distance
