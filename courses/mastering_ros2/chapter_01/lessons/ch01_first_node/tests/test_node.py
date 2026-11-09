"""Checkpoint 'node': your node appears in the ROS graph and emits a heartbeat."""

import re
import time

import pytest

PKG, EXE, NODE = "first_node_lab", "hello_node", "/hello_node"


def counters(output: str) -> list[int]:
    out = []
    for line in output.splitlines():
        found = re.findall(r"\d+", line.split("]")[-1])
        if found:
            out.append(int(found[-1]))
    return out


@pytest.fixture(scope="module")
def obs(_harness):
    h = _harness
    h.stop_all()
    proc = h.start(PKG, EXE)
    node_ok = h.wait_for_node(NODE, timeout=20)
    time.sleep(3.0)
    result = {"node_ok": node_ok, "nodes": h.node_names(), "output": proc.output(), "alive": proc.alive}
    h.stop_all()
    return result


def test_node_in_graph(obs, evidence):
    """A node named /hello_node joins the ROS graph"""
    tail = " | ".join(obs["output"].splitlines()[-4:])
    evidence(expected=f"{NODE} in the node list",
             observed=f"nodes: {obs['nodes'] or 'none'}; process {'running' if obs['alive'] else 'EXITED'}; output: {tail}",
             suggestion="Pass 'hello_node' to super().__init__ and make sure main() calls rclpy.spin(node).")
    assert obs["node_ok"]


def test_heartbeat_counts_up(obs, evidence):
    """The node logs a heartbeat with an increasing counter"""
    nums = counters(obs["output"])
    evidence(expected="≥ 4 heartbeat lines in ~3 s, each counter one larger than the last",
             observed=f"counters seen: {nums[:10]}",
             suggestion="Create the timer with create_timer(0.5, self.heartbeat); increment and log the counter in heartbeat().")
    assert len(nums) >= 4
    assert all(b == a + 1 for a, b in zip(nums, nums[1:]))
