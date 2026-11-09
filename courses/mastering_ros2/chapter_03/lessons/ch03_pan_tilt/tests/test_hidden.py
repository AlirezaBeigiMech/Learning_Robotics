"""Hidden tests for the final submission."""

import random

import numpy as np

from academy_grader import robot_checks as rc
from academy_grader import urdf_tools as ut

PKG, REF, ROOT, TIP = "pan_tilt_description", "pan_tilt.urdf", "base_link", "camera_link"


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
