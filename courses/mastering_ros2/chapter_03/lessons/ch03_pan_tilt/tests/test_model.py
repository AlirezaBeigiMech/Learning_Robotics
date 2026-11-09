"""Checkpoint 'model': your robot description is compared with the specification by behaviour —
kinematics of every frame, geometry, and physical plausibility — never by its text."""

import pytest

from academy_grader import robot_checks as rc
from academy_grader import urdf_tools as ut

PKG, FILE, REF, ROOT = "pan_tilt_description", "urdf/pan_tilt.urdf", "pan_tilt.urdf", "base_link"


@pytest.fixture(scope="module")
def models():
    try:
        student, _ = rc.student_model(PKG, FILE)
        error = None
    except Exception as e:  # xacro or parse error
        student, error = None, f"{type(e).__name__}: {e}"
    return student, rc.reference_model(__file__, REF), error


def _need(models):
    student, _, error = models
    assert student is not None, f"model could not be loaded: {error}"


def test_model_expands_and_parses(models, evidence):
    """The installed model expands with xacro and parses as URDF"""
    student, _, error = models
    evidence(expected=f"share/{PKG}/{FILE} expands and parses", observed=error or "ok",
             suggestion="Build first, then open the Robot tab preview: it shows the exact xacro/XML error.")
    _need(models)


def test_single_tree_rooted_correctly(models, evidence):
    """All links form one tree rooted at the expected link"""
    _need(models)
    student, ref, _ = models
    roots = ut.roots(student)
    structural = [p["message"] for p in ut.analyze(student) if p["severity"] == "error"]
    missing = sorted({l.name for l in ref.links} - {l.name for l in student.links})
    evidence(expected=f"one root '{ROOT}'; links {sorted(l.name for l in ref.links)}",
             observed=f"roots {roots}; missing links {missing or 'none'}; errors {structural or 'none'}",
             suggestion="Every link except the root must be the child of exactly one joint.")
    assert roots == [ROOT] and not missing and not structural


def test_joints_match_specification(models, evidence):
    """Joint types, parents/children, axes, limits and mimics match the specification"""
    _need(models)
    student, ref, _ = models
    problems = rc.compare_joints(student, ref)
    evidence(expected="all joints as specified", observed="; ".join(problems[:6]) or "all match",
             suggestion="Check each joint against the lesson table: type, axis vector and all four limit values.")
    assert not problems


def test_frames_at_zero_configuration(models, evidence):
    """Every link frame is where the specification puts it (all joints at zero)"""
    _need(models)
    student, ref, _ = models
    problems = rc.compare_poses(student, ref, ROOT, {}, [l.name for l in ref.links])
    evidence(expected="each frame within 1 mm / 0.6°", observed="; ".join(problems[:5]) or "all frames match",
             suggestion="A frame's pose comes from the <origin> of the joint that creates it, relative to its parent frame.")
    assert not problems


def test_visual_and_collision_geometry(models, evidence):
    """Visual and collision shapes have the specified type, size and placement"""
    _need(models)
    student, ref, _ = models
    problems = rc.compare_geometry(student, ref, "visuals") + rc.compare_geometry(student, ref, "collisions")
    evidence(expected="shapes and their origins as specified", observed="; ".join(problems[:5]) or "all match",
             suggestion="Geometry is centred on its <origin>: a 0.3 m cylinder standing on a joint needs z = 0.15.")
    assert not problems


def test_inertia_is_physical(models, evidence):
    """Every body has the specified mass and a physically valid inertia"""
    _need(models)
    student, ref, _ = models
    problems = rc.compare_inertia(student, ref)
    evidence(expected="specified masses; inertia of a solid body of that shape (±5%)",
             observed="; ".join(problems[:4]) or "all plausible",
             suggestion="Use the solid-body formulas (or the inertial macros) with the link's own dimensions.")
    assert not problems
