"""End-to-end acceptance test for Chapter 4 (Gazebo + ros2_control) against a RUNNING academy server.

open ch04_diffbot_gazebo → write ros2_control/controllers/C++ node → build → launch Gazebo headless →
controllers verified active → sim clock + TF + controller states streamed → student's drive_forward moves the
robot ~1 m in the odom frame → sim and drive checkpoints graded with Gazebo ground truth.

Usage:  pixi run python backend/tests/e2e_chapter4.py [http://127.0.0.1:8000]
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx
import websockets

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
LESSON, PKG = "ch04_diffbot_gazebo", "diffbot_sim"
SOL = Path(__file__).resolve().parents[2] / "courses/mastering_ros2/chapter_04/lessons" / LESSON / "solution" / PKG
FILES = ["urdf/diffbot.ros2_control.xacro", "config/controllers.yaml", "src/drive_forward.cpp"]
passed: list[str] = []


def ok(msg: str) -> None:
    passed.append(msg)
    print(f"  PASS  {msg}", flush=True)


class Runtime:
    def __init__(self) -> None:
        self.tf = self.clock = self.controllers = None
        self.ws = None

    async def run(self) -> None:
        async with websockets.connect(BASE.replace("http", "ws") + "/ws/runtime", max_size=None,
                                      additional_headers={"Origin": BASE}) as ws:
            self.ws = ws
            async for raw in ws:
                e = json.loads(raw)
                if e["type"] == "tf":
                    self.tf = e
                elif e["type"] == "sim_clock":
                    self.clock = e
                elif e["type"] == "controllers":
                    self.controllers = e

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


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    async with httpx.AsyncClient(base_url=BASE, timeout=600, headers={"X-Academy-Client": "1"}) as c:
        await c.post(f"/api/workspace/lessons/{LESSON}/open", json={"level": "guided"})
        await c.post(f"/api/workspace/lessons/{LESSON}/reset", json={"level": "guided"})
        lesson = (await c.get(f"/api/courses/lessons/{LESSON}")).json()
        assert "controllers" in lesson["lab_tabs"]
        ok("1. Chapter 4 lesson opened (starter package)")

        for rel in FILES:
            r = await c.put("/api/workspace/file", json={"path": f"{PKG}/{rel}", "content": (SOL / rel).read_text(encoding="utf-8")})
            assert r.status_code == 200, r.text
        b = (await c.post("/api/runtime/build", json={"lesson_id": LESSON})).json()
        assert b["ok"], b["tail"]
        ok(f"2. ros2_control block, controllers.yaml and C++ drive_forward written; built in {b['duration_ms'] / 1000:.1f}s")

        rt = Runtime()
        task = asyncio.create_task(rt.run())
        await rt.wait(lambda: rt.ws is not None, 20, "runtime socket")
        await rt.ws.send(json.dumps({"cmd": "robot_watch", "enable": True}))
        r = await c.post("/api/runtime/run", json={"package": PKG, "launch_file": "sim.launch.xml"})
        assert r.status_code == 200, r.text

        def active():
            states = {x["name"]: x["state"] for m in (rt.controllers or {}).get("managers", []) for x in m["controllers"]}
            return states if states.get("diff_drive_controller") == "active" and states.get("joint_state_broadcaster") == "active" else None
        states = await rt.wait(active, 90, "controllers active in Gazebo")
        ok(f"3. Gazebo (headless) + gz_ros2_control: controllers {states}")
        v = (await c.post(f"/api/progress/lessons/{LESSON}/steps/interfaces/complete", json={})).json()
        assert v["completed"], v
        ok(f"   step verified from live controller states: '{v['reason']}'")

        await rt.wait(lambda: rt.clock and rt.clock.get("rtf"), 30, "sim clock")
        ok(f"4. simulation clock streaming: sim time {rt.clock['sim_time']:.1f} s, real-time factor {rt.clock['rtf']}")
        await rt.wait(lambda: rt.frame("base_footprint") and rt.frame("base_footprint")["parent"] == "odom", 30, "odom→base_footprint TF")
        x0 = rt.frame("base_footprint")["t"][0]

        r = await c.post("/api/runtime/run", json={"package": PKG, "executable": "drive_forward"})
        assert r.status_code == 200, r.text
        await rt.wait(lambda: rt.frame("base_footprint")["t"][0] - x0 > 0.95, 60, "robot to drive ~1 m in odom")
        await asyncio.sleep(3)
        x1 = rt.frame("base_footprint")["t"][0]
        assert 0.95 < x1 - x0 < 1.08, x1 - x0
        ok(f"5. C++ drive_forward drove the simulated robot {x1 - x0:.3f} m (odom→base_footprint from TF) and stopped")
        await c.post("/api/runtime/stop", json={})

        async def grade(cp: str) -> dict:
            sub = (await c.post("/api/assessment/submit", json={"lesson_id": LESSON, "checkpoint_id": cp})).json()
            while sub["status"] in ("queued", "running"):
                await asyncio.sleep(3)
                sub = (await c.get(f"/api/assessment/submissions/{sub['id']}")).json()
            return sub

        for cp in ("sim", "drive"):
            sub = await grade(cp)
            assert sub["status"] == "passed", json.dumps(sub["results"], indent=1)[:3000]
            obs = "; ".join(t["observed"] or "" for t in sub["results"]["tests"] if t.get("observed"))[:220]
            ok(f"6. checkpoint '{cp}' passed {sub['results']['summary']['passed']}/{sub['results']['summary']['total']} ({obs})")
        task.cancel()
    print(f"\nE2E CHAPTER 4 RESULT: {len(passed)} checks passed")


if __name__ == "__main__":
    asyncio.run(main())
