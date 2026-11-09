from __future__ import annotations

import asyncio
import contextlib
import json

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import SessionLocal, get_db
from ..models import BuildAttempt, User, utcnow
from ..security import current_user, websocket_user
from ..workspace.manager import get_workspace
from .session import RuntimeErrorForUser, get_runtime
from .terminal import Terminal

router = APIRouter(tags=["runtime"])


class BuildIn(BaseModel):
    packages: list[str] | None = None
    lesson_id: str | None = None


class RunIn(BaseModel):
    package: str
    executable: str | None = None
    launch_file: str | None = None
    args: list[str] = Field(default_factory=list, max_length=20)


class StopIn(BaseModel):
    process_id: int | None = None


def _runtime(user: User, db: Session):
    return get_runtime(get_workspace(db, user.id))


@router.get("/api/runtime/status")
async def status(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return _runtime(user, db).status()


@router.post("/api/runtime/build")
async def build(body: BuildIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    rt = _runtime(user, db)
    attempt = BuildAttempt(user_id=user.id, lesson_id=body.lesson_id, packages=body.packages or [])
    db.add(attempt)
    db.commit()
    try:
        result = await rt.build(body.packages)
    except RuntimeErrorForUser as e:
        raise HTTPException(409, str(e)) from e
    attempt.finished_at = utcnow()
    attempt.exit_code = result["exit_code"]
    attempt.duration_ms = result["duration_ms"]
    attempt.output_tail = result["tail"][-8000:]
    db.commit()
    return result


@router.post("/api/runtime/run")
async def run(body: RunIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    rt = _runtime(user, db)
    try:
        proc = await asyncio.to_thread(rt.run, body.package, body.executable, body.launch_file, body.args)
    except RuntimeErrorForUser as e:
        raise HTTPException(409, str(e)) from e
    return proc.info()


@router.post("/api/runtime/stop")
async def stop(body: StopIn, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    rt = _runtime(user, db)
    try:
        if body.process_id is None:
            await asyncio.to_thread(rt.stop_all)
        else:
            await asyncio.to_thread(rt.stop, body.process_id)
    except RuntimeErrorForUser as e:
        raise HTTPException(404, str(e)) from e
    return {"ok": True}


@router.post("/api/runtime/restart")
async def restart(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    await _runtime(user, db).restart()
    return {"ok": True}


@router.get("/api/runtime/processes/{proc_id}/output")
async def output(proc_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    p = _runtime(user, db).procs.get(proc_id)
    if p is None:
        raise HTTPException(404, "Unknown process")
    return {"process": p.info(), "lines": list(p.tail)}


@router.get("/api/runtime/tf")
async def tf(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return _runtime(user, db).last_tf or {"type": "tf", "frames": []}


@router.get("/api/runtime/graph")
async def graph(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return _runtime(user, db).last_graph or {"type": "graph", "nodes": [], "topics": []}


def _agent_cmd(msg: dict) -> dict | None:
    """Whitelist and sanitise client commands before they reach the telemetry agent."""
    c = msg.get("cmd")
    if c in ("echo", "stop_echo") and isinstance(msg.get("topic"), str) and len(msg["topic"]) < 256:
        return {"cmd": c, "topic": msg["topic"]}
    if c == "snapshot":
        return {"cmd": c}
    if c == "robot_watch":
        return {"cmd": c, "enable": bool(msg.get("enable"))}
    if c == "joint_gui":
        positions = msg.get("positions") or {}
        if not isinstance(positions, dict) or len(positions) > 64:
            return None
        try:
            clean = {str(k)[:100]: float(v) for k, v in positions.items()}
        except (TypeError, ValueError):
            return None
        return {"cmd": c, "enable": bool(msg.get("enable")), "positions": clean}
    return None


@router.websocket("/ws/runtime")
async def runtime_ws(ws: WebSocket) -> None:
    user = websocket_user(ws)
    if user is None:
        await ws.close(code=4401)
        return
    await ws.accept()
    with SessionLocal() as db:
        rt = get_runtime(get_workspace(db, user.id))
    queue: asyncio.Queue = asyncio.Queue()
    rt.subscribers.add(queue)
    rt.ensure_agent()
    await ws.send_text(json.dumps({"type": "hello", "status": rt.status(), "graph": rt.last_graph}, default=str))

    async def pump_out() -> None:
        try:
            while True:
                # default=str: events may carry datetimes (e.g. graded submissions). A serialisation error
                # must never silently kill this sender while the socket stays open.
                await ws.send_text(json.dumps(await queue.get(), default=str))
        except Exception:
            with contextlib.suppress(Exception):
                await ws.close(code=1011)

    sender = asyncio.create_task(pump_out())
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            cmd = _agent_cmd(msg)
            if cmd is not None:
                rt.agent_command(cmd)
    except (WebSocketDisconnect, json.JSONDecodeError, RuntimeError):
        pass
    finally:
        sender.cancel()
        rt.subscribers.discard(queue)


@router.websocket("/ws/terminal")
async def terminal_ws(ws: WebSocket) -> None:
    user = websocket_user(ws)
    if user is None:
        await ws.close(code=4401)
        return
    await ws.accept()
    with SessionLocal() as db:
        rt = get_runtime(get_workspace(db, user.id))
    if rt.terminal is None or not rt.terminal.alive:
        rt.terminal = await asyncio.to_thread(Terminal, rt)
    term: Terminal = rt.terminal
    queue: asyncio.Queue = asyncio.Queue()
    term.listeners.add(queue)
    history = term.history()
    if history:
        await ws.send_text(history)

    async def pump_out() -> None:
        while True:
            chunk = await queue.get()
            if chunk is None:
                await ws.send_text("\r\n[terminal exited — reconnect to start a new one]\r\n")
                await ws.close()
                return
            await ws.send_text(chunk)

    sender = asyncio.create_task(pump_out())
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            if msg.get("type") == "input" and isinstance(msg.get("data"), str):
                term.write(msg["data"])
            elif msg.get("type") == "resize":
                term.resize(int(msg.get("rows", 24)), int(msg.get("cols", 100)))
    except (WebSocketDisconnect, json.JSONDecodeError, RuntimeError, ValueError):
        pass
    finally:
        sender.cancel()
        with contextlib.suppress(Exception):
            term.listeners.discard(queue)
