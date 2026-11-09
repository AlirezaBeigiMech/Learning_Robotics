"""Hidden tests for the final submission."""

import random

import numpy as np

from academy_grader import robot_checks as rc
from academy_grader import urdf_tools as ut

PKG, REF, ROOT, TIP = "arm_description", "seven_dof_arm.urdf", "base_link", "grasp_frame"


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


def test_hidden_gripper_fingers_mirror(ros, evidence):
    """Opening the gripper moves both fingers symmetrically (mimic joint)"""
    ros.start_launch(PKG, "display.launch.xml")
    assert ros.wait_for_node("/robot_state_publisher", 30)
    opening = round(random.uniform(0.005, 0.03), 3)
    left = ros.lookup("gripper_roll_link", "left_finger_link", timeout=10, joints={"left_finger_joint": opening})
    right = ros.lookup("gripper_roll_link", "right_finger_link", timeout=10, joints={"left_finger_joint": opening})
    evidence(expected="right finger mirrors left finger in y", suggestion="right_finger_joint needs <mimic joint=\"left_finger_joint\"/> and axis (0,-1,0).")
    assert left is not None and right is not None
    assert abs(left[1, 3] + right[1, 3]) < 1e-3 and abs(left[1, 3] - (0.01 + opening)) < 1e-3
