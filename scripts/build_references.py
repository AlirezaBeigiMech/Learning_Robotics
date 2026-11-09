"""Regenerate tests/reference/*.urdf for robot-description lessons by expanding each lesson's reference
solution with the real xacro tool, then sanity-check the references.

Usage:  pixi run python scripts/build_references.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "grader_support"))

from academy_grader import robot_checks as rc  # noqa: E402
from academy_grader import urdf_tools as ut  # noqa: E402


def main() -> int:
    ok = True
    for lesson in sorted((ROOT / "courses").glob("*/chapter_*/lessons/*")):
        models = [p for p in (lesson / "solution").glob("*/urdf/*") if p.name.endswith((".urdf", ".urdf.xacro"))]
        for model in models:
            urdf = ut.expand_xacro(model)
            robot = ut.load(urdf)
            out = lesson / "tests" / "reference" / (model.name.removesuffix(".xacro"))
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(urdf, encoding="utf-8")
            problems = ut.analyze(robot)
            root = ut.roots(robot)[0]
            low = rc.lowest_point(robot, {}, root)
            print(f"{lesson.name}: {out.relative_to(ROOT)}  links={len(robot.links)} joints={len(robot.joints)} "
                  f"root={root} lowest_z={low:+.4f} problems={problems or 'none'}")
            ok &= not problems
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
