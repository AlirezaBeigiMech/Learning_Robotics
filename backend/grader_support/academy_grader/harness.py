"""Drive the student's real ROS 2 executables and observe them through the ROS graph.

The grader process already runs inside the student's built overlay (``install\\setup.bat``) and an
isolated ``ROS_DOMAIN_ID``, so ``ros2 run`` resolves the student's package and nothing else on the
machine can interfere.
"""

from __future__ import annotations

import contextlib
import shutil
import statistics
import subprocess
import threading
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rosidl_runtime_py.utilities import get_message

CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200


@dataclass
class RunningProcess:
    label: str
    popen: subprocess.Popen
    lines: list[str] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _pump(self) -> None:
        assert self.popen.stdout
        for raw in iter(self.popen.stdout.readline, b""):
            with self._lock:
                self.lines.append(raw.decode("utf-8", errors="replace").rstrip("\r\n"))

    def output(self) -> str:
        with self._lock:
            return "\n".join(self.lines)

    @property
    def alive(self) -> bool:
        return self.popen.poll() is None

    def stop(self) -> None:
        if self.alive:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.popen.pid)], capture_output=True,
                           creationflags=CREATE_NO_WINDOW)
        with contextlib.suppress(subprocess.TimeoutExpired):
            self.popen.wait(timeout=10)


def qos_name(v) -> str:
    return getattr(v, "name", str(v)).lower()


class RosHarness:
    def __init__(self) -> None:
        if not rclpy.ok():
            rclpy.init()
        self.node: Node = rclpy.create_node(f"_academy_grader_{uuid.uuid4().hex[:8]}")
        self.processes: list[RunningProcess] = []
        self._ros2 = shutil.which("ros2") or "ros2"

    # ------------------------------------------------------------------ processes
    def start(self, package: str, executable: str, *args: str) -> RunningProcess:
        cmd = [self._ros2, "run", package, executable, *args]
        popen = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP)
        rp = RunningProcess(f"{package}/{executable}", popen)
        threading.Thread(target=rp._pump, daemon=True).start()
        self.processes.append(rp)
        return rp

    def start_launch(self, package: str, launch_file: str, *args: str) -> RunningProcess:
        cmd = [self._ros2, "launch", package, launch_file, *args]
        popen = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP)
        rp = RunningProcess(f"{package}/{launch_file}", popen)
        threading.Thread(target=rp._pump, daemon=True).start()
        self.processes.append(rp)
        return rp

    # ------------------------------------------------------------------ TF
    def _tf(self):
        if not hasattr(self, "_tf_buffer"):
            from tf2_ros import Buffer, TransformListener

            self._tf_buffer = Buffer()
            self._tf_listener = TransformListener(self._tf_buffer, self.node, spin_thread=False)
        return self._tf_buffer

    def lookup(self, target: str, source: str, timeout: float = 15.0, joints: dict[str, float] | None = None):
        """Pose of ``source`` in ``target`` as a 4x4 matrix, from the live TF tree. If ``joints`` is given they
        are published on /joint_states first (as joint_state_publisher would) so robot_state_publisher
        recomputes TF for that configuration. Returns None if the transform never became available."""
        import numpy as np
        from rclpy.time import Time
        from sensor_msgs.msg import JointState

        from .urdf_tools import quaternion_matrix

        buf = self._tf()
        pub = self.node.create_publisher(JointState, "/joint_states", 10) if joints else None
        try:
            deadline = time.monotonic() + timeout
            settle_until = time.monotonic() + (1.0 if joints else 0.0)
            while time.monotonic() < deadline:
                if pub is not None:
                    msg = JointState()
                    msg.header.stamp = self.node.get_clock().now().to_msg()
                    msg.name, msg.position = list(joints), [float(v) for v in joints.values()]
                    pub.publish(msg)
                self.spin_for(0.1)
                if time.monotonic() >= settle_until and buf.can_transform(target, source, Time()):
                    tf = buf.lookup_transform(target, source, Time()).transform
                    return quaternion_matrix([tf.translation.x, tf.translation.y, tf.translation.z],
                                             [tf.rotation.x, tf.rotation.y, tf.rotation.z, tf.rotation.w])
            return None
        finally:
            if pub is not None:
                self.node.destroy_publisher(pub)

    def tf_frames(self) -> list[str]:
        import yaml

        # all_frames_as_yaml lists child frames only; the root appears solely as a parent.
        tree = yaml.safe_load(self._tf().all_frames_as_yaml()) or {}
        return sorted(set(tree) | {v.get("parent") for v in tree.values() if isinstance(v, dict) and v.get("parent")})

    @contextlib.contextmanager
    def run(self, package: str, executable: str, *args: str) -> Iterator[RunningProcess]:
        rp = self.start(package, executable, *args)
        try:
            yield rp
        finally:
            rp.stop()

    def stop_all(self, wait_nodes_gone: bool = True) -> None:
        for rp in self.processes:
            rp.stop()
        self.processes.clear()
        if hasattr(self, "_tf_buffer"):
            self._tf_buffer.clear()  # never let a previous test's transforms answer this test's lookups
        if wait_nodes_gone:
            # Hard-killed participants disappear after the lease (3 s with the academy Fast DDS profile).
            deadline = time.monotonic() + 8.0
            while self.node_names() and time.monotonic() < deadline:
                time.sleep(0.25)

    # ------------------------------------------------------------------ graph
    def node_names(self) -> list[str]:
        out = []
        for name, ns in self.node.get_node_names_and_namespaces():
            if not name.startswith("_"):
                out.append((ns.rstrip("/") + "/" + name) if ns not in ("", "/") else "/" + name)
        return out

    def wait_for_node(self, name: str, timeout: float = 20.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if name in self.node_names():
                return True
            time.sleep(0.2)
        return False

    def endpoints(self, topic: str) -> tuple[list[dict], list[dict]]:
        def conv(infos):
            return [{"node": (i.node_namespace.rstrip("/") + "/" + i.node_name) if i.node_namespace not in ("", "/") else "/" + i.node_name,
                     "type": i.topic_type, "reliability": qos_name(i.qos_profile.reliability),
                     "durability": qos_name(i.qos_profile.durability), "qos": i.qos_profile}
                    for i in infos if not i.node_name.startswith("_")]
        return conv(self.node.get_publishers_info_by_topic(topic)), conv(self.node.get_subscriptions_info_by_topic(topic))

    def wait_for_endpoint(self, topic: str, kind: str, node: str | None = None, timeout: float = 20.0) -> dict | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            pubs, subs = self.endpoints(topic)
            for e in pubs if kind == "pub" else subs:
                if node is None or e["node"] == node:
                    return e
            time.sleep(0.2)
        return None

    def topic_types(self) -> dict[str, list[str]]:
        return dict(self.node.get_topic_names_and_types())

    # ------------------------------------------------------------------ data
    def collect(self, topic: str, msg_type: str, seconds: float, qos: QoSProfile | None = None) -> list[tuple[float, object]]:
        """Subscribe (default: reliable/volatile, depth 10 — what a standard subscriber would use) and collect."""
        samples: list[tuple[float, object]] = []
        qos = qos or QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.VOLATILE)
        sub = self.node.create_subscription(get_message(msg_type), topic, lambda m: samples.append((time.monotonic(), m)), qos)
        try:
            self.spin_for(seconds)
        finally:
            self.node.destroy_subscription(sub)
        return samples

    def spin_for(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=min(0.05, max(0.0, deadline - time.monotonic())))

    def publish_values(self, topic: str, msg_type: str, values: list, period: float = 0.2,
                       wait_for_subscriber: float = 15.0, qos: QoSProfile | None = None) -> bool:
        """Publish ``values`` into ``msg.data`` once a subscriber has matched. Returns False if none matched."""
        qos = qos or QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.VOLATILE)
        pub = self.node.create_publisher(get_message(msg_type), topic, qos)
        try:
            deadline = time.monotonic() + wait_for_subscriber
            while pub.get_subscription_count() == 0 and time.monotonic() < deadline:
                self.spin_for(0.1)
            if pub.get_subscription_count() == 0:
                return False
            self.spin_for(0.5)  # let the matched reader finish its handshake
            cls = get_message(msg_type)
            for v in values:
                msg = cls()
                msg.data = v
                pub.publish(msg)
                self.spin_for(period)
            self.spin_for(0.5)
            return True
        finally:
            self.node.destroy_publisher(pub)

    @staticmethod
    def rate(samples: list[tuple[float, object]]) -> float:
        if len(samples) < 3:
            return 0.0
        gaps = [b[0] - a[0] for a, b in zip(samples, samples[1:])]
        med = statistics.median(gaps)
        return 1.0 / med if med > 0 else 0.0

    def close(self) -> None:
        self.stop_all(wait_nodes_gone=False)
        self.node.destroy_node()
