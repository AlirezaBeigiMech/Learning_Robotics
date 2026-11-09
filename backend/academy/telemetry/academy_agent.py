"""Academy telemetry agent — a hidden rclpy node in the student's DDS domain.

Protocol: JSON lines. Commands arrive on stdin, events leave on stdout.
  in : {"cmd": "echo", "topic": "/numbers"} | {"cmd": "stop_echo", "topic": "/numbers"} | {"cmd": "snapshot"}
  out: {"type": "graph", ...} | {"type": "echo", ...} | {"type": "echo_stats", ...} | {"type": "error", ...}

Everything reported here is observed from the live ROS 2 graph; nothing is synthesised.
"""

from __future__ import annotations

import json
import queue
import sys
import threading
import time
from collections import deque

import rclpy
import rclpy.executors
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

try:
    from rclpy.qos import QoSCompatibility, qos_check_compatible
except ImportError:  # pragma: no cover
    qos_check_compatible = None

try:
    from rclpy.action.graph import get_action_client_names_and_types_by_node, get_action_server_names_and_types_by_node
except ImportError:  # pragma: no cover
    get_action_client_names_and_types_by_node = get_action_server_names_and_types_by_node = None

from rosidl_runtime_py.convert import message_to_ordereddict
from rosidl_runtime_py.utilities import get_message

AGENT_NAME = "_academy_telemetry"
SYSTEM_TOPICS = {"/rosout", "/parameter_events"}
SYSTEM_SERVICE_SUFFIXES = (
    "/describe_parameters", "/get_parameter_types", "/get_parameters", "/list_parameters",
    "/set_parameters", "/set_parameters_atomically", "/get_type_description",
)
MAX_ECHO_HZ = 10.0
_out_lock = threading.Lock()


def emit(obj: dict) -> None:
    line = json.dumps(obj, default=str)
    with _out_lock:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()


def qos_dict(q) -> dict:
    def name(v):
        return getattr(v, "name", str(v)).lower()

    # History and depth are local to each endpoint and are not exchanged during DDS discovery,
    # so remote endpoints report them as unknown; we say so instead of showing a misleading 0.
    known = name(q.history) not in ("unknown", "system_default")
    return {"reliability": name(q.reliability), "durability": name(q.durability),
            "history": name(q.history) if known else None, "depth": q.depth if known else None}


def qos_compat(pub_q, sub_q) -> tuple[str, str]:
    if qos_check_compatible is not None:
        try:
            c, reason = qos_check_compatible(pub_q, sub_q)
            return {QoSCompatibility.OK: "ok", QoSCompatibility.WARNING: "warning"}.get(c, "error"), reason
        except Exception:
            pass
    if pub_q.reliability == ReliabilityPolicy.BEST_EFFORT and sub_q.reliability == ReliabilityPolicy.RELIABLE:
        return "error", "Publisher is BEST_EFFORT but subscription requires RELIABLE"
    if pub_q.durability == DurabilityPolicy.VOLATILE and sub_q.durability == DurabilityPolicy.TRANSIENT_LOCAL:
        return "error", "Publisher is VOLATILE but subscription requires TRANSIENT_LOCAL"
    return "ok", ""


def fqn(name: str, ns: str) -> str:
    return (ns.rstrip("/") + "/" + name) if ns not in ("", "/") else "/" + name


def flatten_numeric(d, prefix="", out=None, limit=24):
    out = {} if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(d, bool):
        out[prefix or "value"] = int(d)
    elif isinstance(d, (int, float)):
        out[prefix or "value"] = d
    elif isinstance(d, dict):
        for k, v in d.items():
            flatten_numeric(v, f"{prefix}.{k}" if prefix else k, out, limit)
    return out


def trim(d, max_items=32, max_str=500):
    if isinstance(d, dict):
        return {k: trim(v, max_items, max_str) for k, v in d.items()}
    if isinstance(d, (list, tuple)):
        items = [trim(v, max_items, max_str) for v in list(d)[:max_items]]
        if len(d) > max_items:
            items.append(f"... ({len(d) - max_items} more)")
        return items
    if isinstance(d, str) and len(d) > max_str:
        return d[:max_str] + "..."
    if isinstance(d, (bytes, bytearray)):
        return f"<{len(d)} bytes>"
    return d


class Echo:
    def __init__(self, agent: "Agent", topic: str, type_name: str):
        self.topic, self.type_name = topic, type_name
        self.stamps: deque[float] = deque(maxlen=200)
        self.count = 0
        self.last_sent = 0.0
        msg_cls = get_message(type_name)
        # Best-effort + volatile is compatible with every publisher, so echo never perturbs the student graph.
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT, durability=DurabilityPolicy.VOLATILE)
        self.sub = agent.create_subscription(msg_cls, topic, self.on_msg, qos)

    def rate(self) -> float:
        now = time.monotonic()
        recent = [t for t in self.stamps if now - t <= 5.0]
        if len(recent) < 2 or now - recent[-1] > 2.0:
            return 0.0
        return (len(recent) - 1) / (recent[-1] - recent[0]) if recent[-1] > recent[0] else 0.0

    def on_msg(self, msg) -> None:
        now = time.monotonic()
        self.stamps.append(now)
        self.count += 1
        if now - self.last_sent < 1.0 / MAX_ECHO_HZ:
            return
        self.last_sent = now
        data = message_to_ordereddict(msg)
        emit({"type": "echo", "topic": self.topic, "msg_type": self.type_name, "t": time.time(),
              "count": self.count, "rate": round(self.rate(), 2), "data": trim(data),
              "numeric": flatten_numeric(data)})


class RobotWatch:
    """Observes the robot model exactly as RViz would: /robot_description, /tf, /tf_static, /joint_states."""

    def __init__(self, agent: "Agent") -> None:
        from sensor_msgs.msg import JointState
        from std_msgs.msg import String
        from tf2_msgs.msg import TFMessage

        self.agent = agent
        self.frames: dict[str, dict] = {}  # child -> latest transform
        self.parents: dict[str, set[str]] = {}  # child -> every parent seen (more than one = broken tree)
        self.dirty = False
        self.joints: dict = {}
        self.joints_dirty = False
        latched = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        static = QoSProfile(depth=100, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        live = QoSProfile(depth=100, reliability=ReliabilityPolicy.BEST_EFFORT, durability=DurabilityPolicy.VOLATILE)
        self.subs = [
            agent.create_subscription(String, "/robot_description", self.on_description, latched),
            agent.create_subscription(TFMessage, "/tf", lambda m: self.on_tf(m, False), live),
            agent.create_subscription(TFMessage, "/tf_static", lambda m: self.on_tf(m, True), static),
            agent.create_subscription(JointState, "/joint_states", self.on_joints, live),
        ]
        self.clock_samples: deque = deque(maxlen=30)  # (wall, sim) pairs, ~3 s window, for the real-time factor
        try:
            from rosgraph_msgs.msg import Clock

            self.subs.append(agent.create_subscription(Clock, "/clock", self.on_clock, live))
        except ImportError:  # pragma: no cover
            pass
        self.clock_timer = agent.create_timer(1.0, self.publish_clock)
        self.timer = agent.create_timer(0.1, self.flush)

    def on_description(self, msg) -> None:
        emit({"type": "robot_description", "urdf": msg.data, "t": time.time()})

    def on_tf(self, msg, static: bool) -> None:
        now = time.time()
        for t in msg.transforms:
            child, parent = t.child_frame_id.lstrip("/"), t.header.frame_id.lstrip("/")
            prev = self.frames.get(child)
            tr, q = t.transform.translation, t.transform.rotation
            self.frames[child] = {
                "child": child, "parent": parent, "static": static,
                "t": [tr.x, tr.y, tr.z], "q": [q.x, q.y, q.z, q.w], "received": now,
                "count": (prev["count"] + 1) if prev else 1,
                "first": prev["first"] if prev else now,
            }
            self.parents.setdefault(child, set()).add(parent)
        self.dirty = True

    def on_clock(self, msg) -> None:
        # Gazebo publishes /clock at ~1 kHz; keep one sample per 100 ms so the window spans seconds, not milliseconds
        now = time.monotonic()
        if self.clock_samples and now - self.clock_samples[-1][0] < 0.1:
            return
        self.clock_samples.append((now, msg.clock.sec + msg.clock.nanosec * 1e-9))

    def publish_clock(self) -> None:
        if not self.clock_samples:
            return
        wall_now = time.monotonic()
        (w0, s0), (w1, s1) = self.clock_samples[0], self.clock_samples[-1]
        rtf = (s1 - s0) / (w1 - w0) if w1 - w0 > 0.5 else None
        emit({"type": "sim_clock", "sim_time": round(s1, 3), "rtf": round(rtf, 2) if rtf is not None else None,
              "age": round(wall_now - w1, 2)})

    def on_joints(self, msg) -> None:
        for name, pos in zip(msg.name, msg.position):
            self.joints[name] = pos
        self.joints_dirty = True

    def flush(self) -> None:
        if self.dirty:
            self.dirty = False
            now = time.time()
            frames = []
            for f in self.frames.values():
                span = f["received"] - f["first"]
                frames.append({**f, "age": round(now - f["received"], 2),
                               "rate": round((f["count"] - 1) / span, 1) if span > 0 and not f["static"] else None,
                               "parents": sorted(self.parents.get(f["child"], ()))})
            emit({"type": "tf", "t": now, "frames": frames})
        if self.joints_dirty:
            self.joints_dirty = False
            pubs = [fqn(p.node_name, p.node_namespace) for p in self.agent.get_publishers_info_by_topic("/joint_states")
                    if not p.node_name.startswith("_")]
            emit({"type": "joint_states", "t": time.time(), "positions": self.joints, "publishers": pubs})

    def close(self) -> None:
        for s in self.subs:
            self.agent.destroy_subscription(s)
        self.agent.destroy_timer(self.timer)
        self.agent.destroy_timer(self.clock_timer)


class JointGui:
    """A VISIBLE node (academy_joint_gui) that publishes slider values on /joint_states at 10 Hz, playing the
    role of joint_state_publisher_gui. It appears in the ROS graph so students see who drives the joints."""

    def __init__(self, executor) -> None:
        from sensor_msgs.msg import JointState

        self.JointState = JointState
        self.node = rclpy.create_node("academy_joint_gui")
        self.pub = self.node.create_publisher(JointState, "/joint_states", 10)
        self.positions: dict[str, float] = {}
        self.node.create_timer(0.1, self.tick)
        self.executor = executor
        executor.add_node(self.node)

    def tick(self) -> None:
        if not self.positions:
            return
        msg = self.JointState()
        msg.header.stamp = self.node.get_clock().now().to_msg()
        msg.name = list(self.positions)
        msg.position = [float(v) for v in self.positions.values()]
        self.pub.publish(msg)

    def close(self) -> None:
        self.executor.remove_node(self.node)
        self.node.destroy_node()


class Agent(Node):
    def __init__(self) -> None:
        super().__init__(AGENT_NAME)
        self.commands: queue.Queue = queue.Queue()
        self.echoes: dict[str, Echo] = {}
        self.pending_echo: set[str] = set()
        self.robot: RobotWatch | None = None
        self.joint_gui: JointGui | None = None
        self.executor_ref = None
        self.create_timer(1.0, self.publish_graph)
        self.create_timer(0.05, self.process_commands)
        self.create_timer(1.0, self.publish_echo_stats)
        self.controller_clients: dict = {}
        self.create_timer(2.0, self.poll_controllers)

    # -- commands are applied on the executor thread (rclpy entities are not thread-safe)
    def process_commands(self) -> None:
        while True:
            try:
                cmd = self.commands.get_nowait()
            except queue.Empty:
                return
            try:
                self._apply_command(cmd)
            except Exception as e:
                emit({"type": "error", "cmd": cmd, "message": f"{type(e).__name__}: {e}"})

    def _apply_command(self, cmd: dict) -> None:
        c = cmd.get("cmd")
        if c == "snapshot":
            self.publish_graph()
        elif c == "echo":
            topic = cmd["topic"]
            if topic not in self.echoes and not self._start_echo(topic):
                self.pending_echo.add(topic)  # starts as soon as the topic appears (e.g. after a rebuild)
        elif c == "stop_echo":
            self.pending_echo.discard(cmd["topic"])
            e = self.echoes.pop(cmd["topic"], None)
            if e:
                self.destroy_subscription(e.sub)
            emit({"type": "echo_stopped", "topic": cmd["topic"]})
        elif c == "robot_watch":
            if cmd.get("enable") and self.robot is None:
                self.robot = RobotWatch(self)
            elif not cmd.get("enable") and self.robot is not None:
                self.robot.close()
                self.robot = None
        elif c == "joint_gui":
            positions = cmd.get("positions")
            if cmd.get("enable"):
                if self.joint_gui is None:
                    self.joint_gui = JointGui(self.executor_ref)
                if isinstance(positions, dict):
                    self.joint_gui.positions = {str(k): float(v) for k, v in list(positions.items())[:64]}
            elif self.joint_gui is not None:
                self.joint_gui.close()
                self.joint_gui = None
            emit({"type": "joint_gui_state", "enabled": self.joint_gui is not None})

    def _start_echo(self, topic: str) -> bool:
        types = dict(self.get_topic_names_and_types()).get(topic)
        if not types:
            return False
        self.echoes[topic] = Echo(self, topic, types[0])
        self.pending_echo.discard(topic)
        emit({"type": "echo_started", "topic": topic, "msg_type": types[0]})
        return True

    def poll_controllers(self) -> None:
        """Report ros2_control controller states for every controller_manager in the graph."""
        try:
            from controller_manager_msgs.srv import ListControllers
        except ImportError:  # pragma: no cover
            return
        services = [name for name, types in self.get_service_names_and_types()
                    if name.endswith("/list_controllers") and "controller_manager_msgs/srv/ListControllers" in types]
        if not services:
            if self.controller_clients:
                self.controller_clients.clear()
                emit({"type": "controllers", "managers": []})
            return
        for name in services:
            if name not in self.controller_clients:
                self.controller_clients[name] = self.create_client(ListControllers, name)
        managers = []
        pending = []
        for name, client in self.controller_clients.items():
            if client.service_is_ready():
                pending.append((name, client.call_async(ListControllers.Request())))

        def report(_f=None) -> None:
            if not all(f.done() for _, f in pending):
                return
            for name, f in pending:
                res = f.result()
                if res is None:
                    continue
                managers.append({"manager": name.rsplit("/list_controllers", 1)[0], "controllers": [
                    {"name": c.name, "type": c.type, "state": c.state,
                     "claimed_interfaces": list(c.claimed_interfaces),
                     "command_interfaces": list(c.required_command_interfaces),
                     "state_interfaces": list(c.required_state_interfaces)} for c in res.controller]})
            emit({"type": "controllers", "t": time.time(), "managers": managers})

        for _, f in pending:
            f.add_done_callback(report)

    def publish_echo_stats(self) -> None:
        for e in self.echoes.values():
            emit({"type": "echo_stats", "topic": e.topic, "count": e.count, "rate": round(e.rate(), 2)})

    def publish_graph(self) -> None:
        for topic in list(self.pending_echo):
            self._start_echo(topic)
        nodes = []
        for name, ns in self.get_node_names_and_namespaces():
            if name.startswith("_"):
                continue
            entry = {"name": fqn(name, ns), "services": [], "clients": [], "action_servers": [], "action_clients": []}
            try:
                entry["services"] = [{"name": s, "type": t[0], "system": s.endswith(SYSTEM_SERVICE_SUFFIXES)}
                                     for s, t in self.get_service_names_and_types_by_node(name, ns)]
                entry["clients"] = [{"name": s, "type": t[0], "system": s.endswith(SYSTEM_SERVICE_SUFFIXES)}
                                    for s, t in self.get_client_names_and_types_by_node(name, ns)]
                if get_action_server_names_and_types_by_node:
                    entry["action_servers"] = [{"name": a, "type": t[0]} for a, t in get_action_server_names_and_types_by_node(self, name, ns)]
                    entry["action_clients"] = [{"name": a, "type": t[0]} for a, t in get_action_client_names_and_types_by_node(self, name, ns)]
            except Exception:
                pass  # node vanished between calls
            nodes.append(entry)

        topics = []
        for topic, types in self.get_topic_names_and_types():
            if "/_action/" in topic:
                continue
            pubs = [p for p in self.get_publishers_info_by_topic(topic) if not p.node_name.startswith("_")]
            subs = [s for s in self.get_subscriptions_info_by_topic(topic) if not s.node_name.startswith("_")]
            if not pubs and not subs:
                continue
            pairs = []
            for p in pubs:
                for s in subs:
                    level, reason = qos_compat(p.qos_profile, s.qos_profile)
                    pairs.append({"publisher": fqn(p.node_name, p.node_namespace), "subscriber": fqn(s.node_name, s.node_namespace),
                                  "compatible": level, "reason": reason})
            topics.append({
                "name": topic, "types": types, "system": topic in SYSTEM_TOPICS,
                "publishers": [{"node": fqn(p.node_name, p.node_namespace), "type": p.topic_type, "qos": qos_dict(p.qos_profile)} for p in pubs],
                "subscribers": [{"node": fqn(s.node_name, s.node_namespace), "type": s.topic_type, "qos": qos_dict(s.qos_profile)} for s in subs],
                "qos_pairs": pairs,
                "echo": topic in self.echoes,
            })
        emit({"type": "graph", "t": time.time(), "nodes": nodes, "topics": topics})


def main() -> None:
    rclpy.init()
    agent = Agent()

    def read_stdin() -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                agent.commands.put(json.loads(line))
            except json.JSONDecodeError:
                emit({"type": "error", "message": "bad command"})
        rclpy.try_shutdown()  # parent closed stdin -> exit

    threading.Thread(target=read_stdin, daemon=True).start()
    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(agent)
    agent.executor_ref = executor
    emit({"type": "agent_ready"})
    try:
        executor.spin()
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
