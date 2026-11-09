"""End-to-end acceptance test of the first vertical slice against a RUNNING academy server.

Walks the full student workflow for ch02_pubsub with real ROS 2 processes:
open lesson (no sign-in) → starter fails checkpoint → write publisher → build → run → live graph →
verify step → echo topic → write subscriber → run both → introduce QoS fault → observe it live →
repair → integration checkpoint → final submission with hidden tests → progress saved.
Also exercises the PTY terminal and the editor diagnostics.

Usage:  pixi run python backend/tests/e2e_workflow.py [http://127.0.0.1:8000]
"""

from __future__ import annotations

import asyncio
import json
import sys
import time

import httpx
import websockets

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
LESSON = "ch02_pubsub"
PKG = "topics_lab"

# Student-authored C++ (deliberately different from the reference solution).
PUBLISHER = """#include <chrono>
#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/int32.hpp"

using namespace std::chrono_literals;

class NumberPublisher : public rclcpp::Node
{
public:
  NumberPublisher() : Node("number_publisher")
  {
    pub_ = create_publisher<std_msgs::msg::Int32>("numbers", 10);
    timer_ = create_wall_timer(100ms, [this]() {
      std_msgs::msg::Int32 m;
      m.data = n_++;
      pub_->publish(m);
      RCLCPP_INFO(get_logger(), "sent %d", m.data);
    });
  }

private:
  rclcpp::Publisher<std_msgs::msg::Int32>::SharedPtr pub_;
  rclcpp::TimerBase::SharedPtr timer_;
  int n_ = 0;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<NumberPublisher>());
  rclcpp::shutdown();
  return 0;
}
"""
BROKEN_PUBLISHER = PUBLISHER.replace('create_publisher<std_msgs::msg::Int32>("numbers", 10)',
                                     'create_publisher<std_msgs::msg::Int32>("numbers", rclcpp::QoS(10).best_effort())')
NOT_COMPILING = PUBLISHER.replace("m.data = n_++;", "m.dataa = n_++;")
ERROR_LINE = next(i for i, l in enumerate(NOT_COMPILING.splitlines(), 1) if "m.dataa" in l)
SUBSCRIBER = """#include <memory>
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/int32.hpp"

class NumberSubscriber : public rclcpp::Node
{
public:
  NumberSubscriber() : Node("number_subscriber")
  {
    sub_ = create_subscription<std_msgs::msg::Int32>(
      "numbers", 10, [this](const std_msgs::msg::Int32 & msg) {
        RCLCPP_INFO(get_logger(), "Received: %d", msg.data);
      });
  }

private:
  rclcpp::Subscription<std_msgs::msg::Int32>::SharedPtr sub_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<NumberSubscriber>());
  rclcpp::shutdown();
  return 0;
}
"""
PUB_FILE = f"{PKG}/src/number_publisher.cpp"
SUB_FILE = f"{PKG}/src/number_subscriber.cpp"

passed: list[str] = []


def ok(msg: str) -> None:
    passed.append(msg)
    print(f"  PASS  {msg}", flush=True)


class Runtime:
    """Collects events from /ws/runtime in the background."""

    def __init__(self) -> None:
        self.graph: dict | None = None
        self.echo: list[dict] = []
        self.output: dict[int, list[str]] = {}
        self.ws = None
        self.error = None
        self.events = 0

    async def run(self, _unused: str = "") -> None:
        url = BASE.replace("http", "ws") + "/ws/runtime"
        try:
            await self._run(url)
        except Exception as e:  # surface client-side failures instead of silently timing out
            self.error = repr(e)
            print("  runtime socket error:", self.error, flush=True)

    async def _run(self, url: str) -> None:
        async with websockets.connect(url, additional_headers={"Origin": BASE}, max_size=None) as ws:
            self.ws = ws
            async for raw in ws:
                e = json.loads(raw)
                self.events += 1
                if e["type"] == "graph":
                    self.graph = e
                elif e["type"] == "echo":
                    self.echo.append(e)
                elif e["type"] == "proc_output":
                    self.output.setdefault(e["id"], []).append(e["line"])

    def topic(self, name: str) -> dict | None:
        return next((t for t in (self.graph or {}).get("topics", []) if t["name"] == name), None)

    async def wait(self, cond, timeout: float, what: str):
        t0 = time.time()
        while time.time() - t0 < timeout:
            v = cond()
            if v:
                return v
            await asyncio.sleep(0.3)
        raise AssertionError(f"timed out waiting for: {what} (socket events={self.events}, error={self.error}, "
                             f"last graph age={time.time() - (self.graph or {}).get('t', 0):.0f}s)")


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE, timeout=300, headers={"X-Academy-Client": "1"}) as c:
        me = (await c.get("/api/me")).json()
        ok(f"1. no sign-in: the academy opens as the local student '{me['display_name']}'")

        # the guards that replace sign-in (this server runs code, so other websites must not reach it)
        async with httpx.AsyncClient(base_url=BASE, timeout=30) as raw:
            assert (await raw.get("/api/me")).status_code == 403, "API call without the client header must be refused"
            assert (await raw.post("/api/runtime/build", json={}, headers={"X-Academy-Client": "1", "Origin": "https://evil.example"})).status_code == 403
            assert (await raw.get("/api/me", headers={"X-Academy-Client": "1", "Host": "attacker.example:8000"})).status_code == 403
        ok("   cross-site requests, header-less API calls and DNS-rebinding Host headers are refused (403)")

        # single local student: start this run from the starter files (the current package is backed up)
        await c.post(f"/api/workspace/lessons/{LESSON}/reset", json={"level": "guided"})

        lesson = (await c.get(f"/api/courses/lessons/{LESSON}")).json()
        assert len(lesson["steps"]) == 10 and ".py" not in json.dumps(lesson["checkpoints"]) and "def test_" not in json.dumps(lesson)
        r = (await c.post(f"/api/workspace/lessons/{LESSON}/open", json={"level": "guided"})).json()
        assert r["package"] == PKG
        tree = (await c.get("/api/workspace/tree")).json()
        assert PUB_FILE in {e["path"] for e in tree["entries"]}
        ok(f"2. lesson opened; starter package materialised (ROS_DOMAIN_ID={tree['domain_id']}); hidden tests not exposed")

        # security: path traversal is rejected
        assert (await c.get("/api/workspace/file", params={"path": "../../secret.key"})).status_code == 400
        assert (await c.get("/api/workspace/file", params={"path": "C:/Windows/win.ini"})).status_code == 400
        ok("   workspace path traversal rejected")

        # diagnostics: Python syntax error and the invalid-email package.xml pitfall
        bad_xml = (await c.get("/api/workspace/file", params={"path": f"{PKG}/package.xml"})).json()["content"].replace("student@example.com", "a@b.c")
        d = (await c.post("/api/workspace/diagnostics", json={"path": f"{PKG}/package.xml", "content": bad_xml})).json()["diagnostics"]
        assert d and "email" in d[0]["message"].lower()
        ok("   editor diagnostics: invalid package.xml detected while typing")

        rt = Runtime()
        ws_task = asyncio.create_task(rt.run(""))
        await rt.wait(lambda: rt.graph is not None, 60, "first live graph snapshot")
        ok("   runtime WebSocket connected; telemetry agent streaming graph snapshots")

        async def grade(cp: str) -> dict:
            sub = (await c.post("/api/assessment/submit", json={"lesson_id": LESSON, "checkpoint_id": cp})).json()
            while sub["status"] in ("queued", "running"):
                await asyncio.sleep(2)
                sub = (await c.get(f"/api/assessment/submissions/{sub['id']}")).json()
            return sub

        async def build() -> dict:
            r = (await c.post("/api/runtime/build", json={"lesson_id": LESSON})).json()
            assert r["ok"], r["tail"]
            return r

        async def save(path: str, content: str) -> None:
            r = await c.put("/api/workspace/file", json={"path": path, "content": content})
            assert r.status_code == 200 and not r.json()["diagnostics"], r.text

        async def run(exe: str) -> int:
            r = await c.post("/api/runtime/run", json={"package": PKG, "executable": exe})
            assert r.status_code == 200, r.text
            return r.json()["id"]

        sub = await grade("publisher")
        assert sub["status"] == "failed", sub
        ok(f"   starter code fails the publisher checkpoint ({sub['results']['summary']['passed']}/{sub['results']['summary']['total']})")

        await save(PUB_FILE, NOT_COMPILING)
        r = (await c.post("/api/runtime/build", json={"lesson_id": LESSON})).json()
        diag = next((d for d in r.get("diagnostics", []) if d["severity"] == "error"), None)
        assert not r["ok"] and diag and diag["path"] == PUB_FILE and diag["line"] == ERROR_LINE, (r.get("diagnostics"), r["tail"][-800:])
        ok(f"3. C++ compile error reported as an editor marker: {diag['path']}:{diag['line']} {diag['message'][:70]}")

        await save(PUB_FILE, PUBLISHER)
        b = await build()
        ok(f"4. C++ publisher written; colcon (Ninja + MSVC) build succeeded in {b['duration_ms'] / 1000:.1f}s")

        pub_id = await run("number_publisher")
        await rt.wait(lambda: (t := rt.topic("/numbers")) and any(p["node"] == "/number_publisher" for p in t["publishers"]), 40,
                      "/number_publisher on /numbers in live graph")
        ok("5. publisher running; appears in the live ROS graph publishing /numbers")
        v = (await c.post(f"/api/progress/lessons/{LESSON}/steps/run_publisher/complete", json={})).json()
        assert v["completed"], v
        ok("   step 'run_publisher' verified server-side from the live graph")

        await rt.ws.send(json.dumps({"cmd": "echo", "topic": "/numbers"}))
        await rt.wait(lambda: len(rt.echo) >= 15, 30, "echoed /numbers messages")
        await asyncio.sleep(2)
        rate = rt.echo[-1]["rate"]
        vals = [e["data"]["data"] for e in rt.echo[-5:]]
        assert 7 <= rate <= 14 and vals == sorted(vals), (rate, vals)
        ok(f"6. topic inspector: real messages {vals}, measured {rate:.1f} Hz")

        sub = await grade("publisher")
        assert sub["status"] == "passed", sub["results"]
        ok(f"   publisher checkpoint passed ({sub['results']['summary']['passed']}/{sub['results']['summary']['total']})")

        await save(SUB_FILE, SUBSCRIBER)
        await build()  # stops the running publisher first (Windows file locks)
        ok("7. subscriber written; rebuild stopped running nodes and succeeded")
        await run("number_publisher")
        sub_id = await run("number_subscriber")
        await rt.wait(lambda: any("Received:" in l for l in rt.output.get(sub_id, [])), 40, "subscriber receiving")
        await rt.wait(lambda: (t := rt.topic("/numbers")) and t["subscribers"] and t["publishers"]
                      and all(q["compatible"] == "ok" for q in t["qos_pairs"]), 30, "compatible pub/sub pair in graph")
        v = (await c.post(f"/api/progress/lessons/{LESSON}/steps/run_both/complete", json={})).json()
        assert v["completed"], v
        ok("8+9. both nodes running; subscriber logs 'Received: n'; live graph shows a compatible edge")

        await save(PUB_FILE, BROKEN_PUBLISHER)
        await build()
        await run("number_publisher")
        sub_id = await run("number_subscriber")
        t = await rt.wait(lambda: (t := rt.topic("/numbers")) and any(q["compatible"] == "error" for q in t["qos_pairs"]) and t,
                          40, "QoS incompatibility visible in live graph")
        reason = next(q["reason"] for q in t["qos_pairs"] if q["compatible"] == "error")
        await asyncio.sleep(3)
        received = [l for l in rt.output.get(sub_id, []) if "Received:" in l]
        warned = [l for l in rt.output.get(sub_id, []) if "incompatible" in l.lower()]
        assert not received, received[:3]
        v = (await c.post(f"/api/progress/lessons/{LESSON}/steps/break_qos/complete", json={})).json()
        assert v["completed"], v
        ok(f"10. fault injected: subscriber silent; graph reports '{reason}'; "
           f"{'node logged QoS warning' if warned else 'no QoS warning line in node log'}")

        sub = await grade("integration")
        assert sub["status"] == "failed"
        ok(f"11. integration checkpoint correctly FAILS with the fault: "
           + "; ".join(f"{x['id']}={x['status']}" for x in sub["results"]["tests"]))

        await save(PUB_FILE, PUBLISHER)
        await build()
        sub = await grade("integration")
        assert sub["status"] == "passed", sub["results"]
        ok("    repaired: integration checkpoint passes")

        sub = await grade("final")
        assert sub["status"] == "passed", json.dumps(sub["results"], indent=1)[:3000]
        hidden = [x for x in sub["results"]["tests"] if x["hidden"]]
        ok(f"12+13. final submission passed {sub['results']['summary']['passed']}/{sub['results']['summary']['total']} "
           f"(incl. {len(hidden)} hidden tests)")

        prog = (await c.get(f"/api/progress/lessons/{LESSON}")).json()
        overview = (await c.get("/api/progress")).json()
        assert prog["status"] == "completed" and {"write_publisher", "repair", "submit"} <= set(prog["steps_completed"])
        assert overview["portfolio"] and overview["skills"] and overview["stats"]["build_attempts"] >= 4
        ok(f"14. progress saved: lesson completed, {len(overview['skills'])} skills, "
           f"{overview['stats']['build_attempts']} builds, portfolio entry")

        # terminal: a real PowerShell with the student's ROS environment
        url = BASE.replace("http", "ws") + "/ws/terminal"
        async with websockets.connect(url, additional_headers={"Origin": BASE}) as term:
            # PowerShell concatenates 'END' + 'MARK', so "ENDMARK" only appears after the command has run.
            await term.send(json.dumps({"type": "input", "data": "$env:ROS_DOMAIN_ID; ros2 pkg prefix topics_lab; 'END' + 'MARK'\r"}))
            buf, t0 = "", time.time()
            while time.time() - t0 < 60 and "ENDMARK" not in buf:
                try:
                    buf += await asyncio.wait_for(term.recv(), 5)
                except asyncio.TimeoutError:
                    pass
            assert str(tree["domain_id"]) in buf and "ws\\install" in buf, buf[-800:]
            assert "not found" not in buf, "terminal start-up printed an error: " + buf[-800:]
        ok("    PTY terminal: PowerShell sees the student's domain and overlay (ros2 pkg prefix topics_lab)")

        # cross-site WebSocket is refused
        try:
            async with websockets.connect(url, additional_headers={"Origin": "http://evil.example"}) as w:
                await w.recv()
            raise AssertionError("cross-origin websocket accepted")
        except (websockets.exceptions.ConnectionClosed, websockets.exceptions.InvalidStatus):
            pass  # refused at handshake (HTTP 403) or closed immediately
        ok("    cross-origin WebSocket rejected")

        await c.post("/api/runtime/stop", json={})
        ws_task.cancel()
    print(f"\nE2E RESULT: {len(passed)} checks passed")


if __name__ == "__main__":
    asyncio.run(main())
