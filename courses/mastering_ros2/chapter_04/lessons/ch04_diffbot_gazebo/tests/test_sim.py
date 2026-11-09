"""Checkpoint 'sim': ros2_control runs inside Gazebo, and the controller's model of the robot (wheel radius,
wheel separation) agrees with the PHYSICS. Odometry is compared with Gazebo's ground-truth pose."""

import math

import pytest

from academy_grader import sim

PKG, MODEL = "diffbot_sim", "diffbot"
CONTROLLERS = ["joint_state_broadcaster", "diff_drive_controller"]


@pytest.fixture(scope="module")
def run(_harness):
    h = _harness
    h.stop_all()
    proc = h.start_launch(PKG, "sim.launch.xml")
    states = sim.wait_controllers_active(h, CONTROLLERS, timeout=60)
    odom = sim.Odom(h)
    r = {"states": states, "output": proc, "odom": False}
    if all(states.get(c) == "active" for c in CONTROLLERS) and odom.wait(20):
        r["odom"] = True
        h.spin_for(1.0)
        g0, o0 = sim.gz_pose(MODEL), odom.pose()
        sim.drive(h, 3.0, vx=0.25)
        h.spin_for(1.0)
        g1, o1 = sim.gz_pose(MODEL), odom.pose()
        sim.drive(h, 3.0, wz=0.6)
        h.spin_for(1.0)
        g2, o2 = sim.gz_pose(MODEL), odom.pose()
        r.update(g=(g0, g1, g2), o=(o0, o1, o2))
    odom.close()
    r["log"] = proc.output()
    h.stop_all()
    return r


def _log_tail(r, n=4):
    return " | ".join(l for l in r["log"].splitlines() if "ERROR" in l or "error" in l.lower())[-600:] or \
        " | ".join(r["log"].splitlines()[-n:])


def test_controllers_active(run, evidence):
    """joint_state_broadcaster and diff_drive_controller are loaded and active in Gazebo"""
    evidence(expected="both controllers 'active'", observed=f"controller states: {run['states'] or 'no controller_manager'}; "
             f"launch log: {_log_tail(run)}",
             suggestion="No controller_manager means the <ros2_control>/<gazebo> plugin block is missing or wrong; "
                        "a controller stuck 'unconfigured' usually means missing parameters in controllers.yaml.")
    assert all(run["states"].get(c) == "active" for c in CONTROLLERS)


def test_robot_moves_in_physics(run, evidence):
    """Commanding 0.25 m/s for 3 s really moves the robot in the simulation"""
    assert run["odom"], "no odometry from diff_drive_controller"
    g0, g1, _ = run["g"]
    dist = math.hypot(g1[0] - g0[0], g1[1] - g0[1]) if g0 and g1 else 0.0
    evidence(expected="ground-truth displacement > 0.3 m", observed=f"{dist:.3f} m (Gazebo pose)",
             suggestion="Wheels need a VELOCITY command interface, and the wheel joint names must match the model.")
    assert dist > 0.3


def test_odometry_matches_physics_driving_straight(run, evidence):
    """Odometry distance matches the true distance (wheel_radius is right)"""
    assert run["odom"]
    (g0, g1, _), (o0, o1, _) = run["g"], run["o"]
    true = math.hypot(g1[0] - g0[0], g1[1] - g0[1])
    meas = math.hypot(o1[0] - o0[0], o1[1] - o0[1])
    ratio = meas / true if true > 1e-3 else float("inf")
    evidence(expected="odometry / ground truth within 0.85–1.15", observed=f"odom {meas:.3f} m vs true {true:.3f} m (ratio {ratio:.2f})",
             suggestion="If the ratio is far from 1, wheel_radius in controllers.yaml does not match the model.")
    assert 0.85 <= ratio <= 1.15


def test_odometry_matches_physics_turning(run, evidence):
    """Odometry rotation matches the true rotation (wheel_separation is right)"""
    assert run["odom"]
    (_, g1, g2), (_, o1, o2) = run["g"], run["o"]
    true = abs(sim.angle_diff(g2[3], g1[3]))
    meas = abs(sim.angle_diff(o2[2], o1[2]))
    ratio = meas / true if true > 1e-3 else float("inf")
    evidence(expected="odometry yaw / true yaw within 0.75–1.25", observed=f"odom {math.degrees(meas):.1f}° vs true {math.degrees(true):.1f}° (ratio {ratio:.2f})",
             suggestion="Rotation depends on wheel_separation: it must equal the distance between the wheels in the model.")
    assert true > 0.3 and 0.75 <= ratio <= 1.25
