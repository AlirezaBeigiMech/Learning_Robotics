from __future__ import annotations

import mimetypes
from contextlib import asynccontextmanager

# Python's mimetypes reads the Windows registry, where .js is often mapped to text/plain. Browsers refuse
# to run web workers (Monaco's language services) served as text/plain, so pin the web types explicitly.
for _type, _ext in (("text/javascript", ".js"), ("text/javascript", ".mjs"), ("text/css", ".css"),
                    ("application/json", ".json"), ("image/svg+xml", ".svg"), ("application/wasm", ".wasm"),
                    ("font/ttf", ".ttf"), ("font/woff2", ".woff2")):
    mimetypes.add_type(_type, _ext)

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .assessment.router import router as assessment_router
from .config import settings
from .content.loader import content
from .content.router import router as content_router
from .db import init_db
from .progress.router import router as progress_router
from .robot.router import router as robot_router
from .runtime.router import router as runtime_router
from .runtime.session import shutdown_all
from .security import CLIENT_HEADER, current_user, host_is_local, origin_is_local
from .workspace.router import router as workspace_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    content()  # fail fast on invalid course content
    yield
    shutdown_all()


def create_app() -> FastAPI:
    app = FastAPI(title="Mastering ROS 2 Academy", version="0.1.0", lifespan=lifespan)
    for r in (content_router, workspace_router, runtime_router, assessment_router, progress_router, robot_router):
        app.include_router(r)

    @app.middleware("http")
    async def local_only_guard(request: Request, call_next):
        """Replaces sign-in: only this machine's own academy page may use the API (see security.py)."""
        path = request.url.path
        if not host_is_local(request.headers.get("host")):
            return JSONResponse({"detail": "The academy only answers on localhost"}, status_code=403)
        if not origin_is_local(request.headers.get("origin")):
            return JSONResponse({"detail": "Cross-site request refused"}, status_code=403)
        if path.startswith("/api/") and path != "/api/health" and not request.headers.get(CLIENT_HEADER):
            return JSONResponse({"detail": f"Missing {CLIENT_HEADER} header"}, status_code=403)
        return await call_next(request)

    @app.get("/api/me")
    def me(user=Depends(current_user)) -> dict:
        return {"id": user.id, "display_name": user.display_name}

    @app.get("/api/health")
    def health() -> dict:
        import os
        return {"ok": True, "ros_distro": os.environ.get("ROS_DISTRO"), "lessons": len(content().lessons)}

    dist = settings.frontend_dist
    if dist.is_dir():
        app.mount("/_next", StaticFiles(directory=dist / "_next"), name="next-assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith(("api/", "ws/")):
                return JSONResponse({"detail": "Not found"}, status_code=404)
            candidate = (dist / path).resolve()
            if dist.resolve() in candidate.parents or candidate == dist.resolve():
                for c in (candidate, candidate.with_suffix(".html"), candidate / "index.html"):
                    if c.is_file():
                        return FileResponse(c)
            return FileResponse(dist / "index.html")
    return app


app = create_app()
