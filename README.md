# Mastering ROS 2 Academy

An interactive ROS 2 Jazzy robotics programming laboratory that runs **natively on Windows**. It follows
the project progression of *Mastering ROS for Robotics Programming* (3rd ed., Joseph & Cacace, Packt
2021), re-engineered for ROS 2. Students write, build, run, debug and test **real** ROS 2 code. Every
terminal line, graph edge, message rate and test result comes from real processes on the machine.

## Quick start (Windows 10/11)

Prerequisites:

1. **pixi**: `winget install prefix-dev.pixi` (or see https://pixi.sh)
2. **Visual Studio 2019** with the *Desktop development with C++* workload. **Required**: all lessons are
   C++ (rclcpp), compiled with MSVC through the Ninja generator.
3. ~3 GB of free disk space for the ROS 2 environment.
4. **Chapter 5 only**: two desktop simulators, installed per user (no admin rights), ~2 GB:
   * **Webots R2025a**: `webots-R2025a_setup.exe` from https://github.com/cyberbotics/webots/releases/tag/R2025a,
     install "for me only" (default folder `%LOCALAPPDATA%\Programs\Webots`);
   * **CoppeliaSim Edu 4.10**: `CoppeliaSim_Edu_V4_10_0_rev0_Win.zip` from https://www.coppeliarobotics.com/,
     unzipped into `%LOCALAPPDATA%\Programs\CoppeliaSim` (the zip has no top-level folder: create it first).

   The academy finds them there at start-up (or set `WEBOTS_HOME` / `COPPELIASIM_ROOT_DIR`). A lesson whose
   simulator is missing says so and how to install it.

Then, from this folder:

```powershell
pixi install          # ROS 2 Jazzy (RoboStack), colcon, Python deps, Node.js — one environment
pixi run start        # builds the web UI, then serves the academy
```

Open **http://localhost:8000**. There is no sign-in: the academy is a single-user app for this PC and opens
straight into the course, with your progress saved locally in `data/`. The server listens on `127.0.0.1` only.

On the first ROS run, Windows Defender Firewall may ask about `python.exe`. Discovery is restricted to
localhost (`ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`), so you may choose **private networks only** or
deny it.

## Development

```powershell
pixi run backend          # API + static UI on :8000 (uses the last frontend build)
pixi run dev-frontend     # Next.js dev server on :3000 with hot reload (API proxied to :8000)
pixi run test-backend     # fast unit tests
pixi run test-course      # every lesson's reference solution, starter and fault mutants through the REAL grader
pixi run python backend/tests/e2e_workflow.py   # Ch 2 student workflow against a running server
pixi run python backend/tests/e2e_chapter3.py   # Ch 3 robot-modeling workflow against a running server
pixi run python backend/tests/e2e_chapter4.py   # Ch 4 Gazebo workflow against a running server
pixi run python backend/tests/e2e_chapter5.py   # Ch 5 CoppeliaSim + Webots workflow against a running server
pixi run python scripts/build_references.py     # regenerate URDF reference models from lesson solutions
cd frontend; node scripts/ui-smoke.mjs           # headless Edge UI walkthrough with screenshots (also -ch03, -ch04, -ch05)
```

## What is in the first vertical slice

| Area | Implemented |
|---|---|
| Course | 16-chapter structure, **C++ (rclcpp) throughout** like the book; **Ch 1** (first node), **Ch 2** (publisher & subscriber) and **Ch 3** (pan-tilt URDF, seven-DOF arm and differential-drive robot in xacro, XML launch) implemented and validated |
| Simulation | Gazebo Harmonic headless + ros2_control (diff-drive and 7-DOF arm), Robot tab following `odom` with path trail and sim clock, Controllers tab, ground-truth grading. **Ch 5**: the same robot in CoppeliaSim (Lua + simROS2 bridge) and Webots (C++ driver on the Webots C API), one `go_to_goal` controller graded in both |
| Robot modeling | Live xacro preview of the editor buffer, 3D viewer (Preview from file / Live from `/robot_description` + TF), joint sliders publishing real `/joint_states`, TF Tree, transform playground |
| UI | Three resizable panels: lesson + steps + 5-level hints / Monaco multi-file editor, file explorer, Build·Run·Stop·Test·Reset·Restart, real process output / ROS Graph, Topic Inspector with live chart, PowerShell terminal, Test Results |
| Runtime | Per-student workspace + `ROS_DOMAIN_ID`, localhost-only discovery, Windows Job Object (memory/process limits, tree kill), ConPTY terminal, rclpy telemetry agent (graph + QoS + echo) |
| Grader | Isolated copy, own DDS domain, hidden tests never in the student workspace, behavioural pytest checks with expected/observed/suggestion |
| Persistence | One local student (no accounts): workspace, progress, hints used, build attempts, submissions, skills, portfolio (SQLite in `data/`; PostgreSQL via `ACADEMY_DATABASE_URL`) |

## Design documents

* [docs/01-migration-matrix.md](docs/01-migration-matrix.md): chapter-by-chapter ROS 1 → ROS 2 migration
* [docs/02-architecture.md](docs/02-architecture.md): services, directory layout, DB schema, Windows runtime, simulation
* [docs/03-lesson-and-assessment-schemas.md](docs/03-lesson-and-assessment-schemas.md)
* [docs/04-roadmap.md](docs/04-roadmap.md)
* [docs/06-curriculum-plan.md](docs/06-curriculum-plan.md): the real-time robotics curriculum, runtimes and build order
* [docs/reading/](docs/reading/): reading list and downloaded free references
* [docs/05-compatibility-matrix.md](docs/05-compatibility-matrix.md): RoboStack win-64 package availability (queried, not assumed)
* [courses/mastering_ros2/migration_registry.yaml](courses/mastering_ros2/migration_registry.yaml): per-example status with evidence

## Security model

There are no accounts: the academy serves one student on their own PC. Because the server builds and runs
code and offers a terminal, it must not be reachable by **other websites** open in the same browser. In place
of a login, every request passes a local-only guard (`backend/academy/security.py`):

* the server binds to `127.0.0.1` only;
* the `Host` header must be `localhost`/`127.0.0.1`, which blocks DNS-rebinding attacks;
* a present `Origin` header must be a local page, which blocks cross-site requests and WebSockets;
* every `/api` call must carry `X-Academy-Client`, which a cross-site page cannot send without a CORS preflight
  that this server never approves.

Student code runs in a Windows Job Object with its own DDS domain, and file APIs are confined to `ws/src`. These
are resource and isolation limits, **not** a security sandbox, so only run code you trust.

## Licensing note

Companion-repository code is MIT-licensed (© 2021 Packt). The book's text is copyrighted and is not
reproduced here. All lesson text, exercises and tests in `courses/` are original.
