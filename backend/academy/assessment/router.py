from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..content.loader import content
from ..db import SessionLocal, get_db
from ..models import Event, Submission, User, utcnow
from ..progress.service import apply_submission
from ..runtime.session import peek_runtime
from ..security import current_user
from ..workspace.manager import WorkspaceError, get_workspace
from .grader import grade

router = APIRouter(prefix="/api/assessment", tags=["assessment"])
_executor = ThreadPoolExecutor(max_workers=settings.grader_workers, thread_name_prefix="grader")


class SubmitIn(BaseModel):
    lesson_id: str
    checkpoint_id: str


def submission_out(s: Submission, include_log: bool = False) -> dict:
    results = dict(s.results or {})
    log = results.pop("log", None)
    out = {"id": s.id, "lesson_id": s.lesson_id, "checkpoint_id": s.checkpoint_id, "status": s.status,
           "score": s.score, "created_at": s.created_at, "finished_at": s.finished_at, "results": results}
    if include_log:
        out["log"] = log
    return out


def _grade_job(sub_id: int) -> None:
    with SessionLocal() as db:
        sub = db.get(Submission, sub_id)
        loaded = content().lessons[sub.lesson_id]
        sub.status = "running"
        db.commit()
        try:
            results = grade(sub.files, loaded, sub.checkpoint_id, settings.grader_dir / str(sub.id))
            summary = results["summary"]
            sub.results = results
            sub.score = summary["passed"] / summary["total"] if summary["total"] else 0.0
            sub.status = "passed" if results["build"]["ok"] and summary["total"] and summary["failed"] == 0 else "failed"
        except Exception as e:  # report grader faults honestly instead of a fake pass/fail
            sub.status = "error"
            sub.results = {"build": {"ok": False, "log_tail": ""}, "tests": [], "summary": {"passed": 0, "failed": 0, "total": 0},
                           "error": f"Grader error: {type(e).__name__}: {e}"}
        sub.finished_at = utcnow()
        db.add(Event(user_id=sub.user_id, kind="submission_graded", lesson_id=sub.lesson_id,
                     payload={"submission_id": sub.id, "status": sub.status, "score": sub.score}))
        db.commit()
        apply_submission(db, sub, loaded)
        rt = peek_runtime(sub.user_id)
        if rt:
            rt.broadcast({"type": "submission", "submission": submission_out(sub)})


@router.post("/submit")
async def submit(body: SubmitIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    loaded = content().lessons.get(body.lesson_id)
    if loaded is None or body.checkpoint_id not in {c.id for c in loaded.lesson.checkpoints}:
        raise HTTPException(404, "Unknown lesson or checkpoint")
    busy = db.scalar(select(Submission).where(Submission.user_id == user.id, Submission.status.in_(["queued", "running"])))
    if busy:
        raise HTTPException(409, "A submission is already being graded")
    try:
        ws = get_workspace(db, user.id)
        files = ws.snapshot_package(loaded.lesson.workspace.package)
        for pkg in loaded.lesson.workspace.uses:  # e.g. the CoppeliaSim bridge from the previous lesson
            try:
                files.update(ws.snapshot_package(pkg))
            except WorkspaceError as e:
                raise WorkspaceError(f"This checkpoint also runs your '{pkg}' package from an earlier lesson. {e}") from e
    except WorkspaceError as e:
        raise HTTPException(400, str(e)) from e
    sub = Submission(user_id=user.id, lesson_id=body.lesson_id, checkpoint_id=body.checkpoint_id, files=files)
    db.add(sub)
    db.commit()
    asyncio.get_running_loop().run_in_executor(_executor, _grade_job, sub.id)
    return submission_out(sub)


@router.get("/submissions/{sub_id}")
def get_submission(sub_id: int, log: bool = False, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    sub = db.get(Submission, sub_id)
    if sub is None or sub.user_id != user.id:
        raise HTTPException(404, "Not found")
    return submission_out(sub, include_log=log)


@router.get("/submissions")
def list_submissions(lesson_id: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    q = select(Submission).where(Submission.user_id == user.id)
    if lesson_id:
        q = q.where(Submission.lesson_id == lesson_id)
    return [submission_out(s) for s in db.scalars(q.order_by(Submission.id.desc()).limit(50))]
