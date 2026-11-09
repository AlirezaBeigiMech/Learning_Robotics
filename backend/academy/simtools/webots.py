"""`webots` command for launch files and the terminal: the installed Webots, with a clean environment and log.

The academy's environment points QT_PLUGIN_PATH at the conda Qt, which must not leak into Webots' own Qt.
Webots prints a multi-line "old GPU" notice on integrated graphics; it is dropped from the log.

Usage: webots [Webots options...] world.wbt   e.g.  webots --batch --mode=realtime --no-rendering --minimize world.wbt
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

GPU_NOTICE = re.compile(r"System below the minimal requirements|unsupported Intel GPU|NVIDIA or AMD graphics|"
                        r"been deactivated|re-activate some OpenGL features")


def main() -> int:
    home = os.environ.get("WEBOTS_HOME")
    exe = Path(home or "") / "msys64" / "mingw64" / "bin" / "webots.exe"
    if not home or not exe.is_file():
        print("webots: Webots is not installed (or WEBOTS_HOME is wrong). Install Webots R2025a for Windows and "
              "restart the academy.", file=sys.stderr)
        return 127
    args = sys.argv[1:]
    for flag in ("--stdout", "--stderr"):  # controller and Webots messages go to this process' output
        if flag not in args:
            args.insert(0, flag)
    env = {k: v for k, v in os.environ.items() if k not in ("QT_PLUGIN_PATH", "QML2_IMPORT_PATH")}
    proc = subprocess.Popen([str(exe), *args], env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1)
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            if line.strip() and not GPU_NOTICE.search(line) and line.strip(" -") and line != "WARNING:":
                print(line, flush=True)
    finally:
        if proc.poll() is None:
            proc.kill()
    return proc.wait()


if __name__ == "__main__":
    sys.exit(main())
