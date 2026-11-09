"""Hidden tests for the final submission: odometry on a curved path, velocities in the odometry, wheel frames."""

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
    r = {"ok": truth.wait(60) and odom.wait(10)}
    if r["ok"]:
        h.spin_for(1.0)
        r["s0"] = (odom.pose(), truth.pose())
        # an arc: while moving, sample the reported velocities
        from geometry_msgs.msg import Twist

        pub = h.node.create_publisher(Twist, "/cmd_vel", 10)
        twists = []
        for i in range(80):  # 4 s at 20 Hz
            m = Twist()
            m.linear.x, m.angular.z = 0.15, 0.4
            pub.publish(m)
            h.spin_for(0.05)
            if i > 30:
                t = odom.msgs[-1].twist.twist
                twists.append((t.linear.x, t.angular.z))
        adapters.drive(h, 0.5)
        r["s1"] = (odom.pose(), truth.pose())
        r["twists"] = twists
        r["wheel_tf"] = h.lookup("base_link", "left_wheel_link", timeout=5)
    r["log"] = proc.output()
    truth.close()
    odom.close()
    h.stop_all()
    return r


def test_odometry_on_an_arc(run, evidence):
    """On a curved path, the odometry position stays within 6 cm of the true motion"""
    assert run["ok"], "CoppeliaSim or /odom did not start"
    o = adapters.relative(run["s0"][0], run["s1"][0])
    t = adapters.relative(run["s0"][1], run["s1"][1])
    err = math.hypot(o[0] - t[0], o[1] - t[1])
    evidence(expected="position error < 6 cm, heading error < 12°",
             observed=f"odom ({o[0]:.3f}, {o[1]:.3f}, {math.degrees(o[2]):.0f}°) vs truth ({t[0]:.3f}, {t[1]:.3f}, {math.degrees(t[2]):.0f}°)",
             suggestion="Integrate x and y with the heading (cos/sin of yaw), not only along the x axis.")
    assert err < 0.06 and abs(adapters.wrap(o[2] - t[2])) < math.radians(12)


def test_odometry_reports_velocity(run, evidence):
    """The odometry's twist reports the robot's speed and turn rate"""
    assert run["ok"]
    vs = sorted(v for v, _ in run["twists"])
    ws = sorted(w for _, w in run["twists"])
    v, w = vs[len(vs) // 2], ws[len(ws) // 2]
    evidence(expected="twist.linear.x ≈ 0.15 m/s and twist.angular.z ≈ 0.4 rad/s while driving the arc",
             observed=f"median linear.x {v:.3f}, angular.z {w:.3f}",
             suggestion="Fill twist.twist.linear.x = odom.v and twist.twist.angular.z = odom.w (TODO 5).")
    assert abs(v - 0.15) < 0.04 and abs(w - 0.4) < 0.1


def test_wheel_frames(run, evidence):
    """The wheel links are in TF, 16 cm to each side of base_link"""
    assert run["ok"]
    tf = run["wheel_tf"]
    assert tf is not None, "no transform base_link -> left_wheel_link"
    y = float(tf[1, 3])
    evidence(expected="left_wheel_link at y = +0.16 m", observed=f"y = {y:.3f} m", suggestion="Keep publishWheelTransforms().")
    assert abs(y - 0.16) < 0.005
