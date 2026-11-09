"""Behavioural checks for robot-description lessons: the student's model is compared with a reference
model by what it *does* (kinematics, geometry, physics), never by its text."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from . import urdf_tools as ut


def student_model(package: str, relpath: str):
    """Expand the student's INSTALLED file (what ros2 launch uses) with xacro and parse it."""
    from ament_index_python.packages import get_package_share_directory

    path = Path(get_package_share_directory(package)) / relpath
    return ut.load(ut.expand_xacro(path)), path


def reference_model(test_file: str, name: str):
    return ut.load((Path(test_file).parent / "reference" / name).read_text(encoding="utf-8"))


def fmt_vec(v) -> str:
    return "(" + ", ".join(f"{x:+.3f}" for x in v) + ")"


def rotation_error(a: np.ndarray, b: np.ndarray) -> float:
    """Angle (rad) of the relative rotation between two 4x4 poses."""
    r = a[:3, :3].T @ b[:3, :3]
    return math.acos(max(-1.0, min(1.0, (np.trace(r) - 1) / 2)))


def compare_poses(student, reference, root: str, joints: dict[str, float], frames: list[str],
                  pos_tol: float = 1e-3, rot_tol: float = 1e-2) -> list[str]:
    """Pose of every frame (relative to root) in both models for one joint configuration."""
    problems = []
    s_links = {l.name for l in student.links}
    for f in frames:
        if f not in s_links:
            problems.append(f"frame '{f}' is missing")
            continue
        try:
            ps = ut.fk(student, joints, root, f)
        except ValueError as e:
            problems.append(str(e))
            continue
        pr = ut.fk(reference, joints, root, f)
        dp = float(np.linalg.norm(ps[:3, 3] - pr[:3, 3]))
        dr = rotation_error(ps, pr)
        if dp > pos_tol or dr > rot_tol:
            problems.append(f"'{f}' at {fmt_vec(ps[:3, 3])}, expected {fmt_vec(pr[:3, 3])}"
                            + (f", orientation off by {math.degrees(dr):.1f}°" if dr > rot_tol else ""))
    return problems


def compare_joints(student, reference) -> list[str]:
    problems = []
    sj = {j.name: j for j in student.joints}
    for rj in reference.joints:
        j = sj.get(rj.name)
        if j is None:
            problems.append(f"joint '{rj.name}' is missing")
            continue
        if j.type != rj.type:
            problems.append(f"'{rj.name}' is {j.type}, expected {rj.type}")
        if (j.parent, j.child) != (rj.parent, rj.child):
            problems.append(f"'{rj.name}' connects {j.parent}→{j.child}, expected {rj.parent}→{rj.child}")
        if rj.type != "fixed":
            a = np.asarray(j.axis or [1, 0, 0], float)
            b = np.asarray(rj.axis or [1, 0, 0], float)
            if np.linalg.norm(a / (np.linalg.norm(a) or 1) - b / np.linalg.norm(b)) > 1e-3:
                problems.append(f"'{rj.name}' axis {fmt_vec(a)}, expected {fmt_vec(b)}")
        if rj.limit is not None and rj.type in ("revolute", "prismatic"):
            if j.limit is None:
                problems.append(f"'{rj.name}' has no <limit>")
            else:
                for attr in ("lower", "upper", "effort", "velocity"):
                    got, exp = getattr(j.limit, attr), getattr(rj.limit, attr)
                    if exp is not None and (got is None or abs(got - exp) > 1e-3):
                        problems.append(f"'{rj.name}' limit {attr}={got}, expected {exp}")
        if rj.mimic is not None and (j.mimic is None or j.mimic.joint != rj.mimic.joint):
            problems.append(f"'{rj.name}' should mimic '{rj.mimic.joint}'")
    return problems


def shape(geom) -> tuple[str, tuple]:
    from urdf_parser_py.urdf import Box, Cylinder, Mesh, Sphere

    if isinstance(geom, Box):
        return "box", tuple(round(v, 4) for v in geom.size)
    if isinstance(geom, Cylinder):
        return "cylinder", (round(geom.radius, 4), round(geom.length, 4))
    if isinstance(geom, Sphere):
        return "sphere", (round(geom.radius, 4),)
    if isinstance(geom, Mesh):
        return "mesh", (geom.filename,)
    return "none", ()


def compare_geometry(student, reference, kind: str = "visuals") -> list[str]:
    problems = []
    sl = {l.name: l for l in student.links}
    for rl in reference.links:
        ref_items = getattr(rl, kind)
        if not ref_items:
            continue
        l = sl.get(rl.name)
        if l is None:
            continue  # reported by the frame check
        items = getattr(l, kind)
        if not items:
            problems.append(f"link '{rl.name}' has no {kind[:-1]} geometry")
            continue
        got, exp = shape(items[0].geometry), shape(ref_items[0].geometry)
        if got[0] != exp[0] or any(abs(a - b) > 1e-3 for a, b in zip(got[1], exp[1])):
            problems.append(f"link '{rl.name}' {kind[:-1]} is {got[0]}{got[1]}, expected {exp[0]}{exp[1]}")
            continue
        go, eo = ut.origin_matrix(items[0].origin), ut.origin_matrix(ref_items[0].origin)
        if np.linalg.norm(go[:3, 3] - eo[:3, 3]) > 1e-3 or rotation_error(go, eo) > 1e-2:
            problems.append(f"link '{rl.name}' {kind[:-1]} origin {fmt_vec(go[:3, 3])}, expected {fmt_vec(eo[:3, 3])}")
    return problems


def compare_inertia(student, reference, rel_tol: float = 0.05) -> list[str]:
    problems = []
    sl = {l.name: l for l in student.links}
    for rl in reference.links:
        if rl.inertial is None or rl.name not in sl:
            continue
        l = sl[rl.name]
        reason = ut.inertia_problem(l.inertial)
        if reason:
            problems.append(f"link '{rl.name}': {reason}")
            continue
        if abs(l.inertial.mass - rl.inertial.mass) > rel_tol * rl.inertial.mass:
            problems.append(f"link '{rl.name}' mass {l.inertial.mass:g} kg, expected {rl.inertial.mass:g} kg")
            continue
        # Compare physics, not notation: centre of mass and the inertia tensor expressed in the LINK frame,
        # so rotating the <inertial> origin or writing a rotated tensor directly are equally correct.
        gs, es = ut.origin_matrix(l.inertial.origin), ut.origin_matrix(rl.inertial.origin)
        if np.linalg.norm(gs[:3, 3] - es[:3, 3]) > 1e-3:
            problems.append(f"link '{rl.name}' centre of mass {fmt_vec(gs[:3, 3])}, expected {fmt_vec(es[:3, 3])}")
            continue
        got, exp = link_frame_inertia(l.inertial), link_frame_inertia(rl.inertial)
        if np.abs(got - exp).max() > rel_tol * np.abs(exp).max():
            d = np.diag(got)
            problems.append(f"link '{rl.name}' inertia diag {fmt_vec(d)} (link frame), expected {fmt_vec(np.diag(exp))} "
                            "(solid-body formula for its shape and mass)")
    return problems


def link_frame_inertia(inertial) -> np.ndarray:
    i = inertial.inertia
    m = np.array([[i.ixx, i.ixy, i.ixz], [i.ixy, i.iyy, i.iyz], [i.ixz, i.iyz, i.izz]], dtype=float)
    r = ut.origin_matrix(inertial.origin)[:3, :3]
    return r @ m @ r.T


def lowest_point(robot, joints: dict[str, float], root: str) -> float:
    """Lowest z (in root) of all collision geometry: box corners, cylinder rims, sphere bottoms."""
    from urdf_parser_py.urdf import Box, Cylinder, Sphere

    low = math.inf
    for l in robot.links:
        for c in l.collisions:
            pose = ut.fk(robot, joints, root, l.name) @ ut.origin_matrix(c.origin)
            g = c.geometry
            if isinstance(g, Sphere):
                low = min(low, pose[2, 3] - g.radius)
            elif isinstance(g, Box):
                for sx in (-1, 1):
                    for sy in (-1, 1):
                        for sz in (-1, 1):
                            p = pose @ np.array([sx * g.size[0] / 2, sy * g.size[1] / 2, sz * g.size[2] / 2, 1])
                            low = min(low, p[2])
            elif isinstance(g, Cylinder):
                for k in range(72):
                    a = 2 * math.pi * k / 72
                    for sz in (-1, 1):
                        p = pose @ np.array([g.radius * math.cos(a), g.radius * math.sin(a), sz * g.length / 2, 1])
                        low = min(low, p[2])
    return low


def random_configs(robot, n: int, seed: int) -> list[dict[str, float]]:
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        cfg = {}
        for j in robot.joints:
            if j.type == "continuous":
                cfg[j.name] = float(rng.uniform(-math.pi, math.pi))
            elif j.type in ("revolute", "prismatic") and j.limit is not None and j.mimic is None:
                cfg[j.name] = float(rng.uniform(j.limit.lower, j.limit.upper))
        out.append(cfg)
    return out
