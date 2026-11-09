"""Hidden tests for the final submission (students see titles and verdicts, not the inputs)."""

import re
import time

from academy_grader import RosHarness

PKG, TOPIC, TYPE = "topics_lab", "/numbers", "std_msgs/msg/Int32"


def test_hidden_subscriber_handles_extreme_values(ros, evidence):
    """Subscriber reports negative, zero and 32-bit limit values"""
    values = [-7, 0, 2147483647, -2147483648, 31337]
    with ros.run(PKG, "number_subscriber") as proc:
        assert ros.wait_for_endpoint(TOPIC, "sub", node="/number_subscriber", timeout=20), "subscriber never appeared"
        assert ros.publish_values(TOPIC, TYPE, values, period=0.2)
        time.sleep(1.0)
        out = proc.output()
    missing = [v for v in values if not re.search(rf"(?<![\d-]){re.escape(str(v))}(?!\d)", out)]
    evidence(expected="every value reported exactly as received",
             suggestion="Log msg.data directly; do not convert, clamp or format it.")
    assert not missing


def test_hidden_publisher_sustained_without_gaps(ros, evidence):
    """Publisher sustains 10 Hz for 6 s with no skipped values"""
    with ros.run(PKG, "number_publisher"):
        assert ros.wait_for_endpoint(TOPIC, "pub", node="/number_publisher", timeout=20), "publisher never appeared"
        samples = ros.collect(TOPIC, TYPE, 6.0)
    values = [m.data for _, m in samples]
    gaps = sum(1 for a, b in zip(values, values[1:]) if b != a + 1)
    evidence(expected="≥ 45 messages, no gaps, ~10 Hz",
             suggestion="Publish exactly once per timer callback and increment the counter once.")
    assert len(values) >= 45 and gaps == 0 and 8.0 <= RosHarness.rate(samples) <= 13.0
