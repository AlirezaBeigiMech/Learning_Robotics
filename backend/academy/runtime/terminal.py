"""A real interactive PowerShell (ConPTY) with the student's ROS 2 environment."""

from __future__ import annotations

import asyncio
import base64
import re
import threading
from collections import deque

from winpty import PtyProcess

SCROLLBACK_BYTES = 128 * 1024
# Device-attribute (ESC[c, ESC[>c), status/cursor-position report (ESC[5n, ESC[6n) and window-op (ESC[..t) queries
QUERY_RE = re.compile(r"\x1b\[[>=?]?[0-9;]*c|\x1b\[[56]n|\x1b\[[0-9;]*t")


class Terminal:
    def __init__(self, runtime, rows: int = 24, cols: int = 100) -> None:
        self.runtime = runtime
        self.listeners: set[asyncio.Queue] = set()
        self.scrollback: deque[str] = deque()
        self._size = 0
        ws = runtime.ws
        # The ROS underlay is already active (inherited from the pixi environment), so only the student's
        # overlay is sourced. RoboStack ships no underlay local_setup.ps1, so install\setup.ps1 would print a
        # chaining error in every new terminal.
        init = (
            f"Set-Location -LiteralPath '{ws.ws}'; "
            "if (Test-Path .\\install\\local_setup.ps1) { . .\\install\\local_setup.ps1 }; "
            "function global:prompt { \"ros2[$env:ROS_DOMAIN_ID] $(Split-Path -Leaf (Get-Location))> \" }; "
            f"Write-Host 'ROS 2 Jazzy terminal  |  ROS_DOMAIN_ID={ws.domain_id}  |  discovery: localhost only' -ForegroundColor Cyan; "
            "Write-Host 'Tip: after colcon build, re-source the overlay with  . .\\install\\local_setup.ps1' -ForegroundColor DarkGray"
        )
        encoded = base64.b64encode(init.encode("utf-16-le")).decode()
        cmd = f"powershell.exe -NoLogo -NoExit -ExecutionPolicy Bypass -EncodedCommand {encoded}"
        env = runtime.env()
        env["RCUTILS_COLORIZED_OUTPUT"] = "1"
        self.pty = PtyProcess.spawn(cmd, cwd=str(ws.ws), env=env, dimensions=(rows, cols))
        runtime.job.assign(self.pty.pid)
        threading.Thread(target=self._pump, name="pty-reader", daemon=True).start()

    @property
    def alive(self) -> bool:
        return self.pty.isalive()

    def _pump(self) -> None:
        loop = self.runtime.loop
        while True:
            try:
                data = self.pty.read(4096)
            except EOFError:
                break
            if not data:
                continue
            self.scrollback.append(data)
            self._size += len(data)
            while self._size > SCROLLBACK_BYTES and self.scrollback:
                self._size -= len(self.scrollback.popleft())

            def fan_out(chunk=data) -> None:
                for q in list(self.listeners):
                    q.put_nowait(chunk)
            loop.call_soon_threadsafe(fan_out)
        loop.call_soon_threadsafe(lambda: [q.put_nowait(None) for q in list(self.listeners)])

    def history(self) -> str:
        """Scrollback for a reconnecting browser, minus terminal *queries*. ConPTY asks the terminal for its
        attributes/size at start-up (ESC[c, ESC[6n, ESC[...t); replaying those makes xterm.js answer again,
        and the answer (e.g. ESC[?1;2c) would be typed into the shell as junk."""
        return QUERY_RE.sub("", "".join(self.scrollback))

    def write(self, data: str) -> None:
        if self.alive:
            self.pty.write(data)

    def resize(self, rows: int, cols: int) -> None:
        if self.alive and 2 <= rows <= 500 and 10 <= cols <= 500:
            self.pty.setwinsize(rows, cols)

    def close(self) -> None:
        try:
            self.pty.terminate(force=True)
        except Exception:
            pass
