"""Hidden tests for the final submission."""

import random

import numpy as np

from academy_grader import robot_checks as rc
from academy_grader import urdf_tools as ut

PKG, REF, ROOT, TIP = "diffbot_description", "diffbot.urdf", "base_footprint", "left_wheel_link"


def test_hidden_tf_at_several_configurations(ros, evidence):
    """TF matches the kinematics at several unseen configurations"""
    ref = rc.reference_model(__file__, REF)
    ros.start_launch(PKG, "display.launch.xml")
    assert ros.wait_for_node("/robot_state_publisher", 30), "robot_state_publisher did not start"
    bad = 0
    for cfg in rc.random_configs(ref, 3, seed=random.randrange(10**6)):
        m = ros.lookup(ROOT, TIP, timeout=10, joints=cfg)
        e = ut.fk(ref, cfg, ROOT, TIP)
        if m is None or np.linalg.norm(m[:3, 3] - e[:3, 3]) > 2e-3 or rc.rotation_error(m, e) > 2e-2:
            bad += 1
    evidence(expected="all configurations within 2 mm / 1°", suggestion="Re-check joint origins and axes.")
    assert bad == 0


def test_hidden_robot_stands_on_the_ground(evidence):
    """Wheels and casters touch the ground plane, nothing sinks below it"""
    student, _ = rc.student_model(PKG, "urdf/diffbot.urdf.xacro")
    low = rc.lowest_point(student, {}, ROOT)
    evidence(expected="lowest collision point at z = 0 ± 1 mm in base_footprint",
             suggestion="base_link sits at axle height (wheel_radius); casters must reach exactly to the ground.")
    assert abs(low) < 1e-3


def test_hidden_wheels_roll_about_their_axle(ros, evidence):
    """Turning a wheel joint rotates the wheel about the axle without moving it"""
    ros.start_launch(PKG, "display.launch.xml")
    assert ros.wait_for_node("/robot_state_publisher", 30)
    angle = round(random.uniform(0.5, 2.5), 2)
    m = ros.lookup(ROOT, "right_wheel_link", timeout=10, joints={"left_wheel_joint": 0.0, "right_wheel_joint": angle})
    evidence(expected="wheel centre fixed at (0, -0.16, 0.05) and rotated about y",
             suggestion="Wheel joints are continuous, about the y axis, at axle height.")
    assert m is not None and np.allclose(m[:3, 3], [0, -0.16, 0.05], atol=1e-3)
    assert abs(m[1, 1] - 1.0) < 1e-3 and abs(np.arctan2(m[0, 2], m[0, 0]) - angle) < 1e-2
