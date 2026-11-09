from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..config import settings
from ..models import User
from ..security import current_user
from .loader import content

router = APIRouter(prefix="/api/courses", tags=["content"])


@router.get("")
def course_outline(_: User = Depends(current_user)) -> dict:
    c = content()
    chapters = []
    for num in sorted(c.chapters):
        ch = c.chapters[num]
        chapters.append({
            **ch.model_dump(exclude={"lessons"}),
            "lessons": [
                {
                    "id": lid,
                    "title": c.lessons[lid].lesson.title,
                    "difficulty": c.lessons[lid].lesson.difficulty,
                    "estimated_minutes": c.lessons[lid].lesson.estimated_minutes,
                }
                for lid in ch.lessons
            ],
        })
    return {**c.course.model_dump(), "chapters": chapters}


def missing_requirements(requires: list[str]) -> list[dict]:
    """Desktop simulators a lesson needs that are not installed, with what to install."""
    found = {"webots": settings.webots_home, "coppeliasim": settings.coppeliasim_root}
    info = {
        "webots": {"name": "Webots R2025a", "url": "https://github.com/cyberbotics/webots/releases/tag/R2025a",
                   "where": r"%LOCALAPPDATA%\Programs\Webots (per-user install) or set WEBOTS_HOME"},
        "coppeliasim": {"name": "CoppeliaSim Edu 4.10", "url": "https://www.coppeliarobotics.com/",
                        "where": r"unzip to %LOCALAPPDATA%\Programs\CoppeliaSim or set COPPELIASIM_ROOT_DIR"},
    }
    return [{"id": r, **info[r]} for r in requires if not found[r]]


@router.get("/lessons/{lesson_id}")
def lesson_detail(lesson_id: str, _: User = Depends(current_user)) -> dict:
    loaded = content().lessons.get(lesson_id)
    if loaded is None:
        raise HTTPException(404, "Unknown lesson")
    lesson = loaded.lesson
    steps = []
    for s in lesson.steps:
        d = s.model_dump(exclude={"hints"})
        d["markdown"] = loaded.step_markdown(s.id)
        d["hint_count"] = len(s.hints) + 1  # +1 = reference-solution level
        steps.append(d)
    return {
        **lesson.model_dump(exclude={"steps", "checkpoints"}),
        "missing_requirements": missing_requirements(lesson.requires),
        "chapter": loaded.chapter,
        "steps": steps,
        # Public view of checkpoints: names of test files only, never their contents.
        "checkpoints": [
            {"id": cp.id, "title": cp.title, "final": cp.final, "test_count": len(cp.tests)} for cp in lesson.checkpoints
        ],
    }
