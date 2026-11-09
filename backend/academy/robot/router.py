"""Robot-model preview: expand the student's URDF/xacro with the real xacro tool and analyse it.

This backs the live 3D preview in the editor (Chapter 3). It is labelled in the UI as a preview of the
file; what ROS actually uses is shown separately, from /robot_description and TF."""

from __future__ import annotations

import asyncio
import subprocess
import sys
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import User
from ..runtime.process import cmd_line
from ..runtime.session import ros_env, tool
from ..security import current_user
from ..workspace.manager import StudentWorkspace, WorkspaceError, get_workspace

sys.path.insert(0, str(settings.grader_support_dir))
from academy_grader import urdf_tools  # noqa: E402

router = APIRouter(prefix="/api/robot", tags=["robot"])


class PreviewIn(BaseModel):
    path: str
    content: str | None = Field(default=None, max_length=512 * 1024)


def _expand(ws: StudentWorkspace, rel: str, content: str | None) -> dict:
    target = ws.resolve(rel)
    if not (target.name.endswith(".urdf") or target.name.endswith(".xacro")):
        raise WorkspaceError("Preview works on .urdf and .xacro files")
    if content is None and not target.is_file():
        raise WorkspaceError("File not found")
    # Unsaved editor content is expanded from a temp file next to the original, so relative
    # <xacro:include filename="..."/> paths resolve exactly as they will after saving.
    src = target
    if content is not None:
        src = target.with_name(f".~preview-{uuid.uuid4().hex[:8]}-{target.name}")
        src.write_text(content, encoding="utf-8")
    try:
        setup = ws.install / "setup.bat"
        if setup.is_file():  # overlay makes $(find <your_package>) work
            command = cmd_line(f'call "{setup}" && xacro "{src}"')
        else:
            command = [tool("xacro"), str(src)]
        p = subprocess.run(command, cwd=str(target.parent), env=ros_env(ws.domain_id, ws.log_dir), capture_output=True,
                           timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    finally:
        if src != target:
            src.unlink(missing_ok=True)
    out = p.stdout.decode("utf-8", errors="replace")
    err = p.stderr.decode("utf-8", errors="replace").replace(src.name, target.name)
    if p.returncode != 0 or "<robot" not in out:
        hint = ""
        if "$(find" in (content or "") and not setup.is_file():
            hint = " $(find ...) needs the package to be built once."
        return {"ok": False, "error": (err.strip() or "xacro produced no robot") + hint}
    try:
        robot = urdf_tools.load(out)
    except Exception as e:  # malformed URDF after expansion
        return {"ok": False, "error": f"URDF parse error: {e}"}
    return {"ok": True, "urdf": out, "diagnostics": urdf_tools.analyze(robot),
            "summary": {"name": robot.name, "links": len(robot.links), "joints": len(robot.joints),
                        "movable": sum(j.type != "fixed" for j in robot.joints), "roots": urdf_tools.roots(robot)}}


@router.post("/preview")
async def preview(body: PreviewIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    ws = get_workspace(db, user.id)
    try:
        return await asyncio.to_thread(_expand, ws, body.path, body.content)
    except WorkspaceError as e:
        raise HTTPException(400, str(e)) from e
    except subprocess.TimeoutExpired as e:
        raise HTTPException(408, "xacro took longer than 30 s") from e
