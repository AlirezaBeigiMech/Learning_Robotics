from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..content.loader import content, read_tree
from ..db import get_db
from ..models import BuildAttempt, Event, LessonProgress, SkillMastery, Submission, User
from ..runtime.session import peek_runtime
from ..security import current_user
from .service import get_progress, mark_step

router = APIRouter(prefix="/api/progress", tags=["progress"])


class HintIn(BaseModel):
    level: int


class StepIn(BaseModel):
    step_id: str


def _progress_out(p: LessonProgress | None) -> dict:
    if p is None:
        return {"status": "not_started", "steps_completed": [], "hints_used": {}, "current_step": None, "level": "guided"}
    return {"status": p.status, "steps_completed": p.steps_completed, "hints_used": p.hints_used,
            "current_step": p.current_step, "level": p.level, "completed_at": p.completed_at}


def _loaded(lesson_id: str):
    loaded = content().lessons.get(lesson_id)
    if loaded is None:
        raise HTTPException(404, "Unknown lesson")
    return loaded


@router.get("")
def overview(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(LessonProgress).where(LessonProgress.user_id == user.id)).all()
    subs = db.scalars(select(Submission).where(Submission.user_id == user.id)).all()
    builds = db.scalar(select(func.count()).select_from(BuildAttempt).where(BuildAttempt.user_id == user.id)) or 0
    ok_builds = db.scalar(select(func.count()).select_from(BuildAttempt).where(BuildAttempt.user_id == user.id, BuildAttempt.exit_code == 0)) or 0
    skills = db.scalars(select(SkillMastery).where(SkillMastery.user_id == user.id)).all()
    lessons = content().lessons
    portfolio = []
    for r in rows:
        if r.status == "completed" and r.lesson_id in lessons:
            best = max((s for s in subs if s.lesson_id == r.lesson_id and s.status == "passed"), key=lambda s: s.id, default=None)
            portfolio.append({"lesson_id": r.lesson_id, "title": lessons[r.lesson_id].lesson.title,
                              "completed_at": r.completed_at, "submission_id": best.id if best else None,
                              "package": lessons[r.lesson_id].lesson.workspace.package})
    current = max(rows, key=lambda r: r.started_at, default=None)
    return {
        "lessons": {r.lesson_id: _progress_out(r) for r in rows},
        "current_lesson": current.lesson_id if current else None,
        "stats": {"build_attempts": builds, "successful_builds": ok_builds, "submissions": len(subs),
                  "passed_submissions": sum(s.status == "passed" for s in subs),
                  "hints_used": sum(sum(r.hints_used.values()) for r in rows),
                  "lessons_completed": sum(r.status == "completed" for r in rows)},
        "skills": [{"skill": s.skill, "achieved_at": s.achieved_at} for s in skills],
        "portfolio": portfolio,
    }


@router.get("/lessons/{lesson_id}")
def lesson_progress(lesson_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    _loaded(lesson_id)
    return _progress_out(get_progress(db, user.id, lesson_id))


@router.post("/lessons/{lesson_id}/current")
def set_current(lesson_id: str, body: StepIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    loaded = _loaded(lesson_id)
    if body.step_id not in {s.id for s in loaded.lesson.steps}:
        raise HTTPException(404, "Unknown step")
    prog = get_progress(db, user.id, lesson_id, create=True)
    prog.current_step = body.step_id
    db.commit()
    return _progress_out(prog)


def _check_tf(user_id: int, completion) -> tuple[bool, str]:
    rt = peek_runtime(user_id)
    tf = rt.last_tf if rt else None
    if not tf or not tf.get("frames"):
        return False, "No TF data yet — launch your robot and open the Robot or TF Tree tab."
    now = time.time()
    frames = {f["child"]: f for f in tf["frames"]}
    stale = lambda f: not f["static"] and f["age"] + (now - tf["t"]) > 5
    roots = {f["parent"] for f in tf["frames"]} - set(frames)
    # A frame counts only if its OWN transform is published (or it is the root). Appearing merely as the
    # parent of another frame (e.g. tilt_link above a static camera_link) does not place it in the tree.
    missing = [x for x in completion.frames if x not in frames and x not in roots]
    if missing:
        return False, f"Not in the live TF tree: {', '.join(missing)}."
    old = [x for x in completion.frames if x in frames and stale(frames[x])]
    if old:
        return False, f"TF for {', '.join(old)} is stale (no updates for >5 s). Is something publishing /joint_states?"
    if len(roots) > 1:
        return False, f"The TF tree is split into {len(roots)} trees (roots: {', '.join(sorted(roots))})."
    return True, "Verified in the live TF tree."


def _check_controllers(user_id: int, completion) -> tuple[bool, str]:
    rt = peek_runtime(user_id)
    ev = rt.last_controllers if rt else None
    if not ev or not ev.get("managers") or time.time() - ev.get("t", 0) > 10:
        return False, "No controller_manager is running. Launch your simulation first."
    states = {c["name"]: c["state"] for m in ev["managers"] for c in m["controllers"]}
    missing = [c for c in completion.controllers if c not in states]
    if missing:
        return False, f"Not loaded: {', '.join(missing)}. Check the spawner in your launch file and controllers.yaml."
    inactive = [f"{c} ({states[c]})" for c in completion.controllers if states[c] != "active"]
    if inactive:
        return False, f"Loaded but not active: {', '.join(inactive)}."
    return True, "Verified: " + ", ".join(completion.controllers) + " are active."


def _check_graph(user_id: int, completion) -> tuple[bool, str]:
    rt = peek_runtime(user_id)
    graph = rt.last_graph if rt else None
    if not graph or time.time() - graph.get("t", 0) > 5:
        return False, "No live ROS graph yet — open the lab panel and run your nodes."
    nodes = {n["name"] for n in graph["nodes"]}
    if completion.type == "graph":
        if completion.node not in nodes:
            return False, f"Node {completion.node} is not running right now."
        for topic, role in ((completion.publishes, "publishers"), (completion.subscribes, "subscribers")):
            if topic:
                t = next((t for t in graph["topics"] if t["name"] == topic), None)
                if t is None or completion.node not in {e["node"] for e in t[role]}:
                    verb = "publishing on" if role == "publishers" else "subscribed to"
                    return False, f"{completion.node} is running but is not {verb} {topic}."
        return True, "Verified in the live ROS graph."
    # graph_qos_mismatch
    t = next((t for t in graph["topics"] if t["name"] == completion.topic), None)
    if t is None:
        return False, f"{completion.topic} is not in the graph. Run both nodes."
    bad = [p for p in t["qos_pairs"] if p["compatible"] == "error"]
    if not bad:
        return False, f"Publisher and subscriber on {completion.topic} are currently QoS-compatible."
    return True, f"Reproduced: {bad[0]['reason'] or 'incompatible QoS'}"


@router.post("/lessons/{lesson_id}/steps/{step_id}/complete")
def complete_step(lesson_id: str, step_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    loaded = _loaded(lesson_id)
    step = next((s for s in loaded.lesson.steps if s.id == step_id), None)
    if step is None:
        raise HTTPException(404, "Unknown step")
    prog = get_progress(db, user.id, lesson_id, create=True)
    c = step.completion
    if c.type == "manual":
        ok, reason = True, "Marked as done."
    elif c.type == "checkpoint":
        passed = db.scalar(select(Submission).where(Submission.user_id == user.id, Submission.lesson_id == lesson_id,
                                                    Submission.checkpoint_id == c.checkpoint, Submission.status == "passed"))
        ok, reason = (passed is not None,
                      "Checkpoint passed." if passed else "Run the checkpoint tests and make them pass to complete this step.")
    elif c.type == "tf_frames":
        ok, reason = _check_tf(user.id, c)
    elif c.type == "controllers_active":
        ok, reason = _check_controllers(user.id, c)
    else:
        ok, reason = _check_graph(user.id, c)
    if ok:
        mark_step(db, prog, step_id)
        db.add(Event(user_id=user.id, kind="step_completed", lesson_id=lesson_id, payload={"step": step_id}))
        db.commit()
    return {"completed": ok, "reason": reason, "progress": _progress_out(prog)}


@router.post("/lessons/{lesson_id}/steps/{step_id}/hint")
def hint(lesson_id: str, step_id: str, body: HintIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    loaded = _loaded(lesson_id)
    step = next((s for s in loaded.lesson.steps if s.id == step_id), None)
    if step is None:
        raise HTTPException(404, "Unknown step")
    max_level = len(step.hints) + 1
    prog = get_progress(db, user.id, lesson_id, create=True)
    used = prog.hints_used.get(step_id, 0)
    if not 1 <= body.level <= max_level:
        raise HTTPException(400, "Invalid hint level")
    if body.level > used + 1:
        raise HTTPException(400, "Hints are revealed one level at a time")
    if body.level > used:
        prog.hints_used = {**prog.hints_used, step_id: body.level}
        db.add(Event(user_id=user.id, kind="hint_used", lesson_id=lesson_id, payload={"step": step_id, "level": body.level}))
        db.commit()
    if body.level <= len(step.hints):
        return {"level": body.level, "max_level": max_level, "text": step.hints[body.level - 1]}
    return {"level": body.level, "max_level": max_level, "text": "Reference solution (try to understand it, then write your own):",
            "solution": read_tree(loaded.solution_dir)}


@router.get("/lessons/{lesson_id}/hints")
def hints_revealed(lesson_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Re-deliver hints the student has already unlocked (e.g. after a page reload)."""
    loaded = _loaded(lesson_id)
    prog = get_progress(db, user.id, lesson_id)
    out: dict[str, list[dict]] = {}
    for step in loaded.lesson.steps:
        used = prog.hints_used.get(step.id, 0) if prog else 0
        items = [{"level": i + 1, "text": step.hints[i]} for i in range(min(used, len(step.hints)))]
        if used > len(step.hints):
            items.append({"level": used, "text": "Reference solution (try to understand it, then write your own):",
                          "solution": read_tree(loaded.solution_dir)})
        out[step.id] = items
    return out
