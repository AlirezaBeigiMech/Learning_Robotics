"""Single local student — no accounts, no sign-in.

The academy runs on the student's own PC and only listens on 127.0.0.1. Because this server builds and runs
code, the absence of a login must not let *other websites* drive it from the student's browser. Every request
is therefore checked by `LocalOnlyGuard` (app.py):

* Host header must be localhost/127.0.0.1  -> blocks DNS-rebinding attacks;
* Origin header, when present, must be the academy itself  -> blocks cross-site requests and WebSockets;
* /api requests must carry the `X-Academy-Client` header  -> a cross-site page cannot add it without a CORS
  preflight, which this server never approves.
"""

from __future__ import annotations

import getpass
from urllib.parse import urlparse

from fastapi import Depends, WebSocket
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal, get_db
from .models import User

CLIENT_HEADER = "x-academy-client"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]"}


def _display_name() -> str:
    try:
        return getpass.getuser() or "Student"
    except Exception:
        return "Student"


def local_user(db: Session) -> User:
    """The one student of this installation (the first row; created on first use).
    Taking the first existing row keeps progress made under the earlier account-based version."""
    user = db.scalar(select(User).order_by(User.id).limit(1))
    if user is None:
        user = User(email="local@localhost", display_name=_display_name(), password_hash="")
        db.add(user)
        db.commit()
    return user


def current_user(db: Session = Depends(get_db)) -> User:
    return local_user(db)


def host_is_local(host_header: str | None) -> bool:
    if not host_header:
        return False
    host = host_header.rsplit(":", 1)[0] if not host_header.startswith("[") else host_header.split("]")[0] + "]"
    return host.lower() in LOCAL_HOSTS


def origin_is_local(origin: str | None) -> bool:
    """No Origin header (same-origin GET, CLI tools) is fine; a present Origin must be a local page."""
    if not origin:
        return True
    return host_is_local(urlparse(origin).netloc)


def websocket_user(ws: WebSocket) -> User | None:
    if not host_is_local(ws.headers.get("host")) or not origin_is_local(ws.headers.get("origin")):
        return None
    with SessionLocal() as db:
        return local_user(db)
