"""Behavioural test helpers for academy lessons. Loaded by the grader as a pytest plugin
(``-p academy_grader.plugin``); never copied into a student's workspace."""

from .harness import RosHarness, RunningProcess

__all__ = ["RosHarness", "RunningProcess"]
