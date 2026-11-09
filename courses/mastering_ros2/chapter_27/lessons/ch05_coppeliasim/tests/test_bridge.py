"""Checkpoint 'bridge': your CoppeliaSim add-on moves the robot as /cmd_vel asks and reports it on /odom and /tf.
How far the robot really moved is measured with the simulator's true pose (/ground_truth), not your odometry."""

import math

import pytest

from academy_grader import adapters, sim

PKG = "diffbot_coppelia"


@pytest.fixture(scope="module")
def run(_harness):
    h = _harness
    h.stop_all()
    proc = h.start_launch(PKG, "sim.launch.xml")
    truth, odom = adapters.Truth(h), sim.Odom(h, "/odom")
    r = {"truth_ok": truth.wait(60)}
    r["odom_ok"] = odom.wait(10 if r["truth_ok"] else 1)
    h.wait_for_endpoint("/cmd_vel", "sub", timeout=10 if r["truth_ok"] else 1)  # discovery can lag the first data
    r["cmd_subs"] = h.endpoints("/cmd_vel")[1]
    if r["truth_ok"]:
        snap = lambda: (odom.pose() if odom.msgs else None, truth.pose())  # noqa: E731
        h.spin_for(1.0)
        r["s0"] = snap()
        adapters.drive(h, 4.0, v=0.2)
        r["s1"] = snap()
        adapters.drive(h, 3.0, w=0.6)
        r["s2"] = snap()
        h.spin_for(1.0)
        r["s3"] = snap()
        r["tf"] = h.lookup("odom", "base_link", timeout=5)
    r["log"] = proc.output()
    truth.close()
    odom.close()
    h.stop_all()
    return r


def _ready(run):
    errors = [l for l in run["log"].splitlines() if ":error]" in l]
    assert run["truth_ok"], "CoppeliaSim did not start (no /ground_truth). " + " | ".join(errors[-3:])[-500:]


def test_subscribes_cmd_vel(run, evidence):
    """The bridge subscribes to /cmd_vel with geometry_msgs/msg/Twist"""
    _ready(run)
    types = sorted({s["type"] for s in run["cmd_subs"]})
    evidence(expected="a subscriber on /cmd_vel of type geometry_msgs/msg/Twist", observed=f"subscriber types: {types or 'none'}",
             suggestion="TODO 1: simROS2.createSubscription('/cmd_vel', 'geometry_msgs/msg/Twist', callback)")
    assert "geometry_msgs/msg/Twist" in types


def test_drives_forward(run, evidence):
    """4 s at 0.2 m/s moves the robot about 0.8 m straight ahead (simulator ground truth)"""
    _ready(run)
    dx, dy, dyaw = adapters.relative(run["s0"][1], run["s1"][1])
    evidence(expected="0.68–0.92 m forward, heading change < 6°",
             observed=f"{dx:.3f} m forward, {dy:.3f} m sideways, heading {math.degrees(dyaw):.1f}°",
             suggestion="TODO 3: both wheels turn at v / WHEEL_RADIUS rad/s when angular.z is zero.")
    assert 0.68 <= dx <= 0.92 and abs(dyaw) < math.radians(6)


def test_turns_in_place(run, evidence):
    """3 s at 0.6 rad/s turns the robot about 103° counter-clockwise, on the spot"""
    _ready(run)
    dx, dy, dyaw = adapters.relative(run["s1"][1], run["s2"][1])
    evidence(expected="+83° to +124° (counter-clockwise), centre moves < 5 cm",
             observed=f"{math.degrees(dyaw):+.1f}°, centre moved {math.hypot(dx, dy) * 100:.1f} cm",
             suggestion="Positive angular.z turns LEFT: the right wheel turns faster (v + w·L/2), the left slower (v − w·L/2). "
                        "L is the full wheel separation.")
    assert math.radians(83) <= dyaw <= math.radians(124) and math.hypot(dx, dy) < 0.05


def test_odometry_matches_truth(run, evidence):
    """/odom (from the wheel encoders) agrees with the true motion"""
    _ready(run)
    assert run["odom_ok"], "no message on /odom (TODO 2 and TODO 5)"
    o_fwd, t_fwd = adapters.relative(run["s0"][0], run["s1"][0]), adapters.relative(run["s0"][1], run["s1"][1])
    o_turn, t_turn = adapters.relative(run["s1"][0], run["s2"][0]), adapters.relative(run["s1"][1], run["s2"][1])
    d_err = abs(o_fwd[0] - t_fwd[0])
    yaw_err = abs(adapters.wrap(o_turn[2] - t_turn[2]))
    evidence(expected="straight: odometry within 6 cm of the truth; turn: within 15°",
             observed=f"straight: odom {o_fwd[0]:.3f} m vs truth {t_fwd[0]:.3f} m; "
                      f"turn: odom {math.degrees(o_turn[2]):+.1f}° vs truth {math.degrees(t_turn[2]):+.1f}°",
             suggestion="TODO 4: ds = (dl + dr) / 2 and dyaw = (dr − dl) / WHEEL_SEPARATION; move along the heading at "
                        "the middle of the step. A small error is normal: the wheels slip a little in a turn.")
    assert d_err < 0.06 and yaw_err < math.radians(15)


def test_tf_matches_odometry(run, evidence):
    """TF odom → base_link is the odometry pose, at axle height"""
    _ready(run)
    tf = run["tf"]
    assert tf is not None, "no transform odom -> base_link on /tf (TODO 6)"
    ox, oy, _ = run["s3"][0] if run["s3"][0] else (float("nan"),) * 3
    x, y, z = (float(v) for v in tf[:3, 3])
    evidence(expected="TF translation = /odom position, z = 0.05 m", observed=f"TF ({x:.3f}, {y:.3f}, {z:.3f}); odom ({ox:.3f}, {oy:.3f})",
             suggestion="TODO 6: send the same x, y and yaw as the odometry, with translation.z = WHEEL_RADIUS.")
    assert math.hypot(x - ox, y - oy) < 0.02 and abs(z - 0.05) < 0.005


def test_stops(run, evidence):
    """With zero velocity commanded the robot stays where it is"""
    _ready(run)
    dx, dy, dyaw = adapters.relative(run["s2"][1], run["s3"][1])
    evidence(expected="< 1 cm and < 1° in the second after the stop command", observed=f"{math.hypot(dx, dy) * 100:.2f} cm, {math.degrees(dyaw):.2f}°",
             suggestion="Command the wheel speeds every step from the latest /cmd_vel, including zero.")
    assert math.hypot(dx, dy) < 0.01 and abs(dyaw) < math.radians(1)
