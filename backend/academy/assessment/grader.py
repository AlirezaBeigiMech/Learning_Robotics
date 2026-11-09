"""Isolated grader: a snapshot of the student's package is built and tested in a separate directory,
in its own DDS domain and Job Object. Hidden tests are copied only into the grader directory."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from pathlib import Path

from ..config import settings
from ..content.loader import LoadedLesson
from ..runtime.process import cmd_line
from ..runtime.session import compiler_diagnostics, ros_env, tool
from ..runtime.winjob import JobObject, keep_awake, kill_tree

_domain_lock = threading.Lock()
_domains_in_use: set[int] = set()


@contextmanager
def grader_domain():
    lo, hi = settings.grader_domains
    with _domain_lock:
        d = next((x for x in range(lo, hi + 1) if x not in _domains_in_use), None)
        if d is None:
            raise RuntimeError("All grader DDS domains are busy")
        _domains_in_use.add(d)
    try:
        yield d
    finally:
        with _domain_lock:
            _domains_in_use.discard(d)


def _run(command, cwd: Path, env: dict, timeout: float, job: JobObject) -> tuple[int, str, bool]:
    p = subprocess.Popen(command, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)
    job.assign(p.pid)
    # Output is drained on a thread and every wait has a deadline: a stray grandchild that inherited the
    # pipe must never be able to keep a grading run alive past its timeout.
    chunks: list[bytes] = []
    reader = threading.Thread(target=lambda: chunks.extend(iter(lambda: p.stdout.read(65536), b"")), daemon=True)
    reader.start()
    timed_out = False
    try:
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_tree(p.pid)
        job.terminate_all()
        try:
            p.wait(timeout=15)
        except subprocess.TimeoutExpired:
            p.kill()
    reader.join(timeout=10)
    out = b"".join(chunks).decode("utf-8", errors="replace")
    if timed_out:
        out += f"\n[grader] stopped after {timeout:.0f} s time limit"
    return (-1 if timed_out else p.returncode), out, timed_out


def parse_junit(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    tests = []
    for tc in ET.parse(path).getroot().iter("testcase"):
        props = {p.get("name"): p.get("value") for p in tc.iter("property")}
        status, message = "passed", ""
        for tag in ("failure", "error", "skipped"):
            el = tc.find(tag)
            if el is not None:
                status = {"failure": "failed", "error": "error", "skipped": "skipped"}[tag]
                message = (el.get("message") or el.text or "").strip()
                break
        hidden = props.get("hidden") == "1"
        tests.append({
            "id": tc.get("name"), "file": (tc.get("file") or tc.get("classname") or ""),
            "title": props.get("title", tc.get("name")), "status": status, "hidden": hidden,
            "duration_s": float(tc.get("time") or 0),
            "expected": props.get("expected"),
            # Hidden tests reveal what was expected, never the grader's inputs or raw failure text.
            "observed": None if hidden else props.get("observed"),
            "message": None if hidden else _short(message),
            "suggestion": props.get("suggestion") if status != "passed" else None,
        })
    return tests


def _short(msg: str, limit: int = 600) -> str:
    msg = msg.split("\nassert ")[0]
    return msg if len(msg) <= limit else msg[:limit] + "..."


def grade(files: dict[str, str], loaded: LoadedLesson, checkpoint_id: str, work_dir: Path) -> dict:
    """Build + test ``files`` (paths relative to src/) against a checkpoint. Returns the results document."""
    with keep_awake():  # a laptop dozing off mid-run would otherwise produce spurious time-outs
        return _grade(files, loaded, checkpoint_id, work_dir)


def _grade(files: dict[str, str], loaded: LoadedLesson, checkpoint_id: str, work_dir: Path) -> dict:
    cp = next(c for c in loaded.lesson.checkpoints if c.id == checkpoint_id)
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
    src, tests_dir = work_dir / "ws" / "src", work_dir / "tests"
    for rel, text in files.items():
        dst = src / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")
    tests_dir.mkdir(parents=True)
    for t in cp.tests:
        shutil.copy2(loaded.tests_dir / t, tests_dir / t)
    if (loaded.tests_dir / "reference").is_dir():  # reference models used by behavioural comparisons
        shutil.copytree(loaded.tests_dir / "reference", tests_dir / "reference")
    (work_dir / "logs").mkdir()

    log: list[str] = []
    t0 = time.time()
    job = JobObject(settings.job_memory_mb, settings.job_max_processes)
    try:
        with grader_domain() as domain:
            env = ros_env(domain, work_dir / "logs")
            env["PYTHONPATH"] = os.pathsep.join([str(settings.grader_support_dir), env.get("PYTHONPATH", "")])
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            code, out, timed_out = _run(
                [tool("colcon"), "build", "--merge-install", "--event-handlers", "console_direct+", "desktop_notification-",
                 "status-", "--base-paths", "src"], work_dir / "ws", env, settings.build_timeout_s, job)
            log.append(out)
            if code != 0:
                return {"build": {"ok": False, "log_tail": "\n".join(out.splitlines()[-60:]), "timed_out": timed_out,
                                  "diagnostics": compiler_diagnostics(out.splitlines(), src)},
                        "tests": [], "summary": {"passed": 0, "failed": 0, "total": len(cp.tests), "duration_s": time.time() - t0},
                        "log": "\n".join(log)}
            junit = work_dir / "junit.xml"
            remaining = max(30.0, settings.grader_timeout_s - (time.time() - t0))
            pytest_cmd = cmd_line(
                f'call "{work_dir / "ws" / "install" / "setup.bat"}" && "{sys.executable}" -m pytest "{tests_dir}" '
                f'-p academy_grader.plugin -p no:cacheprovider -o junit_family=xunit1 --junitxml="{junit}" '
                f'-q --tb=short --rootdir "{tests_dir}"')
            code, out, timed_out = _run(pytest_cmd, work_dir, env, remaining, job)
            log.append(out)
    finally:
        job.close()

    tests = parse_junit(work_dir / "junit.xml")
    if not tests:
        tests = [{"id": "grader", "title": "Test run", "status": "error", "hidden": False,
                  "message": "Timed out" if timed_out else "The test run produced no results",
                  "expected": None, "observed": None, "suggestion": "Check that your nodes start and do not block forever.",
                  "file": "", "duration_s": 0}]
    passed = sum(t["status"] == "passed" for t in tests)
    return {"build": {"ok": True, "log_tail": ""}, "tests": tests,
            "summary": {"passed": passed, "failed": len(tests) - passed, "total": len(tests),
                        "duration_s": round(time.time() - t0, 1), "timed_out": timed_out},
            "log": "\n".join(log)[-20000:]}
