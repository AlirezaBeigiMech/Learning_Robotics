"""Checkpoint 'tf': your launch file starts robot_state_publisher with YOUR model, and the TF it
publishes for grader-chosen joint values matches the specification's kinematics."""

import random

import numpy as np
import pytest

from academy_grader import robot_checks as rc
from academy_grader import urdf_tools as ut

PKG, REF, ROOT, TIP = "arm_description", "seven_dof_arm.urdf", "base_link", "grasp_frame"


@pytest.fixture(scope="module")
def live(_harness):
    h = _harness
    h.stop_all()
    proc = h.start_launch(PKG, "display.launch.xml")
    rsp = h.wait_for_node("/robot_state_publisher", 30)
    pubs, _ = h.endpoints("/robot_description")
    ref = rc.reference_model(__file__, REF)
    config = rc.random_configs(ref, 1, seed=random.randrange(10**6))[0]
    measured = h.lookup(ROOT, TIP, timeout=15, joints=config) if rsp else None
    frames = h.tf_frames()
    result = {"rsp": rsp, "desc_pubs": [p["node"] for p in pubs], "config": config, "measured": measured,
              "expected": ut.fk(ref, config, ROOT, TIP), "frames": frames, "ref_links": [l.name for l in ref.links],
              "output": proc.output(), "alive": proc.alive}
    h.stop_all()
    return result


def test_launch_starts_robot_state_publisher(live, evidence):
    """display.launch.xml starts robot_state_publisher, which publishes /robot_description"""
    tail = " | ".join(live["output"].splitlines()[-4:])
    evidence(expected="/robot_state_publisher running and publishing /robot_description",
             observed=f"node {'up' if live['rsp'] else 'missing'}; publishers {live['desc_pubs']}; launch output: {tail}",
             suggestion="Build, then run the launch file yourself and read its output for errors.")
    assert live["rsp"] and "/robot_state_publisher" in live["desc_pubs"]


def test_tf_contains_every_link(live, evidence):
    """TF contains a frame for every link of the model"""
    missing = sorted(set(live["ref_links"]) - set(live["frames"]))
    evidence(expected=f"frames {sorted(live['ref_links'])}", observed=f"missing {missing or 'none'}",
             suggestion="Moving joints only appear in TF once /joint_states provides their values.")
    assert not missing


def test_tf_matches_kinematics(live, evidence):
    """For grader-chosen joint values, TF puts the tip exactly where the kinematics say"""
    m, e = live["measured"], live["expected"]
    cfg = ", ".join(f"{k}={v:+.2f}" for k, v in live["config"].items())
    evidence(expected=f"{TIP} in {ROOT} at {rc.fmt_vec(e[:3, 3])} for {cfg}",
             observed="no transform" if m is None else f"{rc.fmt_vec(m[:3, 3])}, orientation off by "
                                                        f"{np.degrees(rc.rotation_error(m, e)):.1f}°",
             suggestion="If the model checkpoint passes but this fails, the launch file may load a different file.")
    assert m is not None
    assert np.linalg.norm(m[:3, 3] - e[:3, 3]) < 2e-3 and rc.rotation_error(m, e) < 2e-2
