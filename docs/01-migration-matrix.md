# 1. Chapter-by-Chapter ROS 1 → ROS 2 Migration Matrix

Source: *Mastering ROS for Robotics Programming, 3rd ed.* (Joseph & Cacace, Packt 2021) and its
companion repository (`PacktPublishing/Mastering-ROS-for-Robotics-Programming-Third-edition`, MIT
licence, © 2021 Packt). The book text is copyrighted: the academy uses it only as a map of topics and
project progression. All instructional text, diagrams, exercises and tests are original. Companion
code is MIT-licensed, but we re-engineer rather than copy it, because almost none of it survives a
ROS 2 port unchanged.

Target: **ROS 2 Jazzy Jalisco**, running **natively on Windows 10/11** via RoboStack
(`robostack-jazzy` conda channel, managed by `pixi`). See
[05-compatibility-matrix.md](05-compatibility-matrix.md) for package availability per platform; where a
dependency is not available as a Windows binary, the chapter says so explicitly and provides a
labelled alternative instead of pretending.

Status vocabulary (used here and in `courses/mastering_ros2/migration_registry.yaml`):
`Not Started` → `Architecture Designed` → `Implemented` → `Builds Successfully` → `Runtime Validated` → `Exercise Validated`.
A status above `Architecture Designed` is only claimed when this repository contains the code **and** the
corresponding automated check has passed on the reference machine.

What the companion repository actually contains (inspected 2026-10-10):

| Dir | Packages | Notes |
|---|---|---|
| Chapter2 | `mastering_ros_demo_pkg` | `/numbers` Int32 talker/listener @10 Hz, `demo_msg.msg`, `demo_srv.srv`, `Demo_action.action`, actionlib server/client, roslaunch XML |
| Chapter3 | `mastering_ros_robot_description_pkg` | `seven_dof_arm.xacro` (7 revolute joints + 2 finger joints), `diff_wheeled_robot.xacro`, `pan_tilt`, Xtion Pro sensor xacro |
| Chapter4 | `seven_dof_arm_gazebo` | gazebo_ros_control, `JointTrajectoryController` YAML, obstacle world |
| Chapter5 | `csim_demo_pkg`, `webots_demo_pkg` | CoppeliaSim `.ttt` scenes, Webots `e_puck_manager` using `webots_ros` services |
| Chapter6 | `seven_dof_arm_config`, `diff_wheeled_robot_gazebo`, `diff_wheeled_robot_control` | MoveIt 1 Setup-Assistant output (KDL, OMPL/CHOMP/Pilz), gmapping, AMCL, move_base + DWA |
| Chapter7 | `seven_dof_arm_test` | move_group C++ API: collision objects, attach/detach, pick/place, GPD grasp launch |
| Chapter8 | `iris_model`, `px4_ros_ctrl` | RotorS-style iris xacro, MAVROS offboard example |
| Chapter9 | `Arduino/*.ino`, `ros_wiring_examples` | rosserial publishers (ADXL3xx, ultrasonic, odom TF), Odroid/RPi wiringPi |
| Chapter10 | `cv_bridge_tutorial_pkg`, `pcl_ros_tutorial`, `fake_laser_pkg` | cv_bridge edge detection, PCL read/write/filter, depthimage_to_laserscan nodelet |
| Chapter12 | `plugin_calculator`, `nodelet_hello_world`, `gazebo_basic_world_plugin` | pluginlib calculator, nodelet republisher, Gazebo Classic world plugin |
| Chapter13 | `my_controller`, `rviz_teleop_commander` | ros_control `PositionJointInterface` sinusoidal controller, RViz Qt panel |
| Chapter14 | `ros_matlab_test` | MATLAB scripts, Simulink models (talker, VFH obstacle avoidance, TurtleBot orientation control) |
| Chapter15 | `abb_irb6640_moveit_plugins`, `ikfast_demo` | IKFast plugin for ABB IRB 6640 |
| — | *(none for Ch 1, 11, 16)* | Ch 11 references the external Remo/diffbot project; Ch 1 and 16 are conceptual |

---

## Section I — ROS Programming Essentials

### Chapter 1 — Introduction to ROS 2  *(orig. "Introduction to ROS")*

| Field | Content |
|---|---|
| Original objectives | Why ROS; filesystem level (packages, metapackages, msgs); computation graph (master, nodes, topics, services, bags, parameter server); community level; installation |
| Robotics concepts | Distributed computing, publish/subscribe, request/response, naming, introspection |
| ROS 1 tech | `roscore`/master, `rosparam` server, catkin workspace, rosbag |
| ROS 2 replacement | DDS/RMW discovery (no master), per-node parameters, actions as first-class, QoS, colcon/ament workspaces, rosbag2 (MCAP/SQLite), `ROS_DOMAIN_ID`, `ROS_AUTOMATIC_DISCOVERY_RANGE` (Jazzy), distributions & REP 2000 platform tiers |
| Original project | Install ROS, run turtlesim, introspect graph |
| Architecture changes | Teach the graph *without* a master; discovery is the first new concept, not an afterthought |
| Interactive exercises | (1) Live-graph sandbox: build a graph of nodes/topics, see discovery & QoS matching (concept viz, labelled as such); (2) **Coding: first node** — `hello_node` rclpy node with a timer that logs a heartbeat (*implemented in the vertical slice*) |
| Automated tests | Node `hello_node` appears in the live graph; logs ≥3 heartbeats within 5 s; process exits cleanly on interrupt |
| Final project | Create a workspace + package, run the first node, introspect it with the live graph |
| Limitations | turtlesim is available in RoboStack but needs a desktop window; the academy uses its own web graph instead |

### Chapter 2 — Getting Started with ROS 2 Programming

| Field | Content |
|---|---|
| Original objectives | Create packages; topic pub/sub (C++); custom msg/srv; services; actionlib; launch files; when to use topics vs services vs actions |
| Robotics concepts | Rate-controlled loops, callbacks, request/response, long-running goals with feedback & cancel |
| ROS 1 tech | catkin, roscpp, `ros::Rate`+`spinOnce`, `message_generation`, actionlib (`SimpleActionServer`), roslaunch XML |
| ROS 2 replacement | **C++ track (rclcpp, ament_cmake)** like the book: wall timers + executors (no `spinOnce` loop), `rosidl_default_generators`, `rclcpp_action`, XML launch files, declared parameters, QoS profiles. Students write no Python; grader tests are Python infrastructure |
| Original project | `mastering_ros_demo_pkg`: `/numbers` Int32 talker/listener at 10 Hz; `demo_msg` (greeting+number); `demo_srv` (string in/out); `Demo_action` (count goal, feedback current_number) |
| Architecture changes | Timer-driven publisher instead of while-loop; QoS made explicit; interfaces must live in an ament_cmake package (Python packages cannot generate interfaces); action server uses goal/cancel callbacks and returns a result object |
| Interactive exercises | 1 publisher, 2 subscriber, 3 custom msg, 4 service server+client, 5 action server+client, 6 launch multiple nodes, 7 QoS experiments. **Lesson "Publisher & Subscriber" is the vertical slice** |
| Automated tests | Topic `/numbers` exists, type `std_msgs/msg/Int32`, rate 10 Hz ±30 %, consecutive values increase by 1; subscriber receives grader-injected hidden values; publisher/subscriber QoS compatible; end-to-end integration; service returns expected transform of hidden inputs; action emits monotonic feedback and correct result; cancel honoured |
| Final project | Multi-node "sensor → filter → monitor" app with a custom message, a reset service, a counting action and one launch file |
| Limitations | C++ needs Visual Studio 2019's C++ workload (activated by `vs2019_win-64`). Builds use **Ninja**: the default "Visual Studio 16 2019" generator fails in colcon trees (MSBuild FileTracker, MAX_PATH). First build of a package ≈15–30 s, incremental ≈5 s |

## Section II — ROS Robot Simulation

### Chapter 3 — 3D Modeling with URDF/Xacro

| Field | Content |
|---|---|
| Original objectives | URDF/xacro, links/joints/inertia/collision, RViz visualisation, pan-tilt, 7-DOF arm, differential-drive robot |
| ROS 1 tech | `robot_state_publisher`, `joint_state_publisher(_gui)`, rviz, `xacro --inorder`, `check_urdf`, `$(find pkg)` |
| ROS 2 replacement | `robot_state_publisher` takes `robot_description` **as a parameter** (no global param server); `joint_state_publisher_gui`; RViz2; `xacro` 2.x; `$(find pkg)` still works in xacro; launch via `Command(['xacro ', path])` |
| Original project | `seven_dof_arm.xacro` (shoulder_pan, shoulder_pitch, elbow_roll, elbow_pitch, wrist_roll, wrist_pitch, gripper_roll + 2 fingers); `diff_wheeled_robot.xacro` (base r=0.15 m, wheel r=0.04 m, separation 0.6 m, front/back casters) |
| Architecture changes | Drop `<transmission>` + `gazebo_ros_control` tags (moved to `<ros2_control>` in Ch 4); fix inertias for physics realism; separate `*_description` packages |
| Interactive exercises | Live URDF editor with Three.js preview (parse errors shown inline); joint sliders; TF-tree view; collision/visual toggle; student writes xacro macros for wheels |
| Automated tests | `xacro` expands; `check_urdf` passes; joint count/types/limits match spec; TF tree has single root; inertia matrices positive-definite; mass within tolerance |
| Final project | Complete xacro for both robots + launch with robot_state_publisher |
| Limitations | RViz2 runs natively on Windows (RoboStack) as an *optional* local window; the in-browser viewer is the primary visualisation. Meshes are not rendered yet (primitive geometry only) |
| Windows findings (validated) | `ament_cmake` description packages build without MSVC (`project(<pkg> NONE)`); `ros2 launch` decodes xacro output with the ANSI codepage unless Python runs in UTF-8 mode (`PYTHONUTF8=1`, now set for every student/grader process); robot_state_publisher (KDL) warns when the root link has inertia — explained in the lessons, fixed with a massless root in Ch 4 |
| Status | **Exercise Validated** — see registry |

### Chapter 4 — Simulating Robots with Gazebo

| Field | Content |
|---|---|
| Original objectives | Gazebo models, gazebo_ros_control, Xtion depth sensor, joint controllers, diff-drive plugin, teleop |
| ROS 1 tech | Gazebo Classic 11, `gazebo_ros_pkgs`, `gazebo_ros_control`, `libgazebo_ros_diff_drive.so`, ros_control controllers (`effort_controllers/JointPositionController`, JTC) |
| ROS 2 replacement | **Gazebo Harmonic** (gz-sim 8) + `ros_gz_sim`/`ros_gz_bridge` + `gz_ros2_control` + `ros2_controllers` (`joint_trajectory_controller`, `diff_drive_controller`, `joint_state_broadcaster`). Gazebo Classic is EOL and has no Jazzy support |
| Original project | 7-DOF arm in Gazebo with JTC + RGB-D; diff-drive robot with teleop |
| Architecture changes | `<ros2_control>` URDF tag + controller YAML loaded by `controller_manager`; spawn via `ros_gz_sim create`; bridges declared explicitly |
| Interactive exercises | Student writes a JTC client and a `cmd_vel` velocity node; observe joint states; spawn into an obstacle world |
| Automated tests | Controllers reach `active`; arm reaches goal within tolerance; robot travels 1 m ±10 % for a commanded profile |
| Final project | Controllable arm + mobile robot simulations |
| Windows status (validated 2026-10-11) | **Works natively.** Gazebo Harmonic (gz-sim 8.10) runs headless at RTF ≈ 0.75–0.9; ros_gz bridge, `ros_gz_sim create`, gz_ros2_control, diff_drive_controller and joint_trajectory_controller verified. Windows-specific fixes applied by the platform: (1) `gz_ros2_control-system.dll` lives in `Libraryin` but gz searches `Library\lib` → `GZ_SIM_SYSTEM_PLUGIN_PATH` extended, else no controller_manager starts; (2) gz_ros2_control fails to start with `<mimic>` joints (either syntax) → simulation model commands both fingers; (3) default `position_proportional_gain` (0.1) cannot lift a finger against gravity from its limit → 2.0; (4) gz-transport pinned to localhost with a per-student `GZ_PARTITION`; (5) simulation tests time against `/clock`, never the wall clock. Gazebo's log folder name contains ':' (harmless warning on Windows). GUI window not used — the browser renders the robot from TF |
| Lessons | `ch04_diffbot_gazebo` (ros2_control + diff_drive_controller, odometry validated against Gazebo ground truth, C++ closed-loop drive node) and `ch04_arm_gazebo` (JTC for arm + gripper, C++ trajectory node) — **Exercise Validated** |

### Chapter 5 — CoppeliaSim and Webots

| Field | Content |
|---|---|
| ROS 1 tech | CoppeliaSim RosInterface/simROS plugin, Lua scripts; Webots `webots_ros` service-per-device API |
| ROS 2 replacement | CoppeliaSim 4.10 **simROS2** (its Windows build links the Jazzy rclcpp ABI: every imported symbol resolves against RoboStack; needs `example_interfaces` + `image_transport`). Webots R2025a **C controller API** (`Controller.lib`, MSVC-compatible) called from a C++ rclcpp node: the same API `webots_ros2_driver` wraps, which has no Windows build |
| Architecture changes | One portable contract for every simulator: `/cmd_vel` (Twist) in; `/odom` (Odometry, from encoders) + TF `odom → base_link` out; Webots also `/clock`, `/joint_states`, `/scan`. Lesson `ch05_coppeliasim`: Lua add-on (`-a`) imports the URDF with simURDF and bridges it with simROS2, plus a provided `/ground_truth` add-on (`-b`). Lesson `ch05_webots`: C++ extern-controller driver (step loop, sim time, encoders, lidar → LaserScan with Webots' clockwise order reversed, 0.5 s command time-out) and a `go_to_goal` controller graded unchanged in both simulators |
| Exercises / tests | Ground truth: CoppeliaSim `/ground_truth`; Webots: a supervisor robot the grader appends to a copy of the student's world, read by a separate Python process (Webots' ctypes API). Tests compare true motion with commands and odometry, check scan orientation against a wall ahead and a box on the left, and run `go_to_goal` in both simulators (`workspace.uses` submits the previous lesson's package too) |
| Limitations | Both simulators are separate desktop installs, detected at start-up (`WEBOTS_HOME`, `COPPELIASIM_ROOT_DIR`, or the per-user install folders); lessons declare `requires:` and show install instructions when missing. simROS2 has no `rosgraph_msgs/Clock`, `JointState` or `TwistStamped`: the CoppeliaSim bridge runs in real time with ROS-time stamps and publishes wheel TF directly. simURDF cannot import a URDF whose root link is empty, so the Chapter 5 model's root is `base_link` (KDL warns, harmlessly). The academy's `coppeliasim` launcher runs CoppeliaSim on a ConPTY (its log is fully buffered on pipes), clears the conda `QT_PLUGIN_PATH` (crash 0xC0000409) and disables the fixed-port remote-API servers |

### Chapter 6 — MoveIt 2 and Nav2

| Field | Content |
|---|---|
| ROS 1 tech | MoveIt 1 Setup Assistant, move_group, KDL; gmapping, AMCL, move_base (navfn + DWA), costmap_2d |
| ROS 2 replacement | MoveIt 2 (Setup Assistant 2, `moveit_configs_utils`, MoveItPy/`MoveGroupInterface`); **slam_toolbox** (gmapping not ported); **Nav2** (`nav2_amcl`, planner/controller servers, behaviour trees, `nav2_regulated_pure_pursuit` / DWB) |
| Exercises / tests | Plan arm to target pose; SLAM a world; send NavigateToPose goals; tests on planning success, path-length bounds, goal tolerance |
| Windows status | win-64 binaries exist for `moveit` 2.12.4, `moveit_ros_move_group`, `navigation2`/`nav2_bringup` 1.3.13, `slam_toolbox` 2.8.5, `robot_localization` 3.8.3. Pending runtime validation on Windows. Pure-algorithm exercises (A* on an occupancy grid, particle-filter update, IK) also run natively with real tests |

### Chapter 7 — Advanced MoveIt 2

| Field | Content |
|---|---|
| ROS 1 tech | move_group C++ API, PlanningSceneInterface, attach/detach, `moveit_msgs/Grasp` pick/place, GPD, DYNAMIXEL arm |
| ROS 2 replacement | `moveit::planning_interface::MoveGroupInterface` (rclcpp), PlanningSceneInterface, **MoveIt Task Constructor** for pick-and-place (the MoveIt 1 `pick()`/`place()` pipeline is not available in MoveIt 2); `dynamixel_sdk`/`dynamixel_hardware` for real arms |
| Exercises / tests | Add collision objects, check collision, IK/FK, pick-and-place avoiding an obstacle; tests assert object attached/released and pose within tolerance |
| Limitations | **MoveIt Task Constructor has no win-64 RoboStack build** (linux-64 0.1.8 only) → pick-and-place is taught with `MoveGroupInterface` + `PlanningSceneInterface` attach/detach sequences natively; MTC variant offered on a Linux host. GPD has no maintained ROS 2 port → students implement a geometric top-down grasp generator. `dynamixel_sdk` 4.0.3 is available on win-64; `dynamixel_hardware` is not |

### Chapter 8 — Aerial Robots

| Field | Content |
|---|---|
| ROS 1 tech | MAVROS + PX4 SITL (offboard), RotorS |
| ROS 2 replacement | PX4 **uXRCE-DDS** bridge + `px4_msgs` (PX4's native ROS 2 path) or `mavros` for ROS 2; Gazebo Harmonic `x500` model. RotorS has no ROS 2 port |
| Exercises / tests | Offboard state machine: arm → takeoff → waypoints → land, with safety checks (heartbeat ≥2 Hz before mode switch, geofence, battery, failsafe on setpoint loss). Natively testable against a student-runnable **mock autopilot** node (labelled as such) implementing the same topics; full PX4 SITL on the Linux backend |
| Limitations | **No win-64 builds of `mavros` or `px4_msgs`** in robostack-jazzy (mavros exists for linux-64 only; px4_msgs is built from source against the matching PX4 release). PX4 SITL targets Linux/macOS → WSL2 or Linux host. Native Windows path: student builds `px4_msgs` from source in their workspace *or* uses the labelled mock autopilot |

## Section III — ROS Robot Hardware Prototyping

### Chapter 9 — I/O Boards, Sensors and Actuators

| Field | Content |
|---|---|
| ROS 1 tech | rosserial (Arduino, Tiva C), wiringPi on Odroid/RPi, `dynamixel_motor` |
| ROS 2 replacement | **micro-ROS** (rclc on MCU + micro-ROS agent); serial protocols via `pyserial`/`serial_driver`; `dynamixel_sdk`; ros2_control hardware interfaces |
| Exercises / tests | Simulated MCU (a Python process speaking the same byte protocol over a virtual serial pair / TCP) → student writes the ROS 2 driver node; button, ultrasonic, IMU publishers; tests drive the fake device and check message timing/units/frames |
| Limitations | **No `micro_ros_agent` RoboStack build** → the micro-ROS agent is built from source or run on Linux/WSL; the default native path is a serial/TCP protocol driver written in rclpy. Real Arduino flashing is local-only; the simulated device is labelled as simulated and is replaceable by real hardware through the same driver interface |

### Chapter 10 — Vision: OpenCV and PCL

| Field | Content |
|---|---|
| ROS 1 tech | `cv_bridge`, `image_transport`, `usb_cam`, `camera_calibration`, openni/RealSense, `pcl_ros`, nodelets |
| ROS 2 replacement | `cv_bridge`, `image_transport`, `camera_calibration`, `pcl_conversions`, `sensor_msgs_py.point_cloud2`; components instead of nodelets |
| Exercises / tests | Student image-processing node (edges, colour blob, features) fed from recorded/synthetic images; point-cloud voxel/crop filters; tests compare output against reference metrics (e.g. IoU of detected blob, voxel count) on hidden images |
| Limitations | `cv_bridge`, `image_transport`, `camera_calibration`, `pcl_ros`, `depthimage_to_laserscan` all have win-64 builds. **`usb_cam` does not** (Linux V4L2 only) → webcam lessons use an OpenCV `VideoCapture` publisher node students write |

### Chapter 11 — Differential-Drive Robot Hardware (Remo)

| Field | Content |
|---|---|
| Original | Remo DIY robot: Jetson Nano, Teensy MCU via rosserial, encoder motors, LiDAR, `hardware_interface::RobotHW`, diff_drive_controller, Navigation Stack |
| ROS 2 replacement | ros2_control `SystemInterface` hardware plugin + `diff_drive_controller`; micro-ROS or serial protocol to MCU; `robot_localization` EKF; Nav2 |
| Exercises / tests | Wheel-velocity PID on a simulated motor plant; odometry integration with adjustable wheel radius/separation (interactive kinematics); hardware-interface read/write against simulated encoders; tests assert odometry error < tolerance over hidden trajectories |
| Limitations | Real hardware optional; the plugin compiles natively with MSVC |

## Section IV — Advanced ROS Programming

### Chapter 12 — Components, pluginlib, Gazebo plugins

| Field | Content |
|---|---|
| ROS 1 tech | pluginlib, **nodelets**, Gazebo Classic plugins |
| ROS 2 replacement | pluginlib (same concept, `PLUGINLIB_EXPORT_CLASS`, `pluginlib_export_plugin_description_file`); **rclcpp_components** composable nodes + `component_container` + intra-process comms; **gz-sim System plugins** |
| Exercises / tests | Calculator plugin family; two components loaded into one container vs separate processes, latency/copy comparison measured by the test harness |
| Limitations | Gazebo plugin part on the Linux backend (see Ch 4) |

### Chapter 13 — Controllers and Visualisation Plugins

| Field | Content |
|---|---|
| ROS 1 tech | `controller_interface::Controller<PositionJointInterface>` (init/starting/update), RViz Qt panel |
| ROS 2 replacement | `controller_interface::ControllerInterface` lifecycle (`on_init/on_configure/on_activate/update`), command/state interfaces, `mock_components/GenericSystem`; RViz2 `rviz_common::Panel` |
| Exercises / tests | Sinusoidal + PD joint controller on a mock-hardware loop that runs natively; live charts of command/state/error; tests check tracking RMS error and lifecycle transitions |

### Chapter 14 — MATLAB and Simulink

| Field | Content |
|---|---|
| ROS 2 replacement | MATLAB **ROS Toolbox** ROS 2 API (`ros2node`, `ros2publisher`, Simulink ROS 2 blocks). Licensed, optional |
| Exercises / tests | Orientation controller for a mobile robot. Path A: MATLAB/Simulink locally (academy only grades the ROS 2 behaviour it observes). Path B: Python control-design alternative (`numpy`/`scipy`/`python-control`) with identical behavioural tests |
| Limitations | No MATLAB execution in the browser. ROS Toolbox ↔ Jazzy compatibility depends on MATLAB release — check MathWorks' supported-distribution table |

### Chapter 15 — Industrial Robots

| Field | Content |
|---|---|
| ROS 1 tech | ROS-Industrial (`industrial_robot_client`, `abb_driver`), `universal_robot`, IKFast/OpenRAVE |
| ROS 2 replacement | `Universal_Robots_ROS2_Driver` + `ur_description` + MoveIt 2 config with `mock_components`; ABB via community `abb_ros2` (verify Jazzy) or a ported IRB 6640 URDF with mock hardware; IKFast via MoveIt 2 `moveit_kinematics` IKFast plugin generator (OpenRAVE needs Docker/Linux) |
| Exercises / tests | Industrial pick-and-place cell; tests on cycle time, collision-free plan, joint-limit compliance, speed scaling |
| Limitations | Real robot drivers need a lab network; all graded exercises run on mock hardware |

### Chapter 16 — Troubleshooting & Best Practices

| Field | Content |
|---|---|
| Original | VS Code setup, best practices, ROS coding style, troubleshooting tips (roswtf, etc.) |
| ROS 2 replacement | VS Code + ROS extension, `ros2 doctor`, `ros2 bag`, QoS events, `ros2 lifecycle`, `ros2_tracing`, launch debugging, rmw selection, `--no-daemon` |
| Exercises / tests | Broken-project labs: QoS mismatch, wrong frame_id, missing `<exec_depend>`, invalid `package.xml` (e.g. a malformed maintainer email silently turns an ament package into a plain Python package — observed while building this platform on Windows), launch parameter type error, controller YAML error, wrong message type, executor deadlock. Each graded by behaviour after repair |
| Windows-specific labs | `ros2` daemon holding pipes open, PATH length limits (`--merge-install`), firewall prompts on first DDS use, `setup.bat` vs `setup.ps1` |
