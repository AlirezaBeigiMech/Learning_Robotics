"""Checkpoint 'scan': /scan is a correct sensor_msgs/LaserScan: right frame and angles, beams in ROS order.
The world has a wall 2 m ahead of the robot (1.92 m from the laser) and a box 1.2 m to its left."""

import math
from pathlib import Path

import pytest
from rclpy.qos import qos_profile_sensor_data

from academy_grader import adapters

PKG = "diffbot_webots"


@pytest.fixture(scope="module")
def scan(_harness):
    h = _harness
    h.stop_all()
    proc, truth = adapters.start_webots(h, PKG, Path(__file__).parent)
    ok = truth.wait(60)
    msgs = h.collect("/scan", "sensor_msgs/msg/LaserScan", 3.0, qos=qos_profile_sensor_data) if ok else []
    log = proc.output()
    truth.close()
    h.stop_all()
    assert ok, "Webots did not start: " + " | ".join(log.splitlines()[-5:])[-400:]
    assert msgs, "no message on /scan"
    return msgs[-1][1]


def beam(scan, angle):
    i = round((angle - scan.angle_min) / scan.angle_increment)
    return scan.ranges[i] if 0 <= i < len(scan.ranges) else float("nan")


def test_scan_geometry(scan, evidence):
    """360 beams around the robot, one per degree, in frame laser_link"""
    evidence(expected="frame laser_link, 360 ranges, angle_increment 2π/360, angles from −π to π",
             observed=f"frame {scan.header.frame_id!r}, {len(scan.ranges)} ranges, increment {scan.angle_increment:.5f}, "
                      f"angle_min {scan.angle_min:.3f}, angle_max {scan.angle_max:.3f}",
             suggestion="TODO 5: angle_increment = fov / n, angle_min = −fov/2 + increment/2, "
                        "angle_max = angle_min + (n − 1)·increment.")
    assert scan.header.frame_id == "laser_link" and len(scan.ranges) == 360
    assert abs(scan.angle_increment - 2 * math.pi / 360) < 1e-4
    assert abs(scan.angle_min + math.pi) < 0.02 and abs(scan.angle_max - math.pi) < 0.02


def test_wall_ahead(scan, evidence):
    """The wall straight ahead is at angle 0, 1.92 m away"""
    r = beam(scan, 0.0)
    evidence(expected="range at 0° ≈ 1.92 m", observed=f"{r:.3f} m", suggestion="Copy all n ranges (TODO 5).")
    assert abs(r - 1.92) < 0.03


def test_box_on_the_left(scan, evidence):
    """The box on the robot's LEFT appears at +90° (ROS angles grow counter-clockwise)"""
    left, right = beam(scan, math.pi / 2), beam(scan, -math.pi / 2)
    evidence(expected="+90°: ≈ 1.20 m (box); −90°: nothing (inf or > 5 m)", observed=f"+90°: {left:.3f} m, −90°: {right:.3f} m",
             suggestion="Webots lists the beams clockwise (left to right); a LaserScan runs counter-clockwise. "
                        "Reverse the order (std::reverse).")
    assert abs(left - 1.2) < 0.03 and (math.isinf(right) or right > 5)
