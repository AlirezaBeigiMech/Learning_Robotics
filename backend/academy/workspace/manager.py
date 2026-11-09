"""Per-student colcon workspace on disk. All paths are relative to ``<ws>/src`` and are validated so a
student can never read or write outside their own source tree."""

from __future__ import annotations

import ast
import shutil
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Workspace

IGNORED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".git"}
ALLOWED_SUFFIXES = {
    ".py", ".cfg", ".xml", ".txt", ".md", ".yaml", ".yml", ".msg", ".srv", ".action",
    ".cpp", ".hpp", ".h", ".c", ".launch", ".json", ".toml", ".urdf", ".xacro", ".sdf", ".rviz", ".ini", "",
    ".lua", ".wbt",  # CoppeliaSim scripts, Webots worlds (Chapter 5)
}


class WorkspaceError(ValueError):
    pass


@dataclass
class StudentWorkspace:
    user_id: int
    root: Path  # <data>/workspaces/<user>
    domain_id: int

    @property
    def ws(self) -> Path:
        return self.root / "ws"

    @property
    def src(self) -> Path:
        return self.ws / "src"

    @property
    def install(self) -> Path:
        return self.ws / "install"

    @property
    def log_dir(self) -> Path:
        return self.root / "ros_logs"

    # ---- path safety -------------------------------------------------------------------------
    def resolve(self, rel: str) -> Path:
        if not rel or len(rel) > 300:
            raise WorkspaceError("Invalid path")
        p = PurePosixPath(rel.replace("\\", "/"))
        if p.is_absolute() or ".." in p.parts or any(":" in part for part in p.parts):
            raise WorkspaceError("Path must be relative to the workspace src folder")
        if any(part in IGNORED_DIRS or part.startswith(".") for part in p.parts):
            raise WorkspaceError("Hidden and cache folders are not editable")
        full = (self.src / Path(*p.parts)).resolve()
        if self.src.resolve() not in full.parents:
            raise WorkspaceError("Path escapes the workspace")
        return full

    # ---- files -------------------------------------------------------------------------------
    def tree(self) -> list[dict]:
        out = []
        if not self.src.exists():
            return out
        for p in sorted(self.src.rglob("*")):
            rel = p.relative_to(self.src)
            if any(part in IGNORED_DIRS for part in rel.parts) or p.is_symlink() or p.name.startswith(".~"):
                continue  # .~preview-* are transient files of the robot preview
            out.append({"path": rel.as_posix(), "type": "dir" if p.is_dir() else "file",
                        "size": p.stat().st_size if p.is_file() else None})
        return out

    def packages(self) -> list[str]:
        return sorted(p.parent.name for p in self.src.glob("*/package.xml"))

    def read(self, rel: str) -> str:
        p = self.resolve(rel)
        if not p.is_file():
            raise WorkspaceError("File not found")
        if p.stat().st_size > settings.max_file_bytes:
            raise WorkspaceError("File too large to open in the editor")
        try:
            return p.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            raise WorkspaceError("Binary files cannot be opened in the editor") from e

    def write(self, rel: str, text: str, create: bool = False) -> None:
        p = self.resolve(rel)
        if p.suffix not in ALLOWED_SUFFIXES:
            raise WorkspaceError(f"File type '{p.suffix}' is not allowed")
        data = text.encode("utf-8")
        if len(data) > settings.max_file_bytes:
            raise WorkspaceError("File too large")
        if create and p.exists():
            raise WorkspaceError("File already exists")
        if not create and not p.is_file():
            raise WorkspaceError("File not found")
        if create and sum(1 for f in self.src.rglob("*") if f.is_file()) >= settings.max_files_per_package * 4:
            raise WorkspaceError("Workspace file limit reached")
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp~")
        tmp.write_bytes(data)
        tmp.replace(p)

    def mkdir(self, rel: str) -> None:
        self.resolve(rel).mkdir(parents=True, exist_ok=True)

    def delete(self, rel: str) -> None:
        p = self.resolve(rel)
        if p.is_dir():
            shutil.rmtree(p)
        elif p.is_file():
            p.unlink()
        else:
            raise WorkspaceError("Not found")

    def rename(self, src_rel: str, dst_rel: str) -> None:
        s, d = self.resolve(src_rel), self.resolve(dst_rel)
        if not s.exists():
            raise WorkspaceError("Not found")
        if d.exists():
            raise WorkspaceError("Destination exists")
        d.parent.mkdir(parents=True, exist_ok=True)
        s.rename(d)

    def snapshot_package(self, package: str) -> dict[str, str]:
        pkg = self.resolve(package)
        if not (pkg / "package.xml").is_file():
            raise WorkspaceError(f"Package '{package}' not found in your workspace")
        files: dict[str, str] = {}
        total = 0
        for p in sorted(pkg.rglob("*")):
            rel = p.relative_to(self.src)
            if p.is_file() and not any(part in IGNORED_DIRS for part in rel.parts) and p.suffix in ALLOWED_SUFFIXES:
                text = p.read_text(encoding="utf-8", errors="replace")
                total += len(text)
                if len(files) >= settings.max_files_per_package or total > 4 * 1024 * 1024:
                    raise WorkspaceError("Package too large to submit")
                files[rel.as_posix()] = text
        return files

    # ---- lesson materialisation ----------------------------------------------------------------
    def ensure_package(self, package: str, starter_root: Path) -> bool:
        """Copy the starter package into src if the student does not have it yet. Returns True if created."""
        target = self.src / package
        if target.exists():
            return False
        self.src.mkdir(parents=True, exist_ok=True)
        shutil.copytree(starter_root / package, target, ignore=shutil.ignore_patterns("__pycache__"))
        return True

    def migrate_if_build_type_changed(self, package: str, starter_root: Path) -> Path | None:
        """When course material changes a lesson's package type (e.g. Python -> C++), move the student's old
        package to backups instead of leaving an incompatible package in place. Never deletes student work."""
        from catkin_pkg.package import parse_package

        current, starter = self.src / package / "package.xml", starter_root / package / "package.xml"
        if not current.is_file() or not starter.is_file():
            return None
        try:
            if parse_package(str(current)).get_build_type() == parse_package(str(starter)).get_build_type():
                return None
        except Exception:
            return None  # an invalid package.xml is the student's to fix, not ours to move
        return self.reset_package(package, starter_root)

    def reset_package(self, package: str, starter_root: Path) -> Path | None:
        """Move the current package to a timestamped backup and restore the starter. Returns backup path."""
        target = self.src / package
        backup = None
        if target.exists():
            backup = self.root / "backups" / f"{package}-{time.strftime('%Y%m%d-%H%M%S')}"
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(backup))
        self.ensure_package(package, starter_root)
        return backup


def get_workspace(db: Session, user_id: int) -> StudentWorkspace:
    row = db.scalar(select(Workspace).where(Workspace.user_id == user_id))
    if row is None:
        used = set(db.scalars(select(Workspace.ros_domain_id)))
        lo, hi = settings.student_domains
        free = next((d for d in range(lo, hi + 1) if d not in used), None)
        if free is None:
            raise WorkspaceError("No free ROS_DOMAIN_ID left for a new student on this machine")
        root = settings.workspaces_dir / str(user_id)
        row = Workspace(user_id=user_id, path=str(root), ros_domain_id=free)
        db.add(row)
        db.commit()
    ws = StudentWorkspace(user_id, Path(row.path), row.ros_domain_id)
    ws.src.mkdir(parents=True, exist_ok=True)
    ws.log_dir.mkdir(parents=True, exist_ok=True)
    return ws


# ---- diagnostics ------------------------------------------------------------------------------
def diagnose(path: str, text: str) -> list[dict]:
    """Fast static diagnostics shown as editor markers. These complement, never replace, a real build."""
    out: list[dict] = []
    name = PurePosixPath(path).name
    if path.endswith(".py"):
        try:
            ast.parse(text, filename=path)
        except SyntaxError as e:
            out.append({"line": e.lineno or 1, "column": (e.offset or 1), "severity": "error",
                        "message": f"SyntaxError: {e.msg}", "source": "python"})
    elif name == "package.xml":
        from catkin_pkg.package import InvalidPackage, parse_package_string

        try:
            pkg = parse_package_string(text)
            if not pkg.get_build_type():
                out.append({"line": 1, "column": 1, "severity": "warning", "source": "catkin_pkg",
                            "message": "No <build_type> export: colcon will not treat this as a ROS package"})
        except InvalidPackage as e:
            for msg in str(e).splitlines()[1:] or [str(e)]:
                out.append({"line": 1, "column": 1, "severity": "error", "source": "catkin_pkg",
                            "message": f"{msg.strip()} — colcon would not recognise this as a ROS package"})
        except Exception as e:  # malformed XML
            out.append({"line": 1, "column": 1, "severity": "error", "source": "xml", "message": str(e)})
    return out
