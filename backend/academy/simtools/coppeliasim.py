"""`coppeliasim` command for launch files and the terminal: CoppeliaSim with its log streamed line by line.

Three problems this solves on Windows:
  * CoppeliaSim fully buffers its console output when it is piped, so a script error would only appear minutes
    later (or never, if the process is killed). Running it on a pseudo console makes its output line-buffered.
  * The academy's environment points QT_PLUGIN_PATH at the conda Qt; CoppeliaSim's own Qt 5 crashes on it
    (exit 0xC0000409 before printing anything).
  * Every instance would start the ZeroMQ/WebSocket remote-API servers on fixed ports, so a second instance
    (e.g. the grader's) could not start them. ROS 2 lessons do not use them, so they are off unless asked for.

Usage: coppeliasim [CoppeliaSim options...]   e.g.  coppeliasim -h -s0 -amy_addon.lua
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07|\x1b[=>]")
# start-up chatter that is not useful in a lesson (licence ids, add-on list, the Python sandbox probe)
NOISE = re.compile(r":loadinfo\]|add-on '.*' was loaded|^\s*> ?$|pythonLauncher|import zmq|No module named 'zmq'|"
                   r"^Traceback \(most recent call last\):$|Python interpreter could not handle|configured a preferred scripting|"
                   r"crashed in previous session")


def main() -> int:
    root = os.environ.get("COPPELIASIM_ROOT_DIR")
    if not root or not (Path(root) / "coppeliaSim.exe").is_file():
        print("coppeliasim: CoppeliaSim is not installed (or COPPELIASIM_ROOT_DIR is wrong). Install CoppeliaSim Edu "
              "4.10 for Windows and restart the academy.", file=sys.stderr)
        return 127
    args = sys.argv[1:]
    for key, value in (("zmqRemoteApi.autoStart", "false"), ("wsRemoteApi.autoStart", "false"), ("preferredSandboxLang", "lua")):
        if not any(a.startswith(f"-G{key}=") for a in args):
            args.append(f"-G{key}={value}")
    if not any(a.startswith("-v") for a in args):
        args.insert(0, "-vscriptinfos")  # show sim.addLog / print output from scripts
    env = {k: v for k, v in os.environ.items() if k not in ("QT_PLUGIN_PATH", "QML2_IMPORT_PATH")}

    import winpty  # pywinpty: ConPTY

    cmd = subprocess.list2cmdline([str(Path(root) / "coppeliaSim.exe"), *args])
    proc = winpty.PtyProcess.spawn(cmd, cwd=root, env=env, dimensions=(50, 500))
    buf = ""
    try:
        while True:
            try:
                chunk = proc.read(4096)
            except EOFError:
                break
            buf += ANSI.sub("", chunk).replace("\r", "")
            *lines, buf = buf.split("\n")
            for line in lines:
                line = line.removeprefix("> ").rstrip()
                if line.strip() and not NOISE.search(line):
                    print(line, flush=True)
    finally:
        if proc.isalive():
            proc.terminate(force=True)
    return proc.exitstatus or 0


if __name__ == "__main__":
    sys.exit(main())
