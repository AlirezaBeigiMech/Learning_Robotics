"""Simulation helpers for behavioural tests (Chapter 4+): controllers, Gazebo ground truth, driving, joints.

Gazebo runs headless in the grader's own GZ_PARTITION (set by the platform), so `gz model` only ever sees
the simulation started by this test run.
"""

from __future__ import annotations

import math
import re
import subprocess
import time

CREATE_NO_WINDOW = 0x08000000


def wait_controllers_active(h, names: list[str], timeout: float = 60.0,
                            manager: str = "/controller_manager") -> dict[str, str]:
    """Poll list_controllers until every name is 'active' (or timeout). Returns the last seen states."""
    from controller_manager_msgs.srv import ListControllers

    client = h.node.create_client(ListControllers, f"{manager}/list_controllers")
    states: dict[str, str] = {}
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            if client.wait_for_service(timeout_sec=0.5):
                future = client.call_async(ListControllers.Request())
                end = time.monotonic() + 3.0
                while not future.done() and time.monotonic() < end:
                    h.spin_for(0.05)
                if future.done() and future.result() is not None:
                    states = {c.name: c.state for c in future.result().controller}
                    if all(states.get(n) == "active" for n in names):
                        return states
            h.spin_for(0.5)
        return states
    finally:
        h.node.destroy_client(client)


def gz_pose(model: str, timeout: float = 20.0) -> tuple[float, float, float, float] | None:
    """Ground-truth (x, y, z, yaw) of a model straight from the physics engine (`gz model -m <name> -p`)."""
    try:
        out = subprocess.run(f"gz model -m {model} -p", shell=True, capture_output=True, text=True, timeout=timeout,
                             creationflags=CREATE_NO_WINDOW).stdout
    except subprocess.TimeoutExpired:
        return None
    vecs = re.findall(r"\[\s*(-?[\d.e+-]+)\s+(-?[\d.e+-]+)\s+(-?[\d.e+-]+)\s*\]", out)
    if len(vecs) < 2:
        return None
    (x, y, z), (_, _, yaw) = [tuple(float(v) for v in vec) for vec in vecs[-2:]]
    return x, y, z, yaw


def drive(h, seconds: float, vx: float = 0.0, wz: float = 0.0, topic: str = "/diff_drive_controller/cmd_vel") -> None:
    """Command a velocity for `seconds` of wall time at 20 Hz, then command zero (TwistStamped, as in Jazzy)."""
    from geometry_msgs.msg import TwistStamped

    pub = h.node.create_publisher(TwistStamped, topic, 10)
    try:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            m = TwistStamped()
            m.header.stamp = h.node.get_clock().now().to_msg()
            m.twist.linear.x, m.twist.angular.z = vx, wz
            pub.publish(m)
            h.spin_for(0.05)
        for _ in range(10):
            pub.publish(TwistStamped())
            h.spin_for(0.05)
    finally:
        h.node.destroy_publisher(pub)


class Odom:
    """Latest odometry from the controller."""

    def __init__(self, h, topic: str = "/diff_drive_controller/odom") -> None:
        from nav_msgs.msg import Odometry

        self.h = h
        self.msgs: list = []
        self.sub = h.node.create_subscription(Odometry, topic, self.msgs.append, 10)

    def wait(self, timeout: float = 30.0) -> bool:
        end = time.monotonic() + timeout
        while not self.msgs and time.monotonic() < end:
            self.h.spin_for(0.1)
        return bool(self.msgs)

    def pose(self) -> tuple[float, float, float]:
        p = self.msgs[-1].pose.pose
        q = p.orientation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        return p.position.x, p.position.y, yaw

    def speed(self) -> float:
        t = self.msgs[-1].twist.twist
        return math.hypot(t.linear.x, t.linear.y) + abs(t.angular.z)

    def close(self) -> None:
        self.h.node.destroy_subscription(self.sub)


class Joints:
    """Latest positions from /joint_states."""

    def __init__(self, h) -> None:
        from sensor_msgs.msg import JointState

        self.h = h
        self.positions: dict[str, float] = {}
        self.sub = h.node.create_subscription(JointState, "/joint_states",
                                              lambda m: self.positions.update(zip(m.name, m.position)), 10)

    def settle(self, seconds: float) -> dict[str, float]:
        self.h.spin_for(seconds)
        return dict(self.positions)

    def close(self) -> None:
        self.h.node.destroy_subscription(self.sub)


def send_trajectory(h, topic: str, joints: list[str], positions: list[float], seconds: float = 2.0) -> None:
    from builtin_interfaces.msg import Duration
    from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

    pub = h.node.create_publisher(JointTrajectory, topic, 10)
    try:
        end = time.monotonic() + 5.0
        while pub.get_subscription_count() == 0 and time.monotonic() < end:
            h.spin_for(0.1)
        msg = JointTrajectory()
        msg.joint_names = list(joints)
        pt = JointTrajectoryPoint()
        pt.positions = [float(p) for p in positions]
        pt.time_from_start = Duration(sec=int(seconds), nanosec=int((seconds % 1) * 1e9))
        msg.points = [pt]
        pub.publish(msg)
        h.spin_for(0.3)
    finally:
        h.node.destroy_publisher(pub)


def angle_diff(a: float, b: float) -> float:
    return math.atan2(math.sin(a - b), math.cos(a - b))


class SimClock:
    """Simulation time from /clock. Timing assertions in simulation tests must use this, never the wall
    clock: the real-time factor varies with machine load (observed 0.7-0.9 on the same PC)."""

    def __init__(self, h) -> None:
        from rosgraph_msgs.msg import Clock

        self.h = h
        self.now: float | None = None
        self.sub = h.node.create_subscription(Clock, "/clock", self._on, 10)

    def _on(self, msg) -> None:
        self.now = msg.clock.sec + msg.clock.nanosec * 1e-9

    def wait(self, seconds: float, wall_timeout: float = 60.0) -> bool:
        """Spin until `seconds` of simulation time have passed."""
        end_wall = time.monotonic() + wall_timeout
        while self.now is None and time.monotonic() < end_wall:
            self.h.spin_for(0.05)
        if self.now is None:
            return False
        target = self.now + seconds
        while self.now < target and time.monotonic() < end_wall:
            self.h.spin_for(0.02)
        return self.now >= target

    def close(self) -> None:
        self.h.node.destroy_subscription(self.sub)
