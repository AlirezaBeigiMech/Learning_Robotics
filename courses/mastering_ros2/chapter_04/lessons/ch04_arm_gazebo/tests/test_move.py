"""Checkpoint 'move': your move_arm node drives the simulated arm to the pose given in its parameters."""

import random

import pytest

from academy_grader import sim

PKG = "arm_sim"
CONTROLLERS = ["joint_state_broadcaster", "arm_controller", "gripper_controller"]
ARM = ["shoulder_pan_joint", "shoulder_pitch_joint", "elbow_roll_joint", "elbow_pitch_joint",
       "wrist_roll_joint", "wrist_pitch_joint", "gripper_roll_joint"]
DEFAULT = [0.0, 0.5, 0.0, 1.0, 0.0, 0.5, 0.0]


def move_run(h, target: list[float] | None, duration: float | None = None, settle: float = 6.0) -> dict:
    h.stop_all()
    h.start_launch(PKG, "sim.launch.xml")
    states = sim.wait_controllers_active(h, CONTROLLERS, timeout=60)
    joints = sim.Joints(h)
    r = {"ready": all(states.get(c) == "active" for c in CONTROLLERS), "states": states}
    if r["ready"]:
        joints.settle(1.0)
        args = []
        if target is not None:
            args += ["-p", "positions:=[" + ",".join(f"{v:.3f}" for v in target) + "]"]
        if duration is not None:
            args += ["-p", f"duration:={duration}"]
        node = h.start(PKG, "move_arm", *(["--ros-args", *args] if args else []))
        r["reached"] = joints.settle(settle + (duration or 2.0))
        r["node_log"] = node.output()
    joints.close()
    h.stop_all()
    return r


def errors(r, target):
    return {j: abs(r["reached"].get(j, float("nan")) - t) for j, t in zip(ARM, target)}


@pytest.fixture(scope="module")
def default_run(_harness):
    return move_run(_harness, None)


@pytest.fixture(scope="module")
def param_run(_harness):
    # floor-safe pitch ranges (no link within 12 cm of the ground; checked by forward kinematics)
    target = [round(random.uniform(-1.2, 1.2), 3), round(random.uniform(-0.4, 0.8), 3), 0.0,
              round(random.uniform(-0.5, 0.9), 3), 0.0, round(random.uniform(-0.5, 0.9), 3), 0.0]
    r = move_run(_harness, target)
    r["target"] = target
    return r


def test_default_pose(default_run, evidence):
    """Without parameters the arm reaches the default pose [0, 0.5, 0, 1.0, 0, 0.5, 0]"""
    assert default_run["ready"], f"simulation not ready: {default_run['states']}"
    e = errors(default_run, DEFAULT)
    evidence(expected="every joint within 0.03 rad", observed=f"max error {max(e.values()):.3f} rad; node log: "
             + " | ".join(default_run["node_log"].splitlines()[-2:]),
             suggestion="Wait until pub_->get_subscription_count() > 0 before publishing, or the trajectory is lost.")
    assert all(v < 0.03 for v in e.values())


def describe(r, target):
    """Which joints missed, where they ended up, and what the node said: the evidence a student needs."""
    e = errors(r, target)
    off = [f"{j.replace('_joint', '')} {r['reached'].get(j, float('nan')):+.2f} (target {t:+.2f})"
           for j, t in zip(ARM, target) if e[j] >= 0.03]
    log = " | ".join(r.get("node_log", "").splitlines()[-2:])
    return f"max error {max(e.values()):.3f} rad; off: {', '.join(off) or 'none'}; node log: {log}"


def test_positions_parameter(param_run, evidence):
    """The arm reaches a target passed in the 'positions' parameter"""
    assert param_run["ready"]
    e = errors(param_run, param_run["target"])
    evidence(expected="every joint within 0.03 rad of the requested pose", observed=describe(param_run, param_run["target"]),
             suggestion="Use the 'positions' parameter (declare_parameter<std::vector<double>>) for the trajectory point.")
    assert all(v < 0.03 for v in e.values())
