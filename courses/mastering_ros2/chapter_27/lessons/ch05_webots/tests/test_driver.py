"""Checkpoint 'driver': your webots_driver moves the Webots robot as /cmd_vel asks and reports it on /odom, /tf,
/joint_states and /clock. The true motion comes from a supervisor the grader adds to a copy of your world."""

import math
from pathlib import Path

import pytest

from academy_grader import adapters, sim

PKG = "diffbot_webots"


@pytest.fixture(scope="module")
def run(_harness):
    h = _harness
    h.stop_all()
    proc, truth = adapters.start_webots(h, PKG, Path(__file__).parent)
    odom = sim.Odom(h, "/odom")
    r = {"truth_ok": truth.wait(60)}
    r["odom_ok"] = odom.wait(15 if r["truth_ok"] else 1)
    r["clock"] = h.collect("/clock", "rosgraph_msgs/msg/Clock", 1.0)
    h.wait_for_endpoint("/cmd_vel", "sub", node="/webots_driver", timeout=10 if r["truth_ok"] else 1)
    r["cmd_subs"] = h.endpoints("/cmd_vel")[1]
    if r["truth_ok"]:
        joints0 = h.collect("/joint_states", "sensor_msgs/msg/JointState", 0.5)
        snap = lambda: (odom.pose() if odom.msgs else None, truth.pose())  # noqa: E731
        r["s0"] = snap()
        adapters.drive(h, 4.0, v=0.2)
        r["s1"] = snap()
        joints1 = h.collect("/joint_states", "sensor_msgs/msg/JointState", 0.5)
        adapters.drive(h, 3.0, w=0.6)
        r["s2"] = snap()
        h.spin_for(1.0)
        r["s3"] = snap()
        r["joints"] = (joints0[-1][1] if joints0 else None, joints1[-1][1] if joints1 else None)
        r["tf"] = h.lookup("odom", "base_link", timeout=5)
    r["log"] = proc.output()
    r["truth_log"] = truth.errors
    truth.close()
    odom.close()
    h.stop_all()
    return r


def _ready(run):
    tail = " | ".join(l for l in run["log"].splitlines()[-6:])[-500:]
    assert run["truth_ok"], f"Webots did not start or the robot never stepped. Launch log: {tail}"


def test_clock(run, evidence):
    """The driver publishes simulated time on /clock, and it advances"""
    _ready(run)
    stamps = [m.clock.sec + m.clock.nanosec * 1e-9 for _, m in run["clock"]]
    evidence(expected="/clock messages with increasing time", observed=f"{len(stamps)} messages, "
             + (f"{stamps[0]:.2f} s → {stamps[-1]:.2f} s" if stamps else "none"),
             suggestion="The given step() publishes wb_robot_get_time() each step; keep it.")
    assert len(stamps) > 10 and stamps[-1] > stamps[0]


def test_subscribes_cmd_vel(run, evidence):
    """webots_driver subscribes to /cmd_vel with geometry_msgs/msg/Twist"""
    _ready(run)
    subs = sorted({(s["node"], s["type"]) for s in run["cmd_subs"]})
    evidence(expected="/webots_driver subscribed with geometry_msgs/msg/Twist", observed=f"{subs or 'no subscriber'}",
             suggestion="TODO 1: create_subscription<geometry_msgs::msg::Twist>(\"/cmd_vel\", 10, ...)")
    assert ("/webots_driver", "geometry_msgs/msg/Twist") in subs


def test_drives_forward(run, evidence):
    """4 s at 0.2 m/s moves the robot about 0.8 m straight ahead (Webots ground truth)"""
    _ready(run)
    dx, dy, dyaw = adapters.relative(run["s0"][1], run["s1"][1])
    evidence(expected="0.68–0.92 m forward, heading change < 6°",
             observed=f"{dx:.3f} m forward, {dy:.3f} m sideways, heading {math.degrees(dyaw):.1f}°",
             suggestion="TODO 2: both wheels at v / kWheelRadius rad/s when angular.z is zero.")
    assert 0.68 <= dx <= 0.92 and abs(dyaw) < math.radians(6)


def test_turns_in_place(run, evidence):
    """3 s at 0.6 rad/s turns the robot about 103° counter-clockwise, on the spot"""
    _ready(run)
    dx, dy, dyaw = adapters.relative(run["s1"][1], run["s2"][1])
    evidence(expected="+83° to +124° (counter-clockwise), centre moves < 5 cm",
             observed=f"{math.degrees(dyaw):+.1f}°, centre moved {math.hypot(dx, dy) * 100:.1f} cm",
             suggestion="Positive angular.z turns left: right wheel (v + w·L/2)/r, left wheel (v − w·L/2)/r.")
    assert math.radians(83) <= dyaw <= math.radians(124) and math.hypot(dx, dy) < 0.05


def test_odometry_matches_truth(run, evidence):
    """/odom (dead reckoning from the encoders) agrees with the true motion"""
    _ready(run)
    assert run["odom_ok"], "no message on /odom (TODO 4)"
    o_fwd, t_fwd = adapters.relative(run["s0"][0], run["s1"][0]), adapters.relative(run["s0"][1], run["s1"][1])
    o_turn, t_turn = adapters.relative(run["s1"][0], run["s2"][0]), adapters.relative(run["s1"][1], run["s2"][1])
    evidence(expected="straight: within 4 cm of the truth; turn: within 15°",
             observed=f"straight: odom {o_fwd[0]:.3f} m vs truth {t_fwd[0]:.3f} m; "
                      f"turn: odom {math.degrees(o_turn[2]):+.1f}° vs truth {math.degrees(t_turn[2]):+.1f}°",
             suggestion="TODO 3: ds = (dl + dr)/2, dyaw = (dr − dl)/kWheelSeparation, mid-point integration.")
    assert abs(o_fwd[0] - t_fwd[0]) < 0.04 and abs(adapters.wrap(o_turn[2] - t_turn[2])) < math.radians(15)


def test_joint_states(run, evidence):
    """/joint_states reports both wheel angles, and they advance as the wheels roll"""
    _ready(run)
    j0, j1 = run["joints"]
    assert j0 is not None and j1 is not None, "no /joint_states"
    p0, p1 = dict(zip(j0.name, j0.position)), dict(zip(j1.name, j1.position))
    rolled = {k: p1.get(k, float("nan")) - p0.get(k, float("nan")) for k in ("left_wheel_joint", "right_wheel_joint")}
    evidence(expected="each wheel ≈ +15.7 rad (0.78 m / 0.05 m) after 4 s forward",
             observed=", ".join(f"{k}: {v:+.1f} rad" for k, v in rolled.items()), suggestion="Keep the given JointState code.")
    assert all(12 < v < 19 for v in rolled.values())


def test_tf_matches_odometry(run, evidence):
    """TF odom → base_link is the odometry pose, at axle height"""
    _ready(run)
    tf = run["tf"]
    assert tf is not None, "no transform odom -> base_link (TODO 4)"
    ox, oy, _ = run["s3"][0] if run["s3"][0] else (float("nan"),) * 3
    x, y, z = (float(v) for v in tf[:3, 3])
    evidence(expected="TF translation = /odom position, z = 0.05 m", observed=f"TF ({x:.3f}, {y:.3f}, {z:.3f}); odom ({ox:.3f}, {oy:.3f})",
             suggestion="TODO 4: tf_->sendTransform with the odometry pose and translation.z = kWheelRadius.")
    assert math.hypot(x - ox, y - oy) < 0.02 and abs(z - 0.05) < 0.005
