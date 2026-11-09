"""Checkpoint 'portable': the SAME go_to_goal binary reaches its goal in Webots (through your webots_driver) and in
CoppeliaSim (through your diffbot_bridge.lua from the previous lesson). Arrival is measured with each simulator's
ground truth: the goal (1.2, −0.6) is in the odom frame, which starts at the robot's initial pose.
The 18 cm allowance = the controller's 5 cm tolerance + odometry drift: CoppeliaSim's wheels roll ~3 % short of what
their encoders say, and turning slips a few degrees in both simulators."""

import math
from pathlib import Path

import pytest

from academy_grader import adapters, sim

PKG = "diffbot_webots"
GOAL = (1.2, -0.6)


def error_to_goal(r):
    """Distance between where the robot truly ended and where the goal truly is (the odom frame = start pose)."""
    dx, dy, _ = adapters.relative(r["start_truth"], r["end_truth"])
    return math.hypot(dx - GOAL[0], dy - GOAL[1])


@pytest.fixture(scope="module")
def webots(_harness):
    h = _harness
    h.stop_all()
    proc, truth = adapters.start_webots(h, PKG, Path(__file__).parent)
    odom = sim.Odom(h, "/odom")
    r = {"ok": truth.wait(60) and odom.wait(15)}
    if r["ok"]:
        h.spin_for(0.5)
        r.update(adapters.go_to_goal(h, PKG, None, truth, odom))
    r["launch_log"] = proc.output()
    truth.close()
    odom.close()
    h.stop_all()
    return r


@pytest.fixture(scope="module")
def coppelia(_harness, webots):  # after the Webots run: one simulator at a time
    h = _harness
    h.stop_all()
    proc = h.start_launch("diffbot_coppelia", "sim.launch.xml")
    truth, odom = adapters.Truth(h), sim.Odom(h, "/odom")
    r = {"ok": truth.wait(60) and odom.wait(15)}
    if r["ok"]:
        h.spin_for(1.0)
        r.update(adapters.go_to_goal(h, PKG, None, truth, odom))
    r["launch_log"] = proc.output()
    truth.close()
    odom.close()
    h.stop_all()
    return r


def _check(r, sim_name, evidence):
    assert r["ok"], f"{sim_name} did not start or /odom is silent: " + " | ".join(r["launch_log"].splitlines()[-4:])[-400:]
    err = error_to_goal(r)
    moved = math.hypot(*adapters.relative(r["end_truth"], r["rest_truth"])[:2])
    evidence(expected="'Goal reached' logged; robot truly within 18 cm of (1.2, −0.6); then stays put",
             observed=f"reached={r['reached']} after {r['seconds']:.0f} s; true distance to goal {err * 100:.1f} cm; "
                      f"moved {moved * 100:.1f} cm afterwards; log: " + " | ".join(r["log"].splitlines()[-1:]),
             suggestion="TODO 6/7: subscribe /odom, publish /cmd_vel; turn towards the goal and stop within tolerance.")
    assert r["reached"] and err < 0.18 and moved < 0.01


def test_goal_in_webots(webots, evidence):
    """go_to_goal reaches the goal in Webots"""
    _check(webots, "Webots", evidence)


def test_goal_in_coppeliasim(coppelia, evidence):
    """The same go_to_goal reaches the goal in CoppeliaSim (with your bridge from the previous lesson)"""
    _check(coppelia, "CoppeliaSim", evidence)
