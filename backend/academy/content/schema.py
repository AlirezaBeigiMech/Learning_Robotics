"""Normative schema for course content (see docs/03-lesson-and-assessment-schemas.md)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

IDENT = r"^[a-z][a-z0-9_]*$"


class BookReference(BaseModel):
    chapter: int
    title: str | None = None
    sections: list[str] = []


class BookChapter(BaseModel):
    number: int
    title: str


class Completion(BaseModel):
    type: Literal["manual", "checkpoint", "graph", "graph_qos_mismatch", "tf_frames", "controllers_active"]
    frames: list[str] = []
    controllers: list[str] = []
    checkpoint: str | None = None
    node: str | None = None
    publishes: str | None = None
    subscribes: str | None = None
    topic: str | None = None

    @model_validator(mode="after")
    def _check(self) -> "Completion":
        if self.type == "checkpoint" and not self.checkpoint:
            raise ValueError("checkpoint completion needs 'checkpoint'")
        if self.type == "graph" and not self.node:
            raise ValueError("graph completion needs 'node'")
        if self.type == "controllers_active" and not self.controllers:
            raise ValueError("controllers_active completion needs 'controllers'")
        if self.type == "tf_frames" and not self.frames:
            raise ValueError("tf_frames completion needs 'frames'")
        if self.type == "graph_qos_mismatch" and not self.topic:
            raise ValueError("graph_qos_mismatch completion needs 'topic'")
        return self


class Step(BaseModel):
    id: str = Field(pattern=IDENT)
    title: str
    kind: Literal["read", "code", "run", "observe", "debug", "submit"]
    content: str  # relative markdown path
    focus_file: str | None = None
    hints: list[str] = Field(default_factory=list, max_length=4)
    completion: Completion


class Checkpoint(BaseModel):
    id: str = Field(pattern=IDENT)
    title: str
    tests: list[str]
    final: bool = False


class WorkspaceSpec(BaseModel):
    package: str = Field(pattern=IDENT)
    # packages from earlier lessons that this lesson's tests also run (submitted together with ``package``)
    uses: list[str] = []


class LessonCompletion(BaseModel):
    checkpoint: str


class Lesson(BaseModel):
    id: str = Field(pattern=IDENT)
    title: str
    description: str
    book_reference: BookReference
    difficulty: Literal["beginner", "intermediate", "advanced"]
    estimated_minutes: int
    objectives: list[str]
    prerequisites: list[str] = []
    ros_dependencies: list[str] = []
    skills: list[str] = []
    # separately installed desktop simulators the lesson needs (detected at start-up, see config.py)
    requires: list[Literal["webots", "coppeliasim"]] = []
    lab_tabs: list[Literal["graph", "topics", "terminal", "tests", "robot", "simulation", "tf", "controllers", "sensors"]]
    workspace: WorkspaceSpec
    levels: dict[str, str] = {"guided": "starter"}
    steps: list[Step]
    checkpoints: list[Checkpoint]
    completion: LessonCompletion

    @model_validator(mode="after")
    def _refs(self) -> "Lesson":
        cps = {c.id for c in self.checkpoints}
        for s in self.steps:
            if s.completion.type == "checkpoint" and s.completion.checkpoint not in cps:
                raise ValueError(f"step {s.id} references unknown checkpoint {s.completion.checkpoint}")
        if self.completion.checkpoint not in cps:
            raise ValueError("lesson completion references unknown checkpoint")
        if "guided" not in self.levels:
            raise ValueError("every lesson needs a 'guided' level")
        return self


class Reading(BaseModel):
    source: str  # key into Course.sources
    chapters: str = ""  # e.g. "6", "10–11", "6.9, 14.9"
    note: str = ""


class Chapter(BaseModel):
    number: int
    title: str
    book_chapter: BookChapter | None = None  # the original ROS 1 book chapter this one was ported from
    summary: str
    status: Literal["available", "planned"]
    # where the labs run: the native Windows runtime, a Linux VM managed by the academy (QEMU), or a bare-metal
    # x86 Linux host with a PREEMPT_RT kernel (latency numbers are only meaningful there)
    runtime: Literal["windows", "linux", "linux_rt_host"] = "windows"
    competencies: list[str] = []
    readings: list[Reading] = []
    labs: list[str] = []
    lessons: list[str] = []
    final_project: str = ""
    topics: list[str] = []


class Section(BaseModel):
    id: str
    title: str
    chapters: list[int]


class Competency(BaseModel):
    id: str = Field(pattern=IDENT)
    title: str


class Course(BaseModel):
    id: str
    title: str
    ros_distro: str
    description: str
    sources: dict[str, str] = {}
    competencies: list[Competency] = []
    sections: list[Section]
