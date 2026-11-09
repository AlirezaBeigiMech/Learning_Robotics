"""Per-student ROS 2 runtime: builds, node processes, the PTY terminal and the telemetry agent, all inside
one Windows Job Object and one DDS domain."""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from ..config import settings
from ..workspace.manager import StudentWorkspace, diagnose
from .process import ManagedProcess, cmd_line
from .winjob import JobObject, keep_awake

FASTDDS_PROFILE = Path(__file__).with_name("fastdds_academy.xml")
COLCON_DEFAULTS = Path(__file__).with_name("colcon_defaults.yaml")
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
LAUNCH_RE = re.compile(r"^[A-Za-z0-9_.\-]+\.(py|xml|yaml)$")
ARG_RE = re.compile(r"^[A-Za-z0-9_:=./\-]+$")
# Environment variables from the platform's own shell that must never leak into a student's run.
_STRIP_ENV = {"ROS_DOMAIN_ID", "COLCON_DEFAULTS_FILE", "GZ_PARTITION", "GZ_IP", "GZ_RELAY", "FASTDDS_DEFAULT_PROFILES_FILE", "RMW_FASTRTPS_USE_QOS_FROM_XML", "ROS_LOCALHOST_ONLY", "ROS_AUTOMATIC_DISCOVERY_RANGE", "ROS_STATIC_PEERS",
              "AMENT_PREFIX_PATH_OVERLAY"}


# MSVC:  C:\...\src\pub.cpp(12,5): error C2065: 'x': undeclared identifier
# GCC/Clang style:  /path/file.cpp:12:5: error: message
_MSVC_DIAG = re.compile(r"^(?P<file>[A-Za-z]:[^()<>|*?\"]+?)\((?P<line>\d+)(?:,(?P<col>\d+))?\)\s*:\s*"
                        r"(?P<sev>fatal error|error|warning)\s+(?P<code>[A-Z]+\d+)\s*:\s*(?P<msg>.*)$")
_GNU_DIAG = re.compile(r"^(?P<file>(?:[A-Za-z]:)?[^:]+?):(?P<line>\d+):(?:(?P<col>\d+):)?\s*(?P<sev>fatal error|error|warning):\s*(?P<msg>.*)$")
_CMAKE_DIAG = re.compile(r"^CMake (?P<sev>Error|Warning)(?: \(dev\))? at (?P<file>.+?):(?P<line>\d+)")


def compiler_diagnostics(lines: list[str], src: Path) -> list[dict]:
    """Turn compiler/CMake messages about the student's own files into editor markers (paths relative to src)."""
    src_root = src.resolve()
    out, seen = [], set()
    for line in lines:
        text = line.strip()
        m = _MSVC_DIAG.match(text) or _GNU_DIAG.match(text) or _CMAKE_DIAG.match(text)
        if not m:
            continue
        f = Path(m.group("file").strip())
        candidates = [f] if f.is_absolute() else [pkg / f for pkg in src_root.glob("*")]  # CMake: package-relative
        rel = None
        for cand in candidates:
            try:
                resolved = cand.resolve()
                if resolved.is_file():
                    rel = resolved.relative_to(src_root).as_posix()
                    break
            except (ValueError, OSError):
                continue
        if rel is None:
            continue  # message about a file outside the student's sources (e.g. ROS headers)
        g = m.groupdict()
        msg = re.sub(r"\s*\[[A-Za-z]:\\[^\]]*\]$", "", (g.get("msg") or text).strip())  # drop trailing [C:\...project]
        key = (rel, m.group("line"), msg)
        if key in seen:
            continue
        seen.add(key)
        out.append({"path": rel, "line": int(m.group("line")), "column": int(g.get("col") or 1),
                    "severity": "warning" if m.group("sev").lower() == "warning" else "error",
                    "message": f"{g['code']}: {msg}" if g.get("code") else msg, "source": "compiler"})
    return out[:200]


def clear_foreign_cmake_builds(build_dir: Path) -> None:
    """CMake refuses to switch generators inside an existing build folder; drop folders made by another one."""
    for cache in build_dir.glob("*/CMakeCache.txt"):
        try:
            text = cache.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        gen = re.search(r"^CMAKE_GENERATOR:INTERNAL=(.*)$", text, re.M)
        if gen and gen.group(1).strip() != "Ninja":
            shutil.rmtree(cache.parent, ignore_errors=True)


class RuntimeErrorForUser(Exception):
    pass


def ros_env(domain_id: int, log_dir: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in _STRIP_ENV}
    env.update({
        "ROS_DOMAIN_ID": str(domain_id),
        "ROS_AUTOMATIC_DISCOVERY_RANGE": "LOCALHOST",
        "ROS_LOG_DIR": str(log_dir),
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8",
        # UTF-8 mode: otherwise Python on Windows decodes subprocess output (e.g. xacro's URDF inside
        # `ros2 launch`) with the ANSI codepage, and one non-ASCII character in a comment crashes the launch.
        "PYTHONUTF8": "1",
        # C++ builds: Ninja + MSVC. The default "Visual Studio 16 2019" generator fails in ROS workspaces because
        # MSBuild's FileTracker cannot create files beyond MAX_PATH (260 chars) in colcon's nested build trees.
        # Set for every process, so a `colcon build` typed in the terminal behaves exactly like the Build button.
        "CMAKE_GENERATOR": "Ninja",
        "COLCON_DEFAULTS_FILE": str(COLCON_DEFAULTS),
        "CMAKE_BUILD_TYPE": "Release",
        "RCUTILS_COLORIZED_OUTPUT": "0",
        "RMW_IMPLEMENTATION": "rmw_fastrtps_cpp",
        "FASTRTPS_DEFAULT_PROFILES_FILE": str(FASTDDS_PROFILE),
    })
    # Gazebo (Chapter 4+). gz-transport discovers peers by multicast on the LAN, so like DDS it is pinned to
    # localhost and given a private partition per domain. RoboStack installs gz_ros2_control-system.dll in
    # Library\bin while gz-sim searches Library\lib only, so ros2_control would silently never start.
    prefix = Path(sys.prefix) / "Library"
    env.update({
        "GZ_IP": "127.0.0.1",
        "GZ_PARTITION": f"academy_{domain_id}",
        "GZ_SIM_SYSTEM_PLUGIN_PATH": os.pathsep.join([str(prefix / "lib"), str(prefix / "bin")]),
    })
    # Webots and CoppeliaSim (Chapter 5). Launch files call the academy's `webots` / `coppeliasim` commands
    # (simtools/bin), which find the install, fix its environment and stream its log. Each domain gets its own
    # Webots port, so a student's simulation and a grader run never connect to each other's robots.
    env["PATH"] = str(settings.simtools_dir / "bin") + os.pathsep + env.get("PATH", "")
    env["ACADEMY_PYTHON"] = sys.executable
    env["ACADEMY_SIM_PORT"] = str(20000 + domain_id)
    if settings.webots_home:
        env["WEBOTS_HOME"] = str(settings.webots_home)
        # Controller.dll: the Webots C API that a C++ driver node links against (appended: generic DLL names)
        env["PATH"] += os.pathsep + str(settings.webots_home / "lib" / "controller")
    if settings.coppeliasim_root:
        env["COPPELIASIM_ROOT_DIR"] = str(settings.coppeliasim_root)
    env.update(extra or {})
    return env


def tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeErrorForUser(f"'{name}' was not found. Start the academy with `pixi run start`.")
    return path


class StudentRuntime:
    def __init__(self, ws: StudentWorkspace, loop: asyncio.AbstractEventLoop) -> None:
        self.ws = ws
        self.loop = loop
        self.job = JobObject(settings.job_memory_mb, settings.job_max_processes)
        self.procs: dict[int, ManagedProcess] = {}
        self.subscribers: set[asyncio.Queue] = set()
        self.agent: ManagedProcess | None = None
        self.last_graph: dict | None = None
        self.build_lock = asyncio.Lock()
        self.terminal = None  # academy.runtime.terminal.Terminal
        self.last_build: dict | None = None
        self.last_tf: dict | None = None
        self.last_robot_description: dict | None = None
        self.last_controllers: dict | None = None
        # agent subscriptions requested by clients, replayed whenever the agent restarts
        self.echo_topics: set[str] = set()
        self.robot_watch = False
        self.joint_gui: dict[str, float] | None = None

    # ---------------------------------------------------------------- events
    def env(self) -> dict[str, str]:
        return ros_env(self.ws.domain_id, self.ws.log_dir)

    def broadcast(self, event: dict[str, Any]) -> None:
        """Thread-safe fan-out to every connected /ws/runtime client."""
        def fan_out() -> None:
            for q in list(self.subscribers):
                if q.qsize() < 2000:
                    q.put_nowait(event)
        self.loop.call_soon_threadsafe(fan_out)

    def _on_line(self, p: ManagedProcess, line: str) -> None:
        self.broadcast({"type": "proc_output", "id": p.id, "kind": p.kind, "line": line})

    def _on_exit(self, p: ManagedProcess) -> None:
        self.broadcast({"type": "proc_state", "process": p.info()})

    # ---------------------------------------------------------------- telemetry agent
    def ensure_agent(self) -> None:
        if self.agent and self.agent.running:
            return
        setup = self.ws.install / "setup.bat"
        python = sys.executable
        # With an overlay, the agent can also decode the student's custom message types.
        command: str | list[str] = (cmd_line(f'call "{setup}" && "{python}" "{settings.agent_script}"')
                                    if setup.is_file() else [python, str(settings.agent_script)])
        self.agent = ManagedProcess(
            kind="agent", label="telemetry agent", command=command, cwd=str(self.ws.ws), env=self.env(),
            on_line=self._on_agent_line, on_exit=lambda p: None, job=self.job, stdin_pipe=True,
        ).start()
        # A new agent (e.g. after a rebuild) starts with no subscriptions: replay what clients asked for.
        for topic in self.echo_topics:
            self.agent.write_line(json.dumps({"cmd": "echo", "topic": topic}))
        if self.robot_watch:
            self.agent.write_line(json.dumps({"cmd": "robot_watch", "enable": True}))
        if self.joint_gui is not None:
            self.agent.write_line(json.dumps({"cmd": "joint_gui", "enable": True, "positions": self.joint_gui}))

    def _on_agent_line(self, _: ManagedProcess, line: str) -> None:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return  # rcl log noise on stderr
        kind = event.get("type")
        if kind == "graph":
            self.last_graph = event
        elif kind == "tf":
            self.last_tf = event
        elif kind == "robot_description":
            self.last_robot_description = event
        elif kind == "controllers":
            self.last_controllers = event
        self.broadcast(event)

    def agent_command(self, cmd: dict) -> None:
        c = cmd.get("cmd")
        if c == "echo":
            self.echo_topics.add(cmd["topic"])
        elif c == "stop_echo":
            self.echo_topics.discard(cmd["topic"])
        elif c == "robot_watch":
            self.robot_watch = bool(cmd.get("enable"))
            if self.robot_watch and self.last_robot_description:
                self.broadcast(self.last_robot_description)
        elif c == "joint_gui":
            self.joint_gui = dict(cmd.get("positions") or {}) if cmd.get("enable") else None
        self.ensure_agent()
        assert self.agent is not None
        self.agent.write_line(json.dumps(cmd))

    def restart_agent(self) -> None:
        if self.agent:
            self.agent.stop()
        self.agent = None
        self.ensure_agent()

    # ---------------------------------------------------------------- build
    def _validate_packages(self) -> list[str]:
        problems = []
        for pkg_xml in sorted(self.ws.src.glob("*/package.xml")):
            for d in diagnose("package.xml", pkg_xml.read_text(encoding="utf-8", errors="replace")):
                if d["severity"] == "error":
                    problems.append(f"{pkg_xml.parent.name}/package.xml: {d['message']}")
        return problems

    async def build(self, packages: list[str] | None = None) -> dict:
        if packages and not all(NAME_RE.match(p) for p in packages):
            raise RuntimeErrorForUser("Invalid package name")
        if self.build_lock.locked():
            raise RuntimeErrorForUser("A build is already running")
        async with self.build_lock:
            running = [p for p in self.procs.values() if p.running and p.kind == "run"]
            if running:
                # Windows locks running executables in install/, so a rebuild would fail with "Permission denied".
                self.broadcast({"type": "build_notice", "line": f"Stopping {len(running)} running node(s): Windows locks executables that are in use."})
                await asyncio.gather(*(asyncio.to_thread(p.stop) for p in running))
            clear_foreign_cmake_builds(self.ws.ws / "build")
            problems = self._validate_packages()
            for msg in problems:
                self.broadcast({"type": "build_notice", "line": f"ERROR {msg}"})
            if problems:
                result = {"ok": False, "exit_code": None, "duration_ms": 0, "errors": problems,
                          "tail": "\n".join(problems)}
                self.last_build = result
                return result
            cmd = [tool("colcon"), "build", "--merge-install", "--event-handlers", "console_direct+",
                   "desktop_notification-", "status-", "--base-paths", "src"]
            if packages:
                cmd += ["--packages-select", *packages]
            done: asyncio.Future = self.loop.create_future()
            t0 = time.time()

            def on_exit(p: ManagedProcess) -> None:
                self._on_exit(p)
                self.loop.call_soon_threadsafe(lambda: done.done() or done.set_result(p.exit_code))

            proc = ManagedProcess(kind="build", label="colcon build", command=cmd, cwd=str(self.ws.ws),
                                  env=self.env(), on_line=self._on_line, on_exit=on_exit, job=self.job)
            self.procs[proc.id] = proc
            proc.start()
            self.broadcast({"type": "proc_state", "process": proc.info()})
            with keep_awake():  # a laptop dozing off mid-build would otherwise produce spurious time-outs
                try:
                    code = await asyncio.wait_for(done, timeout=settings.build_timeout_s)
                except asyncio.TimeoutError:
                    await asyncio.to_thread(proc.stop)
                    code = -1
            result = {"ok": code == 0, "exit_code": code, "duration_ms": int((time.time() - t0) * 1000),
                      "tail": "\n".join(list(proc.tail)[-80:]), "process_id": proc.id,
                      "diagnostics": compiler_diagnostics(list(proc.tail), self.ws.src)}
            self.last_build = result
            self.restart_agent()  # pick up new message types from the overlay
            return result

    # ---------------------------------------------------------------- run / stop
    def executables(self) -> dict[str, dict[str, list[str]]]:
        out: dict[str, dict[str, list[str]]] = {}
        for pkg in self.ws.packages():
            exes = sorted(p.stem for p in (self.ws.install / "Lib" / pkg).glob("*.exe")) if (self.ws.install / "Lib" / pkg).is_dir() else []
            launch_dir = self.ws.install / "share" / pkg / "launch"
            launches = sorted(p.name for p in launch_dir.glob("*") if LAUNCH_RE.match(p.name)) if launch_dir.is_dir() else []
            out[pkg] = {"executables": exes, "launch_files": launches}
        return out

    def run(self, package: str, executable: str | None = None, launch_file: str | None = None,
            args: list[str] | None = None) -> ManagedProcess:
        if not NAME_RE.match(package):
            raise RuntimeErrorForUser("Invalid package name")
        if not (self.ws.install / "setup.bat").is_file():
            raise RuntimeErrorForUser("Build the workspace first (no install/setup.bat yet).")
        if sum(1 for p in self.procs.values() if p.running and p.kind == "run") >= settings.max_running_nodes:
            raise RuntimeErrorForUser(f"At most {settings.max_running_nodes} processes may run at once. Stop one first.")
        args = args or []
        if not all(ARG_RE.match(a) for a in args):
            raise RuntimeErrorForUser("Arguments may only contain letters, digits and _:=./-")
        if launch_file:
            if not LAUNCH_RE.match(launch_file):
                raise RuntimeErrorForUser("Invalid launch file name")
            ros_cmd, label = f"ros2 launch {package} {launch_file}", f"{package}/{launch_file}"
        else:
            if not executable or not NAME_RE.match(executable):
                raise RuntimeErrorForUser("Invalid executable name")
            ros_cmd, label = f"ros2 run {package} {executable}", f"{package}/{executable}"
        if args:
            ros_cmd += " " + " ".join(args)
        command = cmd_line(f'call "{self.ws.install / "setup.bat"}" && {ros_cmd}')
        proc = ManagedProcess(kind="run", label=label, command=command, cwd=str(self.ws.ws), env=self.env(),
                              on_line=self._on_line, on_exit=self._on_exit, job=self.job)
        self.procs[proc.id] = proc
        proc.start()
        self.broadcast({"type": "proc_state", "process": proc.info()})
        self.ensure_agent()
        self._prune()
        return proc

    def stop(self, proc_id: int) -> None:
        p = self.procs.get(proc_id)
        if p is None:
            raise RuntimeErrorForUser("Unknown process")
        p.stop()

    def stop_all(self) -> None:
        for p in list(self.procs.values()):
            if p.running and p.kind == "run":
                p.stop()

    async def restart(self) -> None:
        await asyncio.to_thread(self.stop_all)
        if self.terminal:
            self.terminal.close()
            self.terminal = None
        if self.agent:
            await asyncio.to_thread(self.agent.stop)
            self.agent = None
        self.last_graph = self.last_tf = self.last_robot_description = self.last_controllers = None
        self.joint_gui = None
        self.ensure_agent()

    def _prune(self) -> None:
        finished = [p for p in self.procs.values() if not p.running]
        for p in finished[:-20]:
            self.procs.pop(p.id, None)

    def status(self) -> dict:
        return {
            "domain_id": self.ws.domain_id,
            "built": (self.ws.install / "setup.bat").is_file(),
            "processes": [p.info() for p in self.procs.values()],
            "executables": self.executables(),
            "agent_running": bool(self.agent and self.agent.running),
            "last_build": self.last_build,
        }

    def shutdown(self) -> None:
        for p in list(self.procs.values()):
            p.stop(timeout=2)
        if self.agent:
            self.agent.stop(timeout=2)
        if self.terminal:
            self.terminal.close()
        self.job.close()


_runtimes: dict[int, StudentRuntime] = {}


def get_runtime(ws: StudentWorkspace) -> StudentRuntime:
    rt = _runtimes.get(ws.user_id)
    if rt is None:
        rt = StudentRuntime(ws, asyncio.get_running_loop())
        _runtimes[ws.user_id] = rt
    return rt


def peek_runtime(user_id: int) -> StudentRuntime | None:
    return _runtimes.get(user_id)


def shutdown_all() -> None:
    for rt in list(_runtimes.values()):
        rt.shutdown()
    _runtimes.clear()
