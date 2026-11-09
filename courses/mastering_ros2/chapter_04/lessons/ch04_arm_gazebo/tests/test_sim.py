"""Checkpoint 'sim': the arm's ros2_control interfaces and trajectory controllers work inside Gazebo.
The grader itself sends trajectories here; your own node is tested in the 'move' checkpoint."""

import random

import pytest

from academy_grader import sim

PKG = "arm_sim"
CONTROLLERS = ["joint_state_broadcaster", "arm_controller", "gripper_controller"]
ARM = ["shoulder_pan_joint", "shoulder_pitch_joint", "elbow_roll_joint", "elbow_pitch_joint",
       "wrist_roll_joint", "wrist_pitch_joint", "gripper_roll_joint"]
FINGERS = ["left_finger_joint", "right_finger_joint"]


def random_arm_target(rng: random.Random) -> list[float]:
    # Inside the joint limits AND floor-safe: with these pitch ranges no link comes within 12 cm of the ground
    # (checked by forward kinematics on 20 000 samples); wider ranges occasionally folded the arm into the floor.
    return [round(rng.uniform(-1.5, 1.5), 3), round(rng.uniform(-0.6, 0.8), 3), round(rng.uniform(-1.5, 0.5), 3),
            round(rng.uniform(-0.8, 0.9), 3), round(rng.uniform(-1.5, 1.5), 3), round(rng.uniform(-0.8, 0.9), 3),
            round(rng.uniform(-1.5, 1.5), 3)]


@pytest.fixture(scope="module")
def run(_harness):
    h = _harness
    h.stop_all()
    proc = h.start_launch(PKG, "sim.launch.xml")
    states = sim.wait_controllers_active(h, CONTROLLERS, timeout=60)
    joints = sim.Joints(h)
    r = {"states": states, "joints_seen": sorted(joints.settle(2.0))}
    if all(states.get(c) == "active" for c in CONTROLLERS):
        target = random_arm_target(random.Random())
        sim.send_trajectory(h, "/arm_controller/joint_trajectory", ARM, target, seconds=2.0)
        sim.send_trajectory(h, "/gripper_controller/joint_trajectory", FINGERS, [0.02, 0.02], seconds=1.0)
        reached = joints.settle(4.0)
        r.update(target=target, reached=reached)
    joints.close()
    r["log"] = proc.output()
    h.stop_all()
    return r


def test_controllers_active(run, evidence):
    """joint_state_broadcaster, arm_controller and gripper_controller are active in Gazebo"""
    errors = " | ".join(l for l in run["log"].splitlines() if "ERROR" in l)[-600:]
    evidence(expected="all three controllers 'active'", observed=f"states: {run['states'] or 'no controller_manager'}; {errors}",
             suggestion="No controller_manager: check the <ros2_control>/<gazebo> plugin block. 'unconfigured': a joint "
                        "list in controllers.yaml is empty or names a joint without interfaces.")
    assert all(run["states"].get(c) == "active" for c in CONTROLLERS)


def test_all_joints_reported(run, evidence):
    """/joint_states reports all nine controlled joints from the simulation"""
    missing = sorted(set(ARM + FINGERS) - set(run["joints_seen"]))
    evidence(expected="7 arm joints + 2 finger joints", observed=f"missing: {missing or 'none'}",
             suggestion="Every joint needs a <joint> entry with state interfaces inside <ros2_control>.")
    assert not missing


def test_arm_follows_trajectory(run, evidence):
    """A trajectory sent by the grader brings every arm joint to its target"""
    assert "reached" in run, "controllers were not active"
    errs = {j: abs(run["reached"].get(j, float("nan")) - t) for j, t in zip(ARM, run["target"])}
    worst = max(errs, key=lambda j: errs[j] if errs[j] == errs[j] else 1e9)
    evidence(expected="every joint within 0.03 rad of the target", observed=f"worst: {worst} off by {errs[worst]:.3f} rad",
             suggestion="arm_controller must list the seven joints with position command interfaces.")
    assert all(e < 0.03 for e in errs.values())


def test_gripper_opens(run, evidence):
    """The gripper controller opens both fingers"""
    assert "reached" in run, "controllers were not active"
    pos = [run["reached"].get(f, float("nan")) for f in FINGERS]
    evidence(expected="both fingers at 0.020 m", observed=f"left {pos[0]:.4f}, right {pos[1]:.4f}",
             suggestion="gripper_controller must command both finger joints.")
    assert all(abs(p - 0.02) < 0.003 for p in pos)
