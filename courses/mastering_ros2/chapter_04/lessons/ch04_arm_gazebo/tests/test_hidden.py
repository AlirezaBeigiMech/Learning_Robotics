"""Hidden test for the final submission: a pose and duration you have not seen."""

import random
import time

from academy_grader import sim
from test_move import ARM, CONTROLLERS, PKG, errors


def test_hidden_slow_trajectory_to_unseen_pose(ros, evidence):
    """A slow trajectory (duration parameter) reaches an unseen pose, and not before its time"""
    target = [round(random.uniform(-1.0, 1.0), 3), 0.8, round(random.uniform(-1.0, 1.0), 3), 0.9, 0.0, 0.6, 0.0]
    duration = 6.0
    ros.start_launch(PKG, "sim.launch.xml")
    assert all(sim.wait_controllers_active(ros, CONTROLLERS, 60).get(c) == "active" for c in CONTROLLERS)
    joints = sim.Joints(ros)
    joints.settle(1.0)
    ros.start(PKG, "move_arm", "--ros-args", "-p", "positions:=[" + ",".join(f"{v:.3f}" for v in target) + "]",
              "-p", f"duration:={duration}")
    # Time the motion in SIMULATION time from when the arm actually starts moving (node start-up and the
    # real-time factor both vary, so wall-clock timing would be flaky).
    clock = sim.SimClock(ros)
    start = time.monotonic()
    while time.monotonic() - start < 20.0 and abs(joints.positions.get("elbow_pitch_joint", 0.0)) < 0.02:
        joints.settle(0.05)
    clock.wait(3.0)  # half-way through a 6 s trajectory; a 2 s one would already be finished
    early = joints.positions.get("elbow_pitch_joint")
    clock.wait(5.0)
    final = {"reached": joints.settle(1.0)}
    clock.close()
    joints.close()
    evidence(expected="3 s (sim time) after the motion starts, a 6 s trajectory is still well short of the target; it arrives later (±0.03 rad)",
             suggestion="Use the 'duration' parameter for time_from_start.")
    assert early is not None and abs(early - 0.9) > 0.2
    assert all(v < 0.03 for v in errors(final, target).values())
