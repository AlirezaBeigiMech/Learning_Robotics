"""Loads and validates course content from ``courses/``. Hidden tests and solutions never leave the server
except through the explicit, tracked endpoints (grader / hint level 5)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from ..config import settings
from .schema import Chapter, Course, Lesson

COURSE_ID = "mastering_ros2"
# Same set of file types a student may have in a workspace (urdf, xacro, launch, interfaces, sources, ...).
from ..workspace.manager import ALLOWED_SUFFIXES as TEXT_SUFFIXES  # noqa: E402


@dataclass
class LoadedLesson:
    lesson: Lesson
    dir: Path
    chapter: int

    def step_markdown(self, step_id: str) -> str:
        step = next(s for s in self.lesson.steps if s.id == step_id)
        return (self.dir / step.content).read_text(encoding="utf-8")

    def level_dir(self, level: str) -> Path:
        return self.dir / self.lesson.levels.get(level, self.lesson.levels["guided"])

    @property
    def solution_dir(self) -> Path:
        return self.dir / "solution"

    @property
    def tests_dir(self) -> Path:
        return self.dir / "tests"


@dataclass
class CourseContent:
    course: Course
    chapters: dict[int, Chapter]
    lessons: dict[str, LoadedLesson]


def _yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_course(root: Path | None = None) -> CourseContent:
    base = (root or settings.courses_dir) / COURSE_ID
    course = Course.model_validate(_yaml(base / "course.yaml"))
    chapters: dict[int, Chapter] = {}
    lessons: dict[str, LoadedLesson] = {}
    for ch_dir in sorted(base.glob("chapter_*")):
        chapter = Chapter.model_validate(_yaml(ch_dir / "chapter.yaml"))
        chapters[chapter.number] = chapter
        for lesson_id in chapter.lessons:
            ldir = ch_dir / "lessons" / lesson_id
            lesson = Lesson.model_validate(_yaml(ldir / "lesson.yaml"))
            if lesson.id != lesson_id:
                raise ValueError(f"{ldir}: id {lesson.id} != directory {lesson_id}")
            for step in lesson.steps:
                if not (ldir / step.content).is_file():
                    raise ValueError(f"{lesson_id}: missing content {step.content}")
            for cp in lesson.checkpoints:
                for t in cp.tests:
                    if not (ldir / "tests" / t).is_file():
                        raise ValueError(f"{lesson_id}: missing test {t}")
            for level_dir in lesson.levels.values():
                if not (ldir / level_dir / lesson.workspace.package / "package.xml").is_file():
                    raise ValueError(f"{lesson_id}: {level_dir} lacks package {lesson.workspace.package}")
            lessons[lesson_id] = LoadedLesson(lesson, ldir, chapter.number)
    referenced = {n for s in course.sections for n in s.chapters}
    if referenced != set(chapters):
        raise ValueError(f"course sections reference {sorted(referenced)} but chapters are {sorted(chapters)}")
    competencies = {c.id for c in course.competencies}
    for chapter in chapters.values():
        for comp in chapter.competencies:
            if comp not in competencies:
                raise ValueError(f"chapter {chapter.number}: unknown competency {comp}")
        for reading in chapter.readings:
            if reading.source not in course.sources:
                raise ValueError(f"chapter {chapter.number}: unknown reading source {reading.source}")
    return CourseContent(course, chapters, lessons)


@lru_cache(maxsize=1)
def content() -> CourseContent:
    return load_course()


def read_tree(directory: Path) -> dict[str, str]:
    """Return {posix relative path: text} for every text file below ``directory``."""
    out: dict[str, str] = {}
    for p in sorted(directory.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix in TEXT_SUFFIXES:
            out[p.relative_to(directory).as_posix()] = p.read_text(encoding="utf-8")
    return out
