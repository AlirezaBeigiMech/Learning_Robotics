"""A real OS process whose merged stdout/stderr is streamed line by line to a callback."""

from __future__ import annotations

import itertools
import re
import subprocess
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from .winjob import JobObject, kill_tree

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_ids = itertools.count(1)


def cmd_line(command: str) -> str:
    """Build a raw cmd.exe command line. Passing a list to Popen would re-quote it in a way cmd.exe
    misparses (`\\"` escapes), so the command is handed over verbatim with /s semantics."""
    return f'cmd.exe /d /s /c "{command}"'


@dataclass
class ManagedProcess:
    kind: str  # run | build | agent | grader
    label: str
    command: str | list[str]
    cwd: str
    env: dict[str, str]
    on_line: Callable[["ManagedProcess", str], None]
    on_exit: Callable[["ManagedProcess"], None]
    job: JobObject | None = None
    id: int = field(default_factory=lambda: next(_ids))
    started_at: float = 0.0
    ended_at: float | None = None
    exit_code: int | None = None
    stopped_by_user: bool = False
    tail: deque = field(default_factory=lambda: deque(maxlen=400))
    stdin_pipe: bool = False
    _popen: subprocess.Popen | None = None

    def start(self) -> "ManagedProcess":
        self.started_at = time.time()
        self._popen = subprocess.Popen(
            self.command, cwd=self.cwd, env=self.env,
            stdin=subprocess.PIPE if self.stdin_pipe else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
        )
        if self.job is not None:
            self.job.assign(self._popen.pid)
        threading.Thread(target=self._pump, name=f"proc-{self.id}", daemon=True).start()
        return self

    @property
    def pid(self) -> int | None:
        return self._popen.pid if self._popen else None

    @property
    def running(self) -> bool:
        return self._popen is not None and self.exit_code is None

    def write_line(self, line: str) -> None:
        if self._popen and self._popen.stdin and self.running:
            try:
                self._popen.stdin.write((line + "\n").encode("utf-8"))
                self._popen.stdin.flush()
            except OSError:
                pass

    def _pump(self) -> None:
        assert self._popen and self._popen.stdout
        for raw in iter(self._popen.stdout.readline, b""):
            line = ANSI_RE.sub("", raw.decode("utf-8", errors="replace").rstrip("\r\n"))
            self.tail.append(line)
            try:
                self.on_line(self, line)
            except Exception:  # never let a consumer kill the pump
                pass
        self.exit_code = self._popen.wait()
        self.ended_at = time.time()
        self.on_exit(self)

    def stop(self, timeout: float = 5.0) -> None:
        if not self.running or self._popen is None:
            return
        self.stopped_by_user = True
        kill_tree(self._popen.pid)
        try:
            self._popen.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._popen.kill()

    def info(self) -> dict:
        return {
            "id": self.id, "kind": self.kind, "label": self.label, "pid": self.pid,
            "running": self.running, "exit_code": self.exit_code, "started_at": self.started_at,
            "ended_at": self.ended_at, "stopped_by_user": self.stopped_by_user,
        }
