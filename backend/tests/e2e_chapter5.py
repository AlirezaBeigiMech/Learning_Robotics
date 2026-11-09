"""End-to-end acceptance test for Chapter 5 (CoppeliaSim + Webots) against a RUNNING academy server.

ch05_coppeliasim: write the Lua bridge → build → launch CoppeliaSim headless → its log streams live → step verified
from the live graph → odom TF streamed → checkpoint graded with /ground_truth.
ch05_webots: write the C++ driver and go_to_goal → build against the Webots C API → launch Webots → sim clock and
TF streamed → go_to_goal reaches its goal in Webots, then the SAME binary in CoppeliaSim → checkpoints graded.

Usage:  pixi run python backend/tests/e2e_chapter5.py [http://127.0.0.1:8000]
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
LESSONS = Path(__file__).resolve().parents[2] / "courses/mastering_ros2/chapter_27/lessons"
passed: list[str] = []


def ok(msg: str) -> None:
    passed.append(msg)
    print(f"  PASS  {msg}", flush=True)


class Runtime:
    def __init__(self) -> None:
        self.tf = self.clock = None
        self.lines: list[tuple[float, str]] = []
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
                elif e["type"] == "proc_output":
                    self.lines.append((time.time(), e["line"]))

    def frame(self, child: str) -> dict | None:
        return next((f for f in (self.tf or {}).get("frames", []) if f["child"] == child), None)

    def saw(self, text: str) -> bool:
        return any(text in line for _, line in self.lines)

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
    async with httpx.AsyncClient(base_url=BASE, timeout=900, headers={"X-Academy-Client": "1"}) as c:
        rt = Runtime()
        task = asyncio.create_task(rt.run())
        await rt.wait(lambda: rt.ws is not None, 20, "runtime socket")
        await rt.ws.send(json.dumps({"cmd": "robot_watch", "enable": True}))

        async def write(lesson: str, pkg: str, rels: list[str]) -> None:
            for rel in rels:
                text = (LESSONS / lesson / "solution" / pkg / rel).read_text(encoding="utf-8")
                r = await c.put("/api/workspace/file", json={"path": f"{pkg}/{rel}", "content": text})
                assert r.status_code == 200, r.text

        async def build(lesson: str) -> float:
            b = (await c.post("/api/runtime/build", json={"lesson_id": lesson})).json()
            assert b["ok"], b["tail"]
            return b["duration_ms"] / 1000

        async def grade(lesson: str, cp: str) -> dict:
            sub = (await c.post("/api/assessment/submit", json={"lesson_id": lesson, "checkpoint_id": cp})).json()
            assert "id" in sub, sub
            while sub["status"] in ("queued", "running"):
                await asyncio.sleep(3)
                sub = (await c.get(f"/api/assessment/submissions/{sub['id']}")).json()
            assert sub["status"] == "passed", json.dumps(sub["results"], indent=1)[:3000]
            obs = "; ".join(t["observed"] or "" for t in sub["results"]["tests"] if t.get("observed"))[:240]
            return {"summary": sub["results"]["summary"], "obs": obs}

        async def odom_pose():
            f = rt.frame("base_link")
            return (f["t"][0], f["t"][1]) if f and f["parent"] == "odom" else None

        # ---------------------------------------------------------------- lesson 1: CoppeliaSim
        L1, P1 = "ch05_coppeliasim", "diffbot_coppelia"
        await c.post(f"/api/workspace/lessons/{L1}/open", json={"level": "guided"})
        await c.post(f"/api/workspace/lessons/{L1}/reset", json={"level": "guided"})
        lesson = (await c.get(f"/api/courses/lessons/{L1}")).json()
        assert lesson["requires"] == ["coppeliasim"] and lesson["missing_requirements"] == [], lesson["missing_requirements"]
        ok("1. CoppeliaSim lesson opened; CoppeliaSim detected (no missing requirement)")
        await write(L1, P1, ["coppeliasim/diffbot_bridge.lua"])
        ok(f"2. Lua bridge written; package built in {await build(L1):.1f}s")

        t_run = time.time()
        r = await c.post("/api/runtime/run", json={"package": P1, "launch_file": "sim.launch.xml"})
        assert r.status_code == 200, r.text
        await rt.wait(lambda: rt.saw("diffbot bridge ready"), 60, "bridge log line")
        t_line = next(t for t, line in rt.lines if "diffbot bridge ready" in line)
        ok(f"3. CoppeliaSim log streamed live: 'diffbot bridge ready' {t_line - t_run:.1f}s after Run")

        async def step_done(lesson_id: str, step: str) -> dict:
            for _ in range(40):
                v = (await c.post(f"/api/progress/lessons/{lesson_id}/steps/{step}/complete", json={})).json()
                if v["completed"]:
                    return v
                await asyncio.sleep(1)
            raise AssertionError(f"step {step} not verified: {v}")
        v = await step_done(L1, "command")
        ok(f"4. step 'From /cmd_vel to the wheels' verified from the live graph: '{v['reason']}'")
        await rt.wait(odom_pose, 30, "odom→base_link from the bridge")
        ok(f"5. TF odom→base_link streamed from CoppeliaSim: {rt.frame('base_link')['t']}")
        await c.post("/api/runtime/stop", json={})
        g = await grade(L1, "bridge")
        ok(f"6. checkpoint 'bridge' passed {g['summary']['passed']}/{g['summary']['total']} ({g['obs']})")

        # ---------------------------------------------------------------- lesson 2: Webots + portability
        L2, P2 = "ch05_webots", "diffbot_webots"
        await c.post(f"/api/workspace/lessons/{L2}/open", json={"level": "guided"})
        await c.post(f"/api/workspace/lessons/{L2}/reset", json={"level": "guided"})
        await write(L2, P2, ["src/webots_driver.cpp", "src/go_to_goal.cpp"])
        ok(f"7. C++ webots_driver and go_to_goal written; built against the Webots C API in {await build(L2):.1f}s")

        r = await c.post("/api/runtime/run", json={"package": P2, "launch_file": "sim.launch.xml"})
        assert r.status_code == 200, r.text
        v = await step_done(L2, "command")
        ok(f"8. Webots running; step verified from the live graph: '{v['reason']}'")
        await rt.wait(lambda: rt.clock and rt.clock.get("rtf"), 40, "Webots /clock")
        ok(f"9. Webots simulated time streaming: {rt.clock['sim_time']:.1f} s, real-time factor {rt.clock['rtf']}")

        async def goal_run(sim: str) -> None:
            await rt.wait(odom_pose, 40, f"odom→base_link ({sim})")
            r = await c.post("/api/runtime/run", json={"package": P2, "executable": "go_to_goal"})
            assert r.status_code == 200, r.text
            def at_goal():
                p = rt.frame("base_link")
                return p and math.hypot(p["t"][0] - 1.2, p["t"][1] + 0.6) < 0.07
            await rt.wait(at_goal, 60, f"go_to_goal to reach (1.2, -0.6) in {sim}")
            x, y = rt.frame("base_link")["t"][:2]
            ok(f"   go_to_goal reached ({x:.3f}, {y:.3f}) in the odom frame in {sim}")

        await goal_run("Webots")
        await c.post("/api/runtime/stop", json={})
        await asyncio.sleep(4)
        r = await c.post("/api/runtime/run", json={"package": P1, "launch_file": "sim.launch.xml"})
        assert r.status_code == 200, r.text
        await rt.wait(lambda: (f := rt.frame("base_link")) and abs(f["t"][0]) < 0.01, 60, "a fresh CoppeliaSim robot at the origin")
        await goal_run("CoppeliaSim")
        ok("10. the same go_to_goal binary drove the robot to its goal in both simulators")
        await c.post("/api/runtime/stop", json={})

        for cp in ("driver", "scan", "portable"):
            g = await grade(L2, cp)
            ok(f"11. checkpoint '{cp}' passed {g['summary']['passed']}/{g['summary']['total']} ({g['obs']})")
        task.cancel()
    print(f"\nE2E CHAPTER 5 RESULT: {len(passed)} checks passed")


if __name__ == "__main__":
    asyncio.run(main())
