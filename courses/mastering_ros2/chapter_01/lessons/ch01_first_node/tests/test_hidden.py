"""Hidden test for the final submission."""

import re
import time

PKG, EXE, NODE = "first_node_lab", "hello_node", "/hello_node"


def test_hidden_keeps_running_at_2hz(ros, evidence):
    """The node keeps spinning and beats at ~2 Hz for 5 s"""
    with ros.run(PKG, EXE) as proc:
        assert ros.wait_for_node(NODE, timeout=20), "node never appeared"
        before = len([l for l in proc.output().splitlines() if re.search(r"\d", l.split("]")[-1])])
        time.sleep(5.0)
        after = len([l for l in proc.output().splitlines() if re.search(r"\d", l.split("]")[-1])])
        alive = proc.alive
    evidence(expected="still running after 5 s, 8–12 heartbeats in that window",
             suggestion="Use a 0.5 s timer and keep the node alive with rclpy.spin().")
    assert alive and 8 <= after - before <= 12
