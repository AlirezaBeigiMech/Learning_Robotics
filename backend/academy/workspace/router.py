from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..content.loader import content
from ..db import get_db
from ..models import Event, User
from ..progress.service import get_progress
from ..security import current_user
from .manager import WorkspaceError, diagnose, get_workspace

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


class FileIn(BaseModel):
    path: str
    content: str = ""


class RenameIn(BaseModel):
    src: str
    dst: str


class DiagIn(BaseModel):
    path: str
    content: str


class OpenIn(BaseModel):
    level: str = "guided"


def _err(e: WorkspaceError) -> HTTPException:
    return HTTPException(400, str(e))


@router.get("/tree")
def tree(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    ws = get_workspace(db, user.id)
    return {"entries": ws.tree(), "packages": ws.packages(), "domain_id": ws.domain_id,
            "built": (ws.install / "setup.bat").is_file()}


@router.get("/file")
def read_file(path: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    try:
        return {"path": path, "content": get_workspace(db, user.id).read(path)}
    except WorkspaceError as e:
        raise _err(e) from e


@router.put("/file")
def save_file(body: FileIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    try:
        get_workspace(db, user.id).write(body.path, body.content)
    except WorkspaceError as e:
        raise _err(e) from e
    return {"ok": True, "diagnostics": diagnose(body.path, body.content)}


@router.post("/file")
def create_file(body: FileIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    try:
        get_workspace(db, user.id).write(body.path, body.content, create=True)
    except WorkspaceError as e:
        raise _err(e) from e
    return {"ok": True}


@router.post("/dir")
def create_dir(body: FileIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    try:
        get_workspace(db, user.id).mkdir(body.path)
    except WorkspaceError as e:
        raise _err(e) from e
    return {"ok": True}


@router.delete("/file")
def delete_file(path: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    try:
        get_workspace(db, user.id).delete(path)
    except WorkspaceError as e:
        raise _err(e) from e
    return {"ok": True}


@router.post("/rename")
def rename(body: RenameIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    try:
        get_workspace(db, user.id).rename(body.src, body.dst)
    except WorkspaceError as e:
        raise _err(e) from e
    return {"ok": True}


@router.post("/diagnostics")
def diagnostics(body: DiagIn, _: User = Depends(current_user)) -> dict:
    return {"diagnostics": diagnose(body.path, body.content)}


@router.post("/lessons/{lesson_id}/open")
def open_lesson(lesson_id: str, body: OpenIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    loaded = content().lessons.get(lesson_id)
    if loaded is None:
        raise HTTPException(404, "Unknown lesson")
    ws = get_workspace(db, user.id)
    prog = get_progress(db, user.id, lesson_id, create=True)
    migrated = ws.migrate_if_build_type_changed(loaded.lesson.workspace.package, loaded.level_dir("guided"))
    if migrated:
        db.add(Event(user_id=user.id, kind="package_migrated", lesson_id=lesson_id, payload={"backup": str(migrated)}))
        db.commit()
    created = ws.ensure_package(loaded.lesson.workspace.package, loaded.level_dir(prog.level if not body.level else body.level))
    if created:
        prog.level = body.level
        db.add(Event(user_id=user.id, kind="lesson_opened", lesson_id=lesson_id, payload={"level": body.level}))
        db.commit()
    return {"created": created or bool(migrated), "package": loaded.lesson.workspace.package, "level": prog.level,
            "migrated_backup": migrated.name if migrated else None}


@router.post("/lessons/{lesson_id}/reset")
def reset_lesson(lesson_id: str, body: OpenIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    loaded = content().lessons.get(lesson_id)
    if loaded is None:
        raise HTTPException(404, "Unknown lesson")
    ws = get_workspace(db, user.id)
    backup = ws.reset_package(loaded.lesson.workspace.package, loaded.level_dir(body.level))
    prog = get_progress(db, user.id, lesson_id, create=True)
    prog.level = body.level
    db.add(Event(user_id=user.id, kind="lesson_reset", lesson_id=lesson_id, payload={"backup": str(backup) if backup else None}))
    db.commit()
    return {"ok": True, "backup": backup.name if backup else None}
