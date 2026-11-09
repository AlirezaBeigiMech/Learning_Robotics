"""Checkpoint 'drive': your drive_forward node moves the simulated robot the requested distance (measured by
Gazebo, not by your own odometry) and then stops."""

import math
import time

import pytest

from academy_grader import sim

PKG, MODEL = "diffbot_sim", "diffbot"
CONTROLLERS = ["joint_state_broadcaster", "diff_drive_controller"]


def drive_run(h, *args, timeout=45.0):
    """Start the sim and the student's node; wait until the robot has moved and come to rest."""
    h.stop_all()
    h.start_launch(PKG, "sim.launch.xml")
    states = sim.wait_controllers_active(h, CONTROLLERS, timeout=60)
    odom = sim.Odom(h)
    r = {"states": states, "ready": all(states.get(c) == "active" for c in CONTROLLERS) and odom.wait(20)}
    if r["ready"]:
        h.spin_for(1.0)
        g0 = sim.gz_pose(MODEL)
        node = h.start(PKG, "drive_forward", *args)
        start, moved, still_since = time.monotonic(), False, None
        while time.monotonic() - start < timeout:
            h.spin_for(0.2)
            speed = odom.speed()
            moved = moved or speed > 0.05
            if moved and speed < 0.01:
                still_since = still_since or time.monotonic()
                if time.monotonic() - still_since > 1.5:
                    break
            else:
                still_since = None
        g1 = sim.gz_pose(MODEL)
        h.spin_for(2.0)
        g2 = sim.gz_pose(MODEL)
        r.update(moved=moved, g=(g0, g1, g2), node_log=node.output(), elapsed=time.monotonic() - start)
    odom.close()
    h.stop_all()
    return r


@pytest.fixture(scope="module")
def run(_harness):
    return drive_run(_harness)


def test_drives_one_metre(run, evidence):
    """With default parameters the robot travels 1.0 m (±10 %, Gazebo ground truth)"""
    assert run["ready"], f"simulation not ready: {run['states']}"
    g0, g1, _ = run["g"]
    d = math.hypot(g1[0] - g0[0], g1[1] - g0[1])
    evidence(expected="0.90–1.10 m travelled", observed=f"{d:.3f} m in {run['elapsed']:.0f} s; node log: "
             + " | ".join(run["node_log"].splitlines()[-2:]),
             suggestion="Publish TwistStamped on /diff_drive_controller/cmd_vel and stop when the odometry distance reaches 'distance'.")
    assert 0.9 <= d <= 1.1


def test_drives_straight(run, evidence):
    """The robot keeps its heading (it does not turn on the way)"""
    assert run["ready"]
    g0, g1, _ = run["g"]
    dyaw = abs(sim.angle_diff(g1[3], g0[3]))
    evidence(expected="heading change < 6°", observed=f"{math.degrees(dyaw):.1f}°",
             suggestion="Command only linear.x; leave angular.z at zero.")
    assert dyaw < math.radians(6)


def test_stops_and_stays_stopped(run, evidence):
    """After reaching the goal the robot stays where it is"""
    assert run["ready"] and run["moved"], "the robot never moved"
    _, g1, g2 = run["g"]
    drift = math.hypot(g2[0] - g1[0], g2[1] - g1[1])
    evidence(expected="< 2 cm movement in the 2 s after stopping", observed=f"{drift * 100:.1f} cm",
             suggestion="Once the distance is reached keep publishing zero velocity (or stop publishing).")
    assert drift < 0.02
