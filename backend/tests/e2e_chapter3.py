"""End-to-end acceptance test for Chapter 3 (robot modeling) against a RUNNING academy server.

open ch03_pan_tilt (no sign-in) → live xacro preview (incl. unsaved edits and an error) → write the model →
build → ros2 launch → /robot_description observed → sliders publish real /joint_states → TF observed and
checked numerically → steps verified from the live TF tree → model/tf/final checkpoints graded.

Usage:  pixi run python backend/tests/e2e_chapter3.py [http://127.0.0.1:8000]
"""

from __future__ import annotations

import asyncio
import json
import math
import sys
import time
from pathlib import Path

import httpx
import websockets

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
LESSON, PKG = "ch03_pan_tilt", "pan_tilt_description"
MODEL = f"{PKG}/urdf/pan_tilt.urdf"
SOLUTION = (Path(__file__).resolve().parents[2] / "courses/mastering_ros2/chapter_03/lessons/ch03_pan_tilt/solution"
            / PKG / "urdf/pan_tilt.urdf").read_text(encoding="utf-8")
# the student's version: same robot, their own comments
STUDENT = SOLUTION.replace("A two-axis pan-tilt unit", "My pan-tilt (°, é and — must not break launch on Windows)")

passed: list[str] = []


def ok(msg: str) -> None:
    passed.append(msg)
    print(f"  PASS  {msg}", flush=True)


class Runtime:
    def __init__(self) -> None:
        self.graph = self.tf = self.desc = self.joints = None
        self.ws = None
        self.gui = False

    async def run(self, _unused: str = "") -> None:
        async with websockets.connect(BASE.replace("http", "ws") + "/ws/runtime", max_size=None,
                                      additional_headers={"Origin": BASE}) as ws:
            self.ws = ws
            async for raw in ws:
                e = json.loads(raw)
                t = e["type"]
                if t == "graph":
                    self.graph = e
                elif t == "tf":
                    self.tf = e
                elif t == "robot_description":
                    self.desc = e
                elif t == "joint_states":
                    self.joints = e
                elif t == "joint_gui_state":
                    self.gui = e["enabled"]

    def frame(self, child: str) -> dict | None:
        return next((f for f in (self.tf or {}).get("frames", []) if f["child"] == child), None)

    async def wait(self, cond, timeout: float, what: str):
        t0 = time.time()
        while time.time() - t0 < timeout:
            v = cond()
            if v:
                return v
            await asyncio.sleep(0.3)
        raise AssertionError(f"timed out waiting for: {what}")


def yaw_pitch(q: list[float]) -> tuple[float, float]:
    x, y, z, w = q
    yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    pitch = math.asin(max(-1, min(1, 2 * (w * y - z * x))))
    return yaw, pitch


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    async with httpx.AsyncClient(base_url=BASE, timeout=300, headers={"X-Academy-Client": "1"}) as c:
        lesson = (await c.get(f"/api/courses/lessons/{LESSON}")).json()
        assert {"robot", "tf"} <= set(lesson["lab_tabs"])
        await c.post(f"/api/workspace/lessons/{LESSON}/open", json={"level": "guided"})
        await c.post(f"/api/workspace/lessons/{LESSON}/reset", json={"level": "guided"})  # start from the starter
        ok("1. Chapter 3 lesson opened; ament_cmake description package materialised")

        p = (await c.post("/api/robot/preview", json={"path": MODEL})).json()
        assert p["ok"] and p["summary"]["links"] == 1, p
        ok(f"2. preview of the starter via real xacro: {p['summary']['links']} link, {p['summary']['joints']} joint "
           f"(diagnostics: {[d['message'] for d in p['diagnostics']][:1]})")
        p = (await c.post("/api/robot/preview", json={"path": MODEL, "content": STUDENT})).json()
        assert p["ok"] and p["summary"]["links"] == 4 and p["summary"]["movable"] == 2 and not p["diagnostics"], p
        ok("   preview of UNSAVED editor content: 4 links, 2 movable joints, no diagnostics")
        broken = STUDENT.replace("</joint>", "</jiont>", 1)
        p = (await c.post("/api/robot/preview", json={"path": MODEL, "content": broken})).json()
        assert not p["ok"] and p["error"], p
        ok(f"   broken XML reported by xacro: {p['error'].splitlines()[0][:90]}")
        tree = (await c.get("/api/workspace/tree")).json()
        assert not any(".~preview" in e["path"] for e in tree["entries"])
        ok("   preview temp files never appear in the workspace")

        r = await c.put("/api/workspace/file", json={"path": MODEL, "content": STUDENT})
        assert r.status_code == 200, r.text
        b = (await c.post("/api/runtime/build", json={"lesson_id": LESSON})).json()
        assert b["ok"], b["tail"]
        ok(f"3. model written; ament_cmake package built in {b['duration_ms'] / 1000:.1f}s")

        rt = Runtime()
        task = asyncio.create_task(rt.run(""))
        await rt.wait(lambda: rt.ws is not None, 20, "runtime socket")
        await rt.ws.send(json.dumps({"cmd": "robot_watch", "enable": True}))

        status = (await c.get("/api/runtime/status")).json()
        assert "display.launch.xml" in status["executables"][PKG]["launch_files"], status["executables"]
        r = await c.post("/api/runtime/run", json={"package": PKG, "launch_file": "display.launch.xml"})
        assert r.status_code == 200, r.text
        await rt.wait(lambda: rt.desc is not None, 40, "/robot_description from robot_state_publisher")
        assert 'name="tilt_joint"' in rt.desc["urdf"] and "°" in rt.desc["urdf"]
        ok("4. ros2 launch → robot_state_publisher publishes /robot_description (non-ASCII comment survived)")
        await rt.wait(lambda: rt.graph and any(n["name"] == "/robot_state_publisher" for n in rt.graph["nodes"]), 20,
                      "robot_state_publisher in the live graph")
        v = (await c.post(f"/api/progress/lessons/{LESSON}/steps/launch/complete", json={})).json()
        assert v["completed"], v
        ok("   step 'launch' verified from the live ROS graph")

        await rt.wait(lambda: rt.frame("camera_link"), 20, "static camera_link on /tf_static")
        assert rt.frame("camera_link")["static"] and rt.frame("tilt_link") is None
        v = (await c.post(f"/api/progress/lessons/{LESSON}/steps/move_joints/complete", json={})).json()
        assert not v["completed"], v
        ok(f"5. before any /joint_states only fixed frames exist; verification correctly refuses: '{v['reason']}'")

        pan, tilt = 0.7, -0.4
        await rt.ws.send(json.dumps({"cmd": "joint_gui", "enable": True, "positions": {"pan_joint": pan, "tilt_joint": tilt}}))
        await rt.wait(lambda: rt.gui, 15, "joint gui node")
        await rt.wait(lambda: (f := rt.frame("tilt_link")) and abs(yaw_pitch(f["q"])[1] - tilt) < 1e-3, 30, "tilt_link at -0.4 rad in TF")
        pan_f = rt.frame("pan_link")
        assert abs(yaw_pitch(pan_f["q"])[0] - pan) < 1e-3 and pan_f["parent"] == "base_link" and not pan_f["static"]
        await rt.wait(lambda: rt.graph and any(n["name"] == "/academy_joint_gui" for n in rt.graph["nodes"]), 15, "joint gui in graph")
        await rt.wait(lambda: rt.joints and rt.joints["publishers"] == ["/academy_joint_gui"], 15, "joint_states publisher")
        ok(f"6. sliders → /academy_joint_gui → /joint_states → robot_state_publisher → TF: pan yaw {pan}, tilt pitch {tilt} "
           f"(rate {rt.frame('tilt_link')['rate']} Hz)")
        v = (await c.post(f"/api/progress/lessons/{LESSON}/steps/move_joints/complete", json={})).json()
        assert v["completed"], v
        ok("   step 'move_joints' verified from the live TF tree")
        tfapi = (await c.get("/api/runtime/tf")).json()
        assert {f["child"] for f in tfapi["frames"]} >= {"pan_link", "tilt_link", "camera_link"}

        await rt.ws.send(json.dumps({"cmd": "joint_gui", "enable": False}))
        await c.post("/api/runtime/stop", json={})

        async def grade(cp: str) -> dict:
            sub = (await c.post("/api/assessment/submit", json={"lesson_id": LESSON, "checkpoint_id": cp})).json()
            while sub["status"] in ("queued", "running"):
                await asyncio.sleep(2)
                sub = (await c.get(f"/api/assessment/submissions/{sub['id']}")).json()
            return sub

        for cp in ("model", "tf", "final"):
            sub = await grade(cp)
            assert sub["status"] == "passed", json.dumps(sub["results"], indent=1)[:2500]
            s = sub["results"]["summary"]
            ok(f"7. checkpoint '{cp}' passed {s['passed']}/{s['total']}")
        prog = (await c.get(f"/api/progress/lessons/{LESSON}")).json()
        assert prog["status"] == "completed", prog
        ok("8. lesson completed and saved")
        task.cancel()
    print(f"\nE2E CHAPTER 3 RESULT: {len(passed)} checks passed")


if __name__ == "__main__":
    asyncio.run(main())
