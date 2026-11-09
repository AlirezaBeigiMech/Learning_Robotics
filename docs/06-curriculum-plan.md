# 6. Curriculum Plan: Real-Time Robotics Systems with ROS 2

The academy was a port of *Mastering ROS for Robotics Programming* (ROS 1, 2021). It is now organised around a
target skill set (R1–R8) and taught on one **course robot: a wheel-legged biped**, which runs entirely in
simulation, with its embedded firmware running in emulation, plus a bare-metal Linux host for real-time
measurements. Existing lessons are unchanged and keep their IDs, so progress is preserved.

## 6.1 Decisions

| Topic | Decision |
|---|---|
| Course robot | Wheel-legged biped: 2 legs × (hip + knee) + 2 wheel motors + IMU. Balances like an inverted pendulum, so control-loop timing has visible consequences. |
| Hardware | **None required for the robot.** Physics in Gazebo (software-in-the-loop); motor-driver and IMU firmware run in **Emulica** (`Embedded_claw/replica-server`). |
| Host OS | The repo **moves to the user's bare-metal Ubuntu machine**. The academy runs natively on Linux there, and that machine is also the PREEMPT_RT host. Windows support stays as a secondary platform for Parts I–II. |
| Linux labs | Native Linux runtime on the Ubuntu host; **QEMU VMs** only where a lab needs its own kernel/GRUB/NICs (Ch 9, 11), **containers / network namespaces** for multi-host DDS (Ch 18). |
| Real-time | **Real measurements required**: measured on the Ubuntu host itself with a PREEMPT_RT kernel. VMs and Windows run the same labs but latency is never graded there. |
| Emulica | **Used only through its existing gRPC API; Emulica itself is not modified** (see 6.4). |
| Pace | **Full-time**: dense lessons (2–4 h), light scaffolding, starter code gives structure but not solutions. |
| Books | LKP 2e, SP 2e, CCIA 2e are available. *Mastering ROS 2* 4e is not yet; chapters cite it but lessons are written against the official ROS 2 / ros2_control docs. No book text is reproduced. |

## 6.2 Competencies (`course.yaml: competencies`)

| ID | Competency | Chapters |
|---|---|---|
| `rt_cpp` | R1 Real-time C++ on PREEMPT_RT | 5, 7, 10, 13–16, 19, 21, 23, 26 |
| `concurrency` | R2 Distributed systems, multithreading, concurrency | 1, 2, 5, 8, 17, 18, 26 |
| `ros2_control` | R3 ros2_control, hardware interfaces, deterministic loops | 3, 4, 6, 7, 15, 19, 20, 21, 26 |
| `fieldbus` | R4 EtherCAT, EtherNet/IP, CAN | 19–22, 26 |
| `dds` | R5 Multi-host ROS 2/DDS | 1, 2, 8, 11, 17, 18, 23, 26 |
| `linux` | R6 Linux systems | 9–14, 18, 24, 26 |
| `infra` | R7 Ansible, Docker, Kubernetes | 23–26 |
| `x86_perf` | R8 x86 RT benchmarking | 12, 14, 16, 26 |

A unit test enforces that every competency is taught by at least one chapter.

## 6.3 Sections and chapters

Readings: **MR2** *Mastering ROS 2* 4e · **LKP** *Linux Kernel Programming* 2e · **SP** *Systems Performance* 2e ·
**CCIA** *C++ Concurrency in Action* 2e · **RM0090** STM32F4 reference manual · free docs in `docs/reading/`.
Runtime: **PC** = native Windows runtime · **VM** = Linux VM · **RT** = bare-metal real-time host.

| # | Chapter | Runtime | Readings | Status |
|---|---|---|---|---|
| **I** | **ROS 2 Foundations** | | | |
| 1 | Introduction to ROS 2 | PC | MR2 1–2 | available |
| 2 | ROS 2 Programming | PC | MR2 2–3 | available (1 of ~7 lessons) |
| 3 | 3D Modeling (URDF, xacro, TF2) | PC | MR2 4 | available |
| 4 | Gazebo + ros2_control (+ wheel-legged robot model, Stage 0) | PC | MR2 5–6 | available / robot planned |
| 5 | Executors, Callback Groups, Concurrency | PC | MR2 3 · LKP 12–13 · CCIA | planned |
| **II** | **ros2_control and Real-Time-Ready ROS 2** | | | |
| 6 | Hardware Interface (the robot's 6 joints + IMU) | PC | MR2 6, 12 | planned |
| 7 | Real-Time-Safe Controllers (LQR balance) | PC | MR2 6, 16 | planned |
| 8 | Components, Intra-Process, Zero-Copy | PC | MR2 3, 16 | planned |
| **III** | **Linux Systems for Robotics** | | | |
| 9 | Kernel: Configure, Build, Boot | VM | LKP 1–5 | planned |
| 10 | Processes, Scheduling, Affinity, cgroups | VM | LKP 6, 10–11 · SP 3, 6 | planned |
| 11 | Networking: netplan, Multi-NIC, sysctl | VM | SP 10 | planned |
| 12 | Kernel & Driver Debugging: ftrace, perf, BPF | VM | SP 4, 13–15 · LKP 4–5 | planned |
| **IV** | **Hard Real-Time** | | | |
| 13 | PREEMPT_RT and RT Application Design | RT | LKP 11–13 · RT wiki, Shuhao Wu | planned |
| 14 | CPU/IRQ Isolation and Latency Analysis | RT | SP 6, 14 · kernel docs, Red Hat RT guide | planned |
| 15 | Deterministic ros2_control Under Load (the robot at 1 kHz) | RT | MR2 6 · control.ros.org, RT WG | planned |
| 16 | x86 Benchmarking: Firmware, Caches, SMIs | RT | SP 2, 6, 7, 12–14 · Drepper | planned |
| **V** | **Distributed ROS 2 and DDS** | | | |
| 17 | QoS and DDS Internals | PC | MR2 1, 3 · ROS/DDS docs | planned |
| 18 | Multi-Host ROS 2 Debugging (robot ↔ base station) | VM | SP 10 · DDS docs, Wireshark, ros2_tracing | planned |
| **VI** | **Embedded Firmware and Industrial Communication** | | | |
| 19 | Robot Firmware on Emulated MCUs (Emulica) | VM | RM0090 · Emulica · Zephyr/CANopenNode | planned |
| 20 | CAN and CANopen with SocketCAN | VM | SocketCAN, CSS guides, ros2_canopen | planned |
| 21 | EtherCAT (real master + software slave) | RT | ETG brochure, SOEM/IgH, ethercat_driver_ros2 | planned |
| 22 | EtherNet/IP and CIP | VM | ODVA PDFs · OpENer | planned |
| **VII** | **Deployment and Infrastructure** | | | |
| 23 | Docker for Real-Time ROS 2 | VM | SP 11 · MR2 13 | planned |
| 24 | Provisioning a Robot Host with Ansible | VM | Ansible docs | planned |
| 25 | Testing, CI/CD, Kubernetes Basics | VM | MR2 13 | planned |
| **VIII** | **Capstone** | | | |
| 26 | The Virtual Wheel-Legged Robot, End to End | RT | all | planned |
| | **Electives** | | | |
| 27 | Other Simulators: CoppeliaSim, Webots | PC | MR2 5 | available |
| 28 | Navigation, Manipulation, Perception | PC | MR2 7–10 | planned |

Each chapter's interactive labs are in its `chapter.yaml` (`labs:`) and shown on the dashboard.

## 6.4 The virtual robot setup

```
 Base-station VM                              Robot host (bare-metal PREEMPT_RT, or a VM for non-RT labs)
 ┌──────────────────────┐   DDS over virtual ┌──────────────────────────────────────────────┐
 │ teleop, telemetry,   │◄── NICs + netem ──►│ controller_manager @ 1 kHz                    │
 │ visualisation, logs  │                    │  ├ balance (LQR) + leg controllers (Ch 7)     │
 └──────────────────────┘                    │  └ SystemInterface (Ch 6) ── SocketCAN vcan0  │
                                             └──────────────────────────────┼───────────────┘
                                                         CAN bridge (Ch 20) │
                ┌──────────────┬──────────────┬─────────────────────────────┼──────────────┐
          ┌─────▼─────┐  ┌─────▼─────┐       ...                      ┌─────▼─────┐  ┌─────▼─────┐
          │ STM32F4   │  │ STM32F4   │   6 × motor-driver firmware    │ STM32F4   │  │ STM32F4   │
          │ motor FW  │  │ motor FW  │   (Ch 19) in Emulica           │ motor FW  │  │ IMU FW    │
          └─────┬─────┘  └─────┬─────┘                                └─────┬─────┘  └─────┬─────┘
                └──── plant bridge: PWM/torque → physics, physics → encoder/IMU registers ───┘
                                              │ lockstep simulation time
                                     ┌────────▼────────┐
                                     │ Gazebo Harmonic │  wheel-legged robot model (Ch 4)
                                     └─────────────────┘
```

**Fidelity levels**, so work can start before the emulator bridge exists:

| Level | Motor drivers | Clock | Used for |
|---|---|---|---|
| 0 | `gz_ros2_control` (no bus) | sim time | Ch 4, 6, 7: model and controllers |
| 1 (SIL) | Small C++ "virtual drive" processes on `vcan` | wall clock | Ch 15, 20, 23: real-time and CAN with real timing on the bare-metal host |
| 2 (emulation) | Real STM32F4 firmware in Emulica | sim time, lockstep | Ch 19, 26: firmware correctness, interrupt latency, bus load |

Real-time performance is measured at Level 1 on bare metal. Level 2 checks firmware behaviour in simulation time,
so a slow emulator cannot make the robot fall for reasons that would not happen on hardware.

### Emulica adapter (academy side only; Emulica is not modified)
The academy talks to Emulica's existing gRPC services (`TelemetryService`, `ExecutionService`, `DebugService`).
What that API supports today, and therefore what Level 2 can do:

| Need | Existing API | Result |
|---|---|---|
| MCU → host CAN (status frames) | `StreamBusFrames` | ✅ adapter forwards frames to `vcan0` |
| Host → MCU CAN (commands) | none (`BusDataInject` is SPI/I²C, one byte) | ❌ **gap** |
| IMU readings into the MCU | `BusDataInject` on I2C1/SPI1 | 🟡 works, one gRPC call per byte: low rate only |
| Encoder input | `PinInject` | 🟡 fine for slow signals; quadrature at speed is too fast for per-edge gRPC |
| PWM / duty cycle out | `GetRegisterSnapshot` / peripheral output events | ✅ read timer compare registers |
| Lockstep time | `Run` / `Pause` only, no "advance N µs" | ❌ **gap**: run/pause loops are approximate, not deterministic |
| Timeline, interrupts, bus load | `StreamTelemetry`, `StreamEvents`, `StreamBusFrames` | ✅ Firmware tab |
| Licence | `AuthService` | needs a local dev licence |

Consequence: until Emulica gains **CAN RX injection** and a **time-step command** (two small server features, the
owner's call), Ch 19 Level 2 covers firmware structure, CAN *transmit*, IMU over I²C, PWM output, interrupt timing
and bus telemetry, in open loop or with slow closed loops. The full closed-loop "robot balances on emulated
firmware" result (Ch 19 final project, capstone Level 2) is marked **blocked on those two features**. Level 1 SIL
covers closed-loop CAN control in the meantime.

## 6.5 Platform work

### Runtimes (`chapter.runtime`)
| Runtime | Plan |
|---|---|
| `windows` | Existing native Windows runtime (Job Object, ConPTY, MSVC). Kept for Parts I–II. |
| `linux` | **Native Linux runtime** on the Ubuntu host (process groups + cgroup v2 limits instead of Job Objects, a PTY terminal, GCC). QEMU VMs / containers started by the academy where a lab needs its own kernel, NICs or several hosts; `tc netem` for faults. |
| `linux_rt_host` | The same Ubuntu host booted with a PREEMPT_RT kernel. Latency grading only runs here; the UI shows host, kernel, isolation settings and load next to every number. |

Porting the academy to Linux is milestone **C0**: `pixi.toml` gains `linux-64`; `runtime/winjob.py`,
`runtime/terminal.py` (ConPTY), `runtime/process.py`, `runtime/session.py`, `assessment/grader.py` and the MSVC
activation get Linux counterparts behind the existing interfaces.

For EtherCAT (Ch 21) the Ubuntu host needs a **second NIC** dedicated to the bus (a USB or PCIe Intel NIC is fine
for the software-slave labs).

### New lab tabs
* **Latency**: live histograms and percentiles (`cyclictest`, `rtla timerlat`, controller period monitor); compare two runs.
* **System**: per-CPU load, isolated CPUs, IRQ → CPU map, cgroup tree, kernel command line.
* **Network**: multi-host topology and RTPS capture summary.
* **Bus**: CAN frame inspector and bus load; EtherCAT slave/PDO view.
* **Balance**: pitch, wheel torque, leg height and loop period of the robot on one timeline.
* **Firmware**: Emulica timeline (interrupts, bus traffic, registers) for the emulated MCUs.
* **Load** panel: start/stop `stress-ng` and network load while watching the other tabs.

### New grading (`Completion.type` and grader helpers)
* `latency_budget`: p99/p99.9/max from a recorded run under a declared load; only on `linux_rt_host`.
* `rt_safety`: the grader replaces `operator new`/`malloc` during `update()` and fails on allocation or blocking.
* `balance`: the robot stays upright through a scripted disturbance sequence.
* `multi_host_delivery`: messages arrive across hosts at a given rate and loss.
* `bus_traffic`: expected CAN/EtherCAT frames and bus load observed.
* `firmware_behaviour`: emulated MCU meets watchdog, timing and protocol checks.
* `idempotent`: an Ansible playbook's second run reports zero changes.

### Honesty rules
* Teaching widgets (scheduler model, EtherCAT frame walkthrough) are labelled **model**.
* Every number shown comes from a real tool run on the named runtime.
* Book chapters are cited by number; all lesson text is original.

## 6.6 Build order

| Milestone | Content | Platform |
|---|---|---|
| **C0** | Existing Ch 1–4 lessons re-validated on Ubuntu | Linux-native runtime, `linux-64` pixi env, grader on Linux |
| **C1** | Ch 2 remaining lessons, Ch 5 | `rt_safety` grading groundwork |
| **C2** | Ch 4 wheel-legged robot (Stage 0), Ch 6, Ch 7 | Balance tab, `balance` grading |
| **C3** | Ch 8, Ch 17 | Latency tab (intra- vs inter-process), QoS playground |
| **C4** | Ch 9–12, Ch 18 | `LinuxRuntime` with QEMU VMs, System and Network tabs |
| **C5** | Ch 13–16, Ch 20 (Level 1 SIL) | Bare-metal target, Latency + Load tabs, `latency_budget`, Bus tab |
| **C6** | Ch 19 (Level 2, within API limits) | Emulica gRPC adapter: CAN TX → vcan, I²C IMU injection, PWM readout, Firmware tab |
| **C7** | Ch 21–25 | Software EtherCAT slave, Docker/Ansible labs, `idempotent` |
| **C8** | Ch 26 capstone, Ch 28 elective | Capstone spec and fault-injection grader |

C0 happens on the Ubuntu machine. C1–C3 also run on Windows. C5 needs the PREEMPT_RT kernel on the Ubuntu host.
C6's closed-loop result needs CAN RX injection and a time-step command in Emulica (not planned here).
