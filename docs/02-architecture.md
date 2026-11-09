# 2. System Architecture (native Windows)

## 2.1 Goals and constraints

* Runs on a student's own **Windows 10/11** PC. No Docker, no WSL needed for Milestone 1.
* Executes **real, student-authored ROS 2 Jazzy code** (RoboStack build, managed by `pixi`).
* Never fakes output: every terminal byte, graph edge, message and test result comes from a real process.
* Modular: each "service" below is a Python package with its own router and a narrow interface, so it can
  be split into separate processes or hosts later without changing the frontend contract.

## 2.2 Component view

```
 Browser (Next.js static app, served by the backend)
 ┌───────────────────────────────────────────────────────────────────────────────┐
 │ Course panel │ Monaco editor + file tree + xterm terminal │ Robotics lab tabs │
 └──────┬──────────────────────┬──────────────────────────────────────┬──────────┘
        │ REST /api/*          │ WS /ws/terminal  WS /ws/runtime      │
 ┌──────▼──────────────────────▼──────────────────────────────────────▼──────────┐
 │ FastAPI process  (python -m academy, inside the pixi env)                     │
 │  content   guard  workspace   runtime   telemetry   assessment   progress    │
 │  (YAML)   (local) (files)     (procs)   (agent I/O) (grader)     (SQLite/PG)  │
 └───┬──────────────┬────────────────┬──────────────┬─────────────┬──────────────┘
     │ reads         │ fs             │ spawns        │ stdin/stdout │ spawns
 courses/        data/workspaces/  Windows Job     telemetry      grader process tree
 (lessons,       <user>/ws/src     Object per      agent (rclpy,  in a temp copy of the
 hidden tests)                     student: nodes, hidden node)   package, own DDS domain,
                                   builds, PTY                    hidden tests copied in
```

| Service (package `academy.*`) | Responsibility | Interface |
|---|---|---|
| `content` | Load & validate `courses/**` (Pydantic), serve public lesson data, keep hidden tests server-side | `GET /api/courses/...` |
| *(no auth)* | Single local student. A local-only guard (Host + Origin checks, required `X-Academy-Client` header) replaces sign-in | `GET /api/me` |
| `workspace` | Per-student colcon workspace on disk, starter-file materialisation, safe path resolution, reset | `/api/workspace/*` |
| `runtime` | Build/run/stop/restart processes in the student's ROS environment; PTY terminal; resource limits | `/api/runtime/*`, `WS /ws/terminal`, `WS /ws/runtime` |
| `telemetry` | Long-lived rclpy agent per student: graph snapshots with QoS, topic echo, rate, numeric series | over `WS /ws/runtime` |
| `assessment` | Isolated grader: copy → build → run hidden pytest suites → parse JUnit → structured results | `/api/assessment/*` |
| `progress` | Lesson/step completion, submissions, build attempts, hints consumed, skills | `/api/progress/*` |
| `simulation` *(M3)* | `SimulationBackend` interface: `kinematic-browser`, `gazebo-remote` | — |
| `tutor` *(M6)* | AI tutor with lesson/code/log context, 5-level hint policy | — |

## 2.3 Directory structure

```
Interactive_learn/
├─ pixi.toml                    # the whole toolchain: ROS 2 Jazzy, MSVC activation, Python deps, Node
├─ README.md                    # Windows setup & run instructions
├─ docs/                        # this design
├─ courses/mastering_ros2/
│  ├─ course.yaml               # 16 chapters, sections, ordering
│  ├─ migration_registry.yaml   # §17 registry with verification statuses
│  └─ chapter_NN/
│     ├─ chapter.yaml
│     └─ lessons/<lesson_id>/
│        ├─ lesson.yaml         # metadata, objectives, steps, hints, checkpoints (schema in doc 03)
│        ├─ content/*.md        # original explanations with ```academy:*``` interactive blocks
│        ├─ starter/            # files materialised into the student's workspace
│        ├─ solution/           # reference solution (revealed only at hint level 5)
│        └─ tests/              # hidden behavioural tests — never copied into the student workspace
├─ backend/
│  ├─ academy/
│  │  ├─ __main__.py  app.py  config.py  db.py  models.py  security.py
│  │  ├─ content/  auth/  workspace/  runtime/  telemetry/  assessment/  progress/
│  │  └─ runtime/agent/academy_agent.py   # rclpy introspection agent (runs inside ROS env)
│  ├─ grader_support/            # pytest plugin + ROS test helpers shipped into grader runs
│  └─ tests/                     # backend tests (unit + real ROS integration)
├─ frontend/                     # Next.js (static export) + Monaco + React Flow + xterm.js
├─ scripts/validate_course.py    # runs every reference solution through the real grader
└─ data/                         # runtime state (gitignored): academy.db, workspaces/, grader/
```

## 2.4 Database schema (SQLAlchemy 2; SQLite default, PostgreSQL via `ACADEMY_DATABASE_URL`)

```sql
users            (id PK, email UNIQUE, display_name, password_hash, created_at, last_login_at)
workspaces       (id PK, user_id FK→users UNIQUE, path, ros_domain_id UNIQUE, created_at)
lesson_progress  (id PK, user_id FK, lesson_id, status ENUM(not_started,in_progress,completed),
                  current_step, steps_completed JSON, hints_used JSON {step_id: level},
                  started_at, completed_at, UNIQUE(user_id, lesson_id))
build_attempts   (id PK, user_id FK, lesson_id NULL, started_at, finished_at, exit_code,
                  duration_ms, output_tail TEXT, packages JSON)
submissions      (id PK, user_id FK, lesson_id, checkpoint_id, created_at,
                  files JSON {relpath: content}, status ENUM(queued,running,passed,failed,error),
                  score REAL, results JSON, grader_log TEXT, finished_at)
skill_mastery    (id PK, user_id FK, skill, evidence_submission_id FK, achieved_at, UNIQUE(user_id, skill))
events           (id PK, user_id FK, kind, lesson_id NULL, payload JSON, created_at)   -- audit/analytics
```

`results` JSON shape (also returned by the API):

```json
{"build": {"ok": true, "log_tail": "..."},
 "tests": [{"id": "test_publisher_rate", "title": "Publishes at 10 Hz", "status": "passed|failed|error|skipped",
            "hidden": false, "expected": "8–13 Hz", "observed": "9.98 Hz", "message": "...", "suggestion": "..."}],
 "summary": {"passed": 5, "failed": 1, "total": 6}}
```

## 2.5 ROS 2 execution environment (Windows)

**Toolchain**: one pixi environment (`.pixi/envs/default`) containing RoboStack `ros-jazzy-ros-base`,
`launch_testing_ros`, colcon, the `vs2019_win-64` MSVC activation package (C++ and interface generation),
CMake, Ninja. The backend itself runs inside this environment, so every child process inherits a correct
ROS environment without sourcing scripts.

**Per-student isolation** (single-machine model):

| Concern | Mechanism |
|---|---|
| Filesystem | Workspace at `data/workspaces/<user_id>/ws`. All file APIs resolve paths with `Path.resolve()` and reject anything outside `ws/src` (no `..`, no absolute paths, no symlinks, size and count limits) |
| DDS isolation | Unique `ROS_DOMAIN_ID` per student (pool 1–100, persisted), `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`, grader uses a separate reserved pool (101–120 via `ROS_DOMAIN_ID`, port-safe on Windows) |
| Process lifetime | Each run/build/terminal is started with `CREATE_NEW_PROCESS_GROUP` and assigned to a per-student **Windows Job Object** with `KILL_ON_JOB_CLOSE`, a job memory limit and an active-process limit. Stop = `CTRL_BREAK_EVENT` → 3 s grace → `TerminateJobObject`/`taskkill /T /F` |
| CLI pitfalls | ROS CLI calls made by the platform use `--no-daemon` (the ros2 daemon otherwise inherits and holds pipes on Windows) |
| Overlay | Builds use `colcon build --merge-install` (Windows PATH-length safe). Run commands execute `call install\setup.bat && ros2 run …` through `cmd.exe /d /s /c` (raw command line — Python's list quoting breaks `cmd`) |
| Terminal | ConPTY via `pywinpty`: PowerShell with the pixi ROS env and the student's domain; overlay auto-sourced when built |
| Concurrency | One build at a time per student (asyncio lock); max N concurrent processes per student |

Security note: Windows processes under the same user account are **not a security sandbox**. This model
is appropriate for a student running the academy on their own machine. A multi-tenant hosted deployment
must use the `ContainerRuntime` backend (Linux containers; designed, not part of M1) behind the same
`RuntimeBackend` interface.

**Robot model support (Chapter 3+).** `POST /api/robot/preview` expands the student's file — including unsaved
editor content, written to a transient sibling file so relative includes resolve — with the real `xacro`, then
analyses it with the shared `academy_grader.urdf_tools` (single tree, limits, axes, inertia validity). The agent's
`robot_watch` subscribes to `/robot_description` (TRANSIENT_LOCAL), `/tf`, `/tf_static` and `/joint_states`; its
`joint_gui` command creates a *visible* `/academy_joint_gui` node publishing slider values on `/joint_states`.
Agent subscriptions are remembered by the runtime and replayed whenever the agent restarts (e.g. after a build).

**Telemetry agent** (`academy_agent.py`): a hidden rclpy node (`/_academy_telemetry`) per student,
started lazily, speaking JSON-lines over stdin/stdout. Every second it emits a graph snapshot built from
`get_node_names_and_namespaces`, `get_topic_names_and_types`, `get_publishers_info_by_topic` /
`get_subscriptions_info_by_topic` (including reliability/durability/history/depth), service and action
names. It computes QoS compatibility per pub/sub pair. On `echo` it subscribes with an adaptive QoS
(best-effort/volatile, which matches any publisher), throttles to ≤10 msgs/s to the browser, measures
rate, and flattens numeric fields for charts. Its own node and endpoints are filtered out.

## 2.6 Robotics simulation integration architecture

```
SimulationBackend (interface)
  ├─ KinematicBrowserBackend   Level A — Three.js, URDF, joint sliders, TF, diff-drive kinematics.
  │                             Runs in browser; driven by REAL /joint_states, /tf, /odom from the
  │                             student's ROS graph via the telemetry agent. Labelled "kinematic view".
  ├─ GazeboLocalBackend         Level B — gz-sim 8 (Harmonic) + ros_gz + gz_ros2_control, all available as
  │                             win-64 RoboStack/conda-forge binaries. Server runs headless (`gz sim -s`)
  │                             in the student's Job Object; poses/joint states reach the browser through
  │                             ros_gz_bridge → telemetry. Optional native gz GUI window. Started on demand.
  ├─ GazeboRemoteBackend        Same contract on a Linux host (WSL2/server) for hosted multi-user use and
  │                             for Linux-only stacks (PX4 SITL, MoveIt Task Constructor, webots_ros2).
  └─ ExternalSimulatorBackend   CoppeliaSim (simROS2) / Webots (webots_ros2), local installs, detected.
```

Lessons declare `simulation: {level: A|B, backend: ...}`; a lesson requiring Level B shows an explicit
"requires simulation host" state rather than substituting a visualisation.

## 2.7 Request flow — "Run publisher"

1. Browser `POST /api/runtime/run {"package":"ros2_topics_lab","executable":"number_publisher"}`.
2. `runtime` verifies the package is built (else 409 with hint), spawns
   `cmd.exe /d /s /c "call <ws>\install\setup.bat && ros2 run ros2_topics_lab number_publisher"` with
   the student env, in the student Job Object; returns `process_id`.
3. stdout/stderr lines are pushed to the student's `WS /ws/runtime` channel as `{"type":"proc_output"}`.
4. The telemetry agent's next snapshot shows `/number_publisher` → `/numbers`; the graph tab updates.
5. Student clicks `/numbers` → `{"type":"echo","topic":"/numbers"}` → agent subscribes → live messages + chart.
