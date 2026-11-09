"""URDF utilities shared by the grader and the backend's live preview: xacro expansion, parsing,
structural analysis and forward kinematics (same convention as robot_state_publisher/KDL)."""

from __future__ import annotations

import contextlib
import io
import math
from pathlib import Path

import numpy as np


def load(xml: str):
    """Parse a URDF string with urdf_parser_py (its warnings about unknown tags are silenced)."""
    from urdf_parser_py.urdf import URDF

    with contextlib.redirect_stderr(io.StringIO()):
        return URDF.from_xml_string(xml)


def expand_xacro(path: str | Path, mappings: dict[str, str] | None = None) -> str:
    import xacro

    doc = xacro.process_file(str(path), mappings=mappings or {})
    return doc.toprettyxml(indent="  ")


# ---------------------------------------------------------------- math
def rpy_to_matrix(r: float, p: float, y: float) -> np.ndarray:
    """URDF rpy = fixed-axis roll(X), pitch(Y), yaw(Z):  R = Rz(y) @ Ry(p) @ Rx(r)."""
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return np.array([
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp, cp * sr, cp * cr],
    ])


def axis_angle(axis, theta: float) -> np.ndarray:
    a = np.asarray(axis, dtype=float)
    a = a / (np.linalg.norm(a) or 1.0)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(theta) * k + (1 - math.cos(theta)) * (k @ k)


def homogeneous(rot: np.ndarray | None = None, trans=None) -> np.ndarray:
    t = np.eye(4)
    if rot is not None:
        t[:3, :3] = rot
    if trans is not None:
        t[:3, 3] = trans
    return t


def origin_matrix(origin) -> np.ndarray:
    if origin is None:
        return np.eye(4)
    xyz = origin.xyz or [0, 0, 0]
    rpy = origin.rpy or [0, 0, 0]
    return homogeneous(rpy_to_matrix(*rpy), xyz)


def quaternion_matrix(t, q) -> np.ndarray:
    x, y, z, w = q
    rot = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])
    return homogeneous(rot, t)


def joint_matrix(joint, q: float) -> np.ndarray:
    t = origin_matrix(joint.origin)
    axis = joint.axis or [1, 0, 0]
    if joint.type in ("revolute", "continuous"):
        t = t @ homogeneous(axis_angle(axis, q))
    elif joint.type == "prismatic":
        t = t @ homogeneous(None, np.asarray(axis, dtype=float) / (np.linalg.norm(axis) or 1.0) * q)
    return t


# ---------------------------------------------------------------- structure
def parent_joint_map(robot) -> dict:
    return {j.child: j for j in robot.joints}


def roots(robot) -> list[str]:
    children = {j.child for j in robot.joints}
    return [l.name for l in robot.links if l.name not in children]


def chain(robot, base: str, tip: str) -> list:
    """Joints from base to tip (base must be an ancestor of tip)."""
    pj = parent_joint_map(robot)
    out, link = [], tip
    while link != base:
        j = pj.get(link)
        if j is None:
            raise ValueError(f"'{base}' is not an ancestor of '{tip}'")
        out.append(j)
        link = j.parent
    return list(reversed(out))


def fk(robot, joints: dict[str, float], base: str, tip: str) -> np.ndarray:
    t = np.eye(4)
    for j in chain(robot, base, tip):
        q = joints.get(j.name, 0.0)
        if j.mimic is not None:
            q = joints.get(j.mimic.joint, 0.0) * (j.mimic.multiplier or 1.0) + (j.mimic.offset or 0.0)
        t = t @ joint_matrix(j, q)
    return t


def inertia_problem(inertial) -> str | None:
    """None if the inertia is physically plausible, else a reason."""
    if inertial is None:
        return "no <inertial>"
    if inertial.mass is None or inertial.mass <= 0:
        return f"mass must be > 0 (got {inertial.mass})"
    i = inertial.inertia
    m = np.array([[i.ixx, i.ixy, i.ixz], [i.ixy, i.iyy, i.iyz], [i.ixz, i.iyz, i.izz]], dtype=float)
    eig = np.linalg.eigvalsh(m)
    if eig.min() <= 0:
        return f"inertia matrix is not positive-definite (eigenvalues {np.round(eig, 6).tolist()})"
    a, b, c = sorted(eig)
    if a + b < c * (1 - 1e-6):
        return f"principal moments violate the triangle inequality ({a:.4g} + {b:.4g} < {c:.4g})"
    return None


def analyze(robot) -> list[dict]:
    """Problems a robotics engineer would flag, as editor/viewer diagnostics."""
    out: list[dict] = []
    names = [l.name for l in robot.links]
    for dup in {n for n in names if names.count(n) > 1}:
        out.append({"severity": "error", "message": f"duplicate link name '{dup}'"})
    link_set = set(names)
    for j in robot.joints:
        for end in (j.parent, j.child):
            if end not in link_set:
                out.append({"severity": "error", "message": f"joint '{j.name}' references unknown link '{end}'"})
        if j.type in ("revolute", "prismatic") and j.limit is None:
            out.append({"severity": "error", "message": f"{j.type} joint '{j.name}' needs a <limit>"})
        if j.type in ("revolute", "prismatic", "continuous") and j.axis is not None and not any(j.axis):
            out.append({"severity": "error", "message": f"joint '{j.name}' has a zero axis"})
        if j.limit is not None and j.type == "revolute" and j.limit.lower is not None and j.limit.upper is not None \
                and j.limit.lower > j.limit.upper:
            out.append({"severity": "error", "message": f"joint '{j.name}': lower limit > upper limit"})
    parents = {}
    for j in robot.joints:
        if j.child in parents:
            out.append({"severity": "error", "message": f"link '{j.child}' has two parents ('{parents[j.child]}', '{j.parent}')"})
        parents[j.child] = j.parent
    r = roots(robot)
    if len(r) != 1:
        out.append({"severity": "error", "message": f"a URDF must form one tree; found {len(r)} root links: {r}"})
    for l in robot.links:
        if l.visuals and not l.collisions:
            out.append({"severity": "warning", "message": f"link '{l.name}' has visual but no collision geometry"})
        if l.visuals or l.collisions:
            problem = inertia_problem(l.inertial)
            if problem:
                out.append({"severity": "warning", "message": f"link '{l.name}': {problem} (physics simulators need valid inertia)"})
    return out
