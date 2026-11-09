from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..content.loader import LoadedLesson
from ..models import LessonProgress, SkillMastery, Submission, utcnow


def get_progress(db: Session, user_id: int, lesson_id: str, create: bool = False) -> LessonProgress | None:
    row = db.scalar(select(LessonProgress).where(LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id))
    if row is None and create:
        row = LessonProgress(user_id=user_id, lesson_id=lesson_id, steps_completed=[], hints_used={})
        db.add(row)
        db.commit()
    return row


def mark_step(db: Session, prog: LessonProgress, step_id: str) -> None:
    if step_id not in prog.steps_completed:
        prog.steps_completed = [*prog.steps_completed, step_id]  # reassign so the JSON column is flagged dirty


def apply_submission(db: Session, sub: Submission, loaded: LoadedLesson) -> None:
    """On a passing submission, complete the steps gated by that checkpoint and, for the lesson's final
    checkpoint, the lesson itself plus its skills."""
    if sub.status != "passed":
        return
    prog = get_progress(db, sub.user_id, sub.lesson_id, create=True)
    for step in loaded.lesson.steps:
        if step.completion.type == "checkpoint" and step.completion.checkpoint == sub.checkpoint_id:
            mark_step(db, prog, step.id)
    if sub.checkpoint_id == loaded.lesson.completion.checkpoint and prog.status != "completed":
        prog.status = "completed"
        prog.completed_at = utcnow()
        for skill in loaded.lesson.skills:
            exists = db.scalar(select(SkillMastery).where(SkillMastery.user_id == sub.user_id, SkillMastery.skill == skill))
            if exists is None:
                db.add(SkillMastery(user_id=sub.user_id, skill=skill, evidence_submission_id=sub.id))
    db.commit()
