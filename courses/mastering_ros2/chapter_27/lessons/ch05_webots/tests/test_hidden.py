"""Hidden tests for the final submission: command time-out, reported velocities, a different goal."""

import math
from pathlib import Path

import pytest

from academy_grader import adapters, sim

PKG = "diffbot_webots"
GOAL = (0.8, 0.5)


@pytest.fixture(scope="module")
def run(_harness):
    h = _harness
    h.stop_all()
    proc, truth = adapters.start_webots(h, PKG, Path(__file__).parent)
    odom = sim.Odom(h, "/odom")
    r = {"ok": truth.wait(60) and odom.wait(15)}
    if r["ok"]:
        h.spin_for(0.5)
        r["goal"] = adapters.go_to_goal(h, PKG, GOAL, truth, odom)
        # drive, then go silent WITHOUT a stop command: the driver must stop on its own
        from geometry_msgs.msg import Twist

        pub = h.node.create_publisher(Twist, "/cmd_vel", 10)
        twists = []
        for i in range(40):  # 2 s at 0.2 m/s
            m = Twist()
            m.linear.x = 0.2
            pub.publish(m)
            h.spin_for(0.05)
            if i > 20:
                twists.append(odom.msgs[-1].twist.twist.linear.x)
        h.node.destroy_publisher(pub)
        a = truth.pose()
        h.spin_for(2.5)
        b = truth.pose()
        r["coast"] = math.hypot(b[0] - a[0], b[1] - a[1])
        r["twists"] = sorted(twists)
    truth.close()
    odom.close()
    h.stop_all()
    return r


def test_other_goal(run, evidence):
    """go_to_goal honours the goal_x / goal_y parameters"""
    assert run["ok"], "Webots did not start"
    g = run["goal"]
    dx, dy, _ = adapters.relative(g["start_truth"], g["end_truth"])
    err = math.hypot(dx - GOAL[0], dy - GOAL[1])
    evidence(expected=f"reaches {GOAL} (true error < 15 cm)", observed=f"reached={g['reached']}, true error {err * 100:.1f} cm",
             suggestion="Read the goal from the parameters, not from constants.")
    assert g["reached"] and err < 0.15


def test_stops_without_commands(run, evidence):
    """When /cmd_vel goes silent the driver stops the robot within 0.5 s"""
    assert run["ok"]
    evidence(expected="< 15 cm travelled in the 2.5 s after the last command (0.5 s at 0.2 m/s ≈ 10 cm)",
             observed=f"{run['coast'] * 100:.1f} cm", suggestion="TODO 2: zero the command when it is older than kCmdTimeout.")
    assert run["coast"] < 0.15


def test_odometry_reports_velocity(run, evidence):
    """The odometry's twist reports the forward speed"""
    assert run["ok"]
    v = run["twists"][len(run["twists"]) // 2] if run["twists"] else float("nan")
    evidence(expected="twist.linear.x ≈ 0.2 m/s while driving", observed=f"median {v:.3f} m/s",
             suggestion="TODO 4: fill odom.twist.twist.linear.x = v_ and angular.z = w_.")
    assert abs(v - 0.2) < 0.04
