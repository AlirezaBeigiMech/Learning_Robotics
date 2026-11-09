"""Checkpoint 'integration': your publisher and your subscriber talk to each other."""

import re
import time

import pytest
from rclpy.qos import QoSCompatibility, qos_check_compatible

PKG, TOPIC = "topics_lab", "/numbers"


def longest_consecutive_run(output: str) -> int:
    nums = []
    for line in output.splitlines():
        found = re.findall(r"-?\d+", line.split("]")[-1])  # skip the [INFO] [timestamp] prefix
        if found:
            nums.append(int(found[-1]))
    best = run = 1 if nums else 0
    for a, b in zip(nums, nums[1:]):
        run = run + 1 if b == a + 1 else 1
        best = max(best, run)
    return best


@pytest.fixture(scope="module")
def obs(_harness):
    h = _harness
    h.stop_all()
    pub = h.start(PKG, "number_publisher")
    sub = h.start(PKG, "number_subscriber")
    ok = h.wait_for_node("/number_publisher", 20) and h.wait_for_node("/number_subscriber", 20)
    h.wait_for_endpoint(TOPIC, "sub", node="/number_subscriber", timeout=10)
    time.sleep(6.0)
    pubs, subs = h.endpoints(TOPIC)
    result = {"ok": ok, "pubs": pubs, "subs": subs, "sub_output": sub.output(), "pub_output": pub.output()}
    h.stop_all()
    return result


def test_qos_compatible(obs, evidence):
    """Publisher and subscriber QoS profiles are compatible"""
    p = next((e for e in obs["pubs"] if e["node"] == "/number_publisher"), None)
    s = next((e for e in obs["subs"] if e["node"] == "/number_subscriber"), None)
    verdict, reason = (qos_check_compatible(p["qos"], s["qos"]) if p and s else (None, "endpoint missing"))
    evidence(expected="compatible QoS (e.g. both RELIABLE, or BEST_EFFORT subscriber)",
             observed=(f"publisher {p['reliability']}/{p['durability']} → subscriber {s['reliability']}/{s['durability']}: {reason or 'ok'}"
                       if p and s else reason),
             suggestion="A RELIABLE subscription cannot receive from a BEST_EFFORT publisher. Make the publisher RELIABLE "
                        "(default depth-10 profile) or relax the subscriber.")
    assert p and s, "both endpoints must exist on /numbers"
    assert verdict != QoSCompatibility.ERROR, reason


def test_messages_flow_end_to_end(obs, evidence):
    """The subscriber receives an unbroken sequence from the publisher"""
    run = longest_consecutive_run(obs["sub_output"])
    evidence(expected="≥ 20 consecutive increasing numbers in the subscriber log within ~6 s",
             observed=f"longest consecutive run: {run}; subscriber tail: " + " | ".join(obs["sub_output"].splitlines()[-3:]),
             suggestion="Run both nodes and check the subscriber log. Silence usually means a topic name, type or QoS mismatch.")
    assert obs["ok"], "both nodes must start"
    assert run >= 20
