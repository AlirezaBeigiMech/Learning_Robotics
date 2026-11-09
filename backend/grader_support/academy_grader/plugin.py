"""pytest plugin: ``ros`` and ``evidence`` fixtures, plus titles/hidden flags in the JUnit report."""

from __future__ import annotations

import pytest
import rclpy

from .harness import RosHarness


@pytest.fixture(scope="session")
def _harness():
    h = RosHarness()
    yield h
    h.close()
    rclpy.try_shutdown()


@pytest.fixture
def ros(_harness: RosHarness):
    _harness.stop_all(wait_nodes_gone=True)
    yield _harness
    _harness.stop_all(wait_nodes_gone=True)


@pytest.fixture
def evidence(record_property):
    """Record what the test expected and what it observed, shown to the student next to the result."""

    def _record(expected: str | None = None, observed: str | None = None, suggestion: str | None = None) -> None:
        if expected is not None:
            record_property("expected", expected)
        if observed is not None:
            record_property("observed", observed)
        if suggestion is not None:
            record_property("suggestion", suggestion)

    return _record


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    doc = (item.function.__doc__ or "").strip().splitlines()
    item.user_properties.append(("title", doc[0] if doc else item.name))
    item.user_properties.append(("hidden", "1" if item.name.startswith("test_hidden_") else "0"))
