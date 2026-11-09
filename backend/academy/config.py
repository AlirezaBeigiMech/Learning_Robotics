"""Runtime configuration. Every value can be overridden with an ``ACADEMY_*`` environment variable."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _env(name: str, default: str) -> str:
    return os.environ.get(f"ACADEMY_{name}", default)


def _find_install(env_names: tuple[str, ...], candidates: tuple[str, ...], marker: str) -> Path | None:
    """A separately installed desktop simulator: an explicit environment variable wins, then the usual install folders.
    ``marker`` (a file inside the install) guards against empty or half-removed folders."""
    for name in env_names:
        if os.environ.get(name):
            p = Path(os.environ[name])
            return p if (p / marker).is_file() else None
    local = os.environ.get("LOCALAPPDATA", "")
    for c in candidates:
        p = Path(c.replace("%LOCALAPPDATA%", local))
        if (p / marker).is_file():
            return p
    return None


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR", str(ROOT / "data"))))
    courses_dir: Path = field(default_factory=lambda: Path(_env("COURSES_DIR", str(ROOT / "courses"))))
    frontend_dist: Path = field(default_factory=lambda: Path(_env("FRONTEND_DIST", str(ROOT / "frontend" / "out"))))
    grader_support_dir: Path = ROOT / "backend" / "grader_support"
    agent_script: Path = ROOT / "backend" / "academy" / "telemetry" / "academy_agent.py"
    host: str = field(default_factory=lambda: _env("HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(_env("PORT", "8000")))
    database_url: str = field(default_factory=lambda: _env("DATABASE_URL", ""))
    # Workspace limits
    max_file_bytes: int = 256 * 1024
    max_files_per_package: int = 300
    # Runtime limits (per student, enforced with a Windows Job Object)
    job_memory_mb: int = field(default_factory=lambda: int(_env("JOB_MEMORY_MB", "4096")))
    job_max_processes: int = 128
    max_running_nodes: int = 8
    build_timeout_s: int = 600
    # DDS domain pools (Windows-safe port ranges)
    student_domains: tuple[int, int] = (1, 100)
    grader_domains: tuple[int, int] = (101, 120)
    grader_timeout_s: int = 480  # simulation lessons launch Gazebo several times per checkpoint
    grader_workers: int = 2
    # Chapter 5 simulators: not conda packages, so they are detected rather than installed by pixi
    webots_home: Path | None = field(default_factory=lambda: _find_install(
        ("ACADEMY_WEBOTS_HOME", "WEBOTS_HOME"),
        (r"%LOCALAPPDATA%\Programs\Webots", r"C:\Program Files\Webots"), r"msys64\mingw64\bin\webots.exe"))
    coppeliasim_root: Path | None = field(default_factory=lambda: _find_install(
        ("ACADEMY_COPPELIASIM_ROOT", "COPPELIASIM_ROOT_DIR"),
        (r"%LOCALAPPDATA%\Programs\CoppeliaSim", r"C:\Program Files\CoppeliaRobotics\CoppeliaSimEdu"), "coppeliaSim.exe"))
    simtools_dir: Path = ROOT / "backend" / "academy" / "simtools"

    @property
    def db_url(self) -> str:
        return self.database_url or f"sqlite:///{(self.data_dir / 'academy.db').as_posix()}"

    @property
    def workspaces_dir(self) -> Path:
        return self.data_dir / "workspaces"

    @property
    def grader_dir(self) -> Path:
        return self.data_dir / "grader"


settings = Settings()
