"""Helpers for Chapter 5's simulator adapters (CoppeliaSim and Webots bridges with the portable contract):
/cmd_vel (geometry_msgs/Twist) in, /odom (nav_msgs/Odometry) out, plus a simulator-side ground truth."""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000


def yaw_of(q) -> float:
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def wrap(a: float) -> float:
    return math.atan2(math.sin(a), math.cos(a))


def relative(p0: tuple[float, float, float], p1: tuple[float, float, float]) -> tuple[float, float, float]:
    """Pose p1 expressed in the frame of p0 (x forward, y left at p0): (dx, dy, dyaw). Odometry and ground truth
    start in different frames, so they are compared through these relative motions."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    c, s = math.cos(p0[2]), math.sin(p0[2])
    return c * dx + s * dy, -s * dx + c * dy, wrap(p1[2] - p0[2])


class Truth:
    """Latest pose from a ground-truth Odometry topic (CoppeliaSim's /ground_truth)."""

    def __init__(self, h, topic: str = "/ground_truth") -> None:
        from nav_msgs.msg import Odometry

        self.h, self.msgs = h, []
        self.sub = h.node.create_subscription(Odometry, topic, self.msgs.append, 10)

    def wait(self, timeout: float = 60.0) -> bool:
        end = time.monotonic() + timeout
        while not self.msgs and time.monotonic() < end:
            self.h.spin_for(0.1)
        return bool(self.msgs)

    def pose(self) -> tuple[float, float, float]:
        p = self.msgs[-1].pose.pose
        return p.position.x, p.position.y, yaw_of(p.orientation)

    def close(self) -> None:
        self.h.node.destroy_subscription(self.sub)


class WebotsTruth:
    """The true pose of the Webots robot `DEF <def_name>`, read by a supervisor robot that the grader adds to a COPY
    of the student's world. The supervisor runs in its own process (the Webots controller library can connect only
    once per process) and prints one JSON pose per simulated 50 ms."""

    SUPERVISOR = '\nRobot {\n  name "academy_truth"\n  supervisor TRUE\n  controller "<extern>"\n}\n'

    @classmethod
    def prepare_world(cls, src: Path, dst: Path) -> Path:
        dst.write_text(src.read_text(encoding="utf-8") + cls.SUPERVISOR, encoding="utf-8")
        return dst

    def __init__(self, def_name: str = "DIFFBOT") -> None:
        port = os.environ["ACADEMY_SIM_PORT"]
        env = dict(os.environ, WEBOTS_CONTROLLER_URL=f"ipc://{port}/academy_truth")
        self.proc = subprocess.Popen([sys.executable, "-u", str(Path(__file__).with_name("webots_truth.py")), def_name],
                                     env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                     creationflags=CREATE_NO_WINDOW)
        self.poses: list[tuple[float, float, float, float]] = []  # (sim time, x, y, yaw)
        self.errors: list[str] = []
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self) -> None:
        assert self.proc.stdout
        for line in self.proc.stdout:
            try:
                d = json.loads(line)
                self.poses.append((d["t"], d["x"], d["y"], d["yaw"]))
            except (json.JSONDecodeError, KeyError):
                self.errors.append(line.rstrip())

    def wait(self, timeout: float = 60.0) -> bool:
        end = time.monotonic() + timeout
        while not self.poses and time.monotonic() < end and self.proc.poll() is None:
            time.sleep(0.1)
        return bool(self.poses)

    def pose(self) -> tuple[float, float, float]:
        return self.poses[-1][1:]

    def sim_time(self) -> float:
        return self.poses[-1][0] if self.poses else 0.0

    def close(self) -> None:
        if self.proc.poll() is None:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)], capture_output=True,
                           creationflags=CREATE_NO_WINDOW)


def start_webots(h, package: str, work_dir: Path, *launch_args: str, launch: str = "sim.launch.xml"):
    """Launch the student's Webots bring-up on a copy of their world that also holds the grader's supervisor.
    Returns (launch process, WebotsTruth). The launch file must accept a `world` argument."""
    from ament_index_python.packages import get_package_share_directory

    world = Path(get_package_share_directory(package)) / "worlds" / "diffbot.wbt"
    graded = WebotsTruth.prepare_world(world, work_dir / f"graded_{package}.wbt")
    proc = h.start_launch(package, launch, f"world:={graded}", *launch_args)
    return proc, WebotsTruth()


def go_to_goal(h, package: str, goal: tuple[float, float] | None, truth, odom, timeout: float = 45.0) -> dict:
    """Run the student's go_to_goal (optionally with goal_x/goal_y) until it logs "Goal reached", then 2 s more to see
    that the robot rests, and stop it. Returns the true start/end/rest poses, the odometry's end pose and the log."""
    args = ["--ros-args", "-p", f"goal_x:={goal[0]}", "-p", f"goal_y:={goal[1]}"] if goal else []
    start_truth, start_odom = truth.pose(), odom.pose()
    node = h.start(package, "go_to_goal", *args)
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout and "Goal reached" not in node.output():
        h.spin_for(0.25)
    reached = "Goal reached" in node.output()
    h.spin_for(1.0)
    end_truth = truth.pose()
    h.spin_for(1.0)
    rest_truth = truth.pose()
    node.stop()  # it keeps publishing zero velocity; later commands must not compete with it
    return {"reached": reached, "seconds": time.monotonic() - t0, "start_truth": start_truth, "start_odom": start_odom,
            "end_truth": end_truth, "rest_truth": rest_truth, "end_odom": odom.pose(), "log": node.output()}


def drive(h, seconds: float, v: float = 0.0, w: float = 0.0, topic: str = "/cmd_vel", settle: float = 1.0,
          send_stop: bool = True) -> None:
    """Command geometry_msgs/Twist (v, w) at 20 Hz for `seconds` of wall time, then zero (unless send_stop is False,
    which simply goes silent) and wait `settle` seconds."""
    from geometry_msgs.msg import Twist

    pub = h.node.create_publisher(Twist, topic, 10)
    try:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            m = Twist()
            m.linear.x, m.angular.z = float(v), float(w)
            pub.publish(m)
            h.spin_for(0.05)
        if send_stop:
            for _ in range(10):
                pub.publish(Twist())
                h.spin_for(0.05)
        h.spin_for(settle)
    finally:
        h.node.destroy_publisher(pub)
