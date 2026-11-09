"""Windows Job Objects: memory/process limits and guaranteed cleanup of whole process trees."""

from __future__ import annotations

import ctypes
import subprocess
from contextlib import contextmanager

import win32api
import win32con
import win32job


class JobObject:
    def __init__(self, memory_mb: int, max_processes: int) -> None:
        self.handle = win32job.CreateJobObject(None, "")
        info = win32job.QueryInformationJobObject(self.handle, win32job.JobObjectExtendedLimitInformation)
        info["BasicLimitInformation"]["LimitFlags"] = (
            win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            | win32job.JOB_OBJECT_LIMIT_JOB_MEMORY
            | win32job.JOB_OBJECT_LIMIT_ACTIVE_PROCESS
        )
        info["BasicLimitInformation"]["ActiveProcessLimit"] = max_processes
        info["JobMemoryLimit"] = memory_mb * 1024 * 1024
        win32job.SetInformationJobObject(self.handle, win32job.JobObjectExtendedLimitInformation, info)

    def assign(self, pid: int) -> bool:
        """Assign a process; children it creates afterwards join the job automatically."""
        try:
            h = win32api.OpenProcess(win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE, False, pid)
        except win32api.error:
            return False  # already exited
        try:
            win32job.AssignProcessToJobObject(self.handle, h)
            return True
        except win32job.error:
            return False
        finally:
            win32api.CloseHandle(h)

    def pids(self) -> list[int]:
        try:
            return list(win32job.QueryInformationJobObject(self.handle, win32job.JobObjectBasicProcessIdList))
        except win32job.error:
            return []

    def terminate_all(self) -> None:
        try:
            win32job.TerminateJobObject(self.handle, 1)
        except win32job.error:
            pass

    def close(self) -> None:
        self.terminate_all()
        try:
            win32api.CloseHandle(self.handle)
        except win32api.error:
            pass


def kill_tree(pid: int) -> None:
    """Kill a process and all its descendants (cmd.exe → ros2 → node → python)."""
    subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True,
                   creationflags=subprocess.CREATE_NO_WINDOW)


class _ReasonContext(ctypes.Structure):
    _fields_ = [("Version", ctypes.c_ulong), ("Flags", ctypes.c_ulong), ("SimpleReasonString", ctypes.c_wchar_p)]


@contextmanager
def keep_awake(reason: str = "ROS 2 Academy: build or grading in progress"):
    """Keep Windows from idle-sleeping (incl. Modern Standby) while a build or grading run is in progress.

    Without this, a laptop left alone during a long run can enter standby mid-test; on resume every timer jumps
    forward at once (observed twice: a ~15 s test reported as 767 s and 1192 s, matching Kernel-Power standby
    events). Uses a handle-based power request, so it is safe to enter and exit on different threads.
    """
    kernel32 = ctypes.windll.kernel32
    kernel32.PowerCreateRequest.restype = ctypes.c_void_p
    kernel32.PowerCreateRequest.argtypes = [ctypes.POINTER(_ReasonContext)]
    kernel32.PowerSetRequest.argtypes = [ctypes.c_void_p, ctypes.c_int]
    kernel32.PowerClearRequest.argtypes = [ctypes.c_void_p, ctypes.c_int]
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    system_required, execution_required = 1, 3
    ctx = _ReasonContext(0, 0x1, reason)  # POWER_REQUEST_CONTEXT_VERSION, POWER_REQUEST_CONTEXT_SIMPLE_STRING
    handle = kernel32.PowerCreateRequest(ctypes.byref(ctx))
    active = [t for t in (system_required, execution_required) if handle and kernel32.PowerSetRequest(handle, t)]
    try:
        yield bool(active)
    finally:
        for t in active:
            kernel32.PowerClearRequest(handle, t)
        if handle:
            kernel32.CloseHandle(handle)
