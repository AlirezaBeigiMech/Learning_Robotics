"""Checkpoint 'publisher': behaviour of the running number_publisher node."""

import pytest

PKG, EXE, NODE, TOPIC, TYPE = "topics_lab", "number_publisher", "/number_publisher", "/numbers", "std_msgs/msg/Int32"


@pytest.fixture(scope="module")
def obs(_harness):
    h = _harness
    h.stop_all()
    proc = h.start(PKG, EXE)
    node_ok = h.wait_for_node(NODE, timeout=20)
    ep = h.wait_for_endpoint(TOPIC, "pub", node=NODE, timeout=10) if node_ok else None
    samples = h.collect(TOPIC, TYPE, 3.0) if ep and ep["type"] == TYPE else []
    result = {"node_ok": node_ok, "ep": ep, "samples": samples, "alive": proc.alive,
              "output": proc.output(), "nodes": h.node_names(), "pubs": h.endpoints(TOPIC)[0]}
    h.stop_all()
    return result


def _crash_info(o):
    tail = "\n".join(o["output"].splitlines()[-8:])
    return f"process {'running' if o['alive'] else 'EXITED'}; last output:\n{tail}" if tail else f"nodes seen: {o['nodes']}"


def test_publisher_advertises_topic(obs, evidence):
    """number_publisher advertises /numbers with type std_msgs/msg/Int32"""
    seen = [(p["node"], p["type"]) for p in obs["pubs"]]
    evidence(expected=f"{NODE} publishes {TYPE} on {TOPIC}",
             observed=f"publishers on {TOPIC}: {seen}" if obs["node_ok"] else f"node {NODE} not found — {_crash_info(obs)}",
             suggestion="Name the node 'number_publisher' and call self.create_publisher(Int32, 'numbers', 10).")
    assert obs["node_ok"], f"node {NODE} never appeared"
    assert obs["ep"] is not None, f"{NODE} does not publish on {TOPIC}"
    assert obs["ep"]["type"] == TYPE


def test_publisher_qos_is_reliable(obs, evidence):
    """Publisher uses the default RELIABLE / VOLATILE QoS"""
    ep = obs["ep"]
    evidence(expected="reliability=reliable, durability=volatile",
             observed=f"reliability={ep['reliability']}, durability={ep['durability']}" if ep else "no publisher found",
             suggestion="Pass a plain queue depth (10) as the QoS argument, or a QoSProfile with RELIABLE reliability.")
    assert ep is not None
    assert ep["reliability"] == "reliable" and ep["durability"] == "volatile"


def test_publisher_rate_10hz(obs, evidence):
    """Messages arrive at about 10 Hz"""
    from academy_grader import RosHarness

    rate = RosHarness.rate(obs["samples"])
    evidence(expected="8–13 Hz (timer period 0.1 s)", observed=f"{rate:.1f} Hz from {len(obs['samples'])} messages in 3 s",
             suggestion="Create the timer with self.create_timer(0.1, self.publish_next) and publish once per callback.")
    assert len(obs["samples"]) >= 15, "too few messages received"
    assert 8.0 <= rate <= 13.0


def test_publisher_counts_up(obs, evidence):
    """Each message carries the previous value plus one"""
    values = [m.data for _, m in obs["samples"]]
    diffs = {b - a for a, b in zip(values, values[1:])}
    evidence(expected="consecutive values differ by exactly 1 (e.g. 7, 8, 9, ...)",
             observed=f"first values: {values[:8]}" if values else "no messages received",
             suggestion="Put self.count into msg.data, publish, then do self.count += 1 inside the timer callback.")
    assert len(values) >= 5
    assert diffs == {1}
