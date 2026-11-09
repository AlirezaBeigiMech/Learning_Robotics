"""Checkpoint 'subscriber': the grader publishes unpredictable values and checks the subscriber reports them."""

import random
import re
import time

import pytest

PKG, EXE, NODE, TOPIC, TYPE = "topics_lab", "number_subscriber", "/number_subscriber", "/numbers", "std_msgs/msg/Int32"


def reported(output: str, value: int) -> bool:
    return re.search(rf"(?<![\d-]){re.escape(str(value))}(?!\d)", output) is not None


@pytest.fixture(scope="module")
def obs(_harness):
    h = _harness
    h.stop_all()
    proc = h.start(PKG, EXE)
    node_ok = h.wait_for_node(NODE, timeout=20)
    ep = h.wait_for_endpoint(TOPIC, "sub", node=NODE, timeout=10) if node_ok else None
    values = random.sample(range(10_000, 99_999), 6)
    delivered = h.publish_values(TOPIC, TYPE, values, period=0.2) if ep and ep["type"] == TYPE else False
    time.sleep(1.0)
    result = {"node_ok": node_ok, "ep": ep, "values": values, "delivered": delivered, "output": proc.output(),
              "alive": proc.alive, "nodes": h.node_names()}
    h.stop_all()
    return result


def test_subscriber_subscribes(obs, evidence):
    """number_subscriber subscribes to /numbers with type std_msgs/msg/Int32"""
    ep = obs["ep"]
    tail = "\n".join(obs["output"].splitlines()[-6:])
    evidence(expected=f"{NODE} subscribed to {TOPIC} ({TYPE})",
             observed=(f"subscription type {ep['type']}" if ep else
                       f"no subscription found; nodes: {obs['nodes']}; process {'running' if obs['alive'] else 'EXITED'}; output:\n{tail}"),
             suggestion="Call self.create_subscription(Int32, 'numbers', self.on_number, 10) in __init__ and store the result.")
    assert obs["node_ok"], f"node {NODE} never appeared"
    assert ep is not None and ep["type"] == TYPE


def test_subscriber_reports_every_value(obs, evidence):
    """Every number published by the grader shows up in the subscriber's log"""
    missing = [v for v in obs["values"] if not reported(obs["output"], v)]
    evidence(expected=f"log lines containing each of {len(obs['values'])} grader-chosen numbers",
             observed=(f"{len(obs['values']) - len(missing)}/{len(obs['values'])} reported; last log lines: "
                       + " | ".join(obs["output"].splitlines()[-3:])),
             suggestion="In the callback, log msg.data, e.g. self.get_logger().info(f'Received: {msg.data}').")
    assert obs["delivered"], "the subscriber never matched the grader's publisher"
    assert not missing
