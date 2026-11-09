# 5. Versioned Compatibility Matrix

Baseline: **ROS 2 Jazzy** · RoboStack channel `https://prefix.dev/robostack-jazzy` + `conda-forge` · Python 3.12 ·
MSVC via `vs2019_win-64` activation (requires Visual Studio 2019 C++ workload) · Windows 10/11 x64.

"Binary" columns come from `pixi search -p <platform> ros-jazzy-<pkg>` run on **2026-10-10**.
"Validated here" means this repository has an automated check that passed on the reference Windows machine.
Re-run `scripts/check_compat.ps1` (planned M2) before each course release; pin exact versions in `pixi.lock`.

| Package | Used in | win-64 | linux-64 | Validated here |
|---|---|---|---|---|
| ros-base (rclpy, rclcpp, std_msgs, ros2cli, launch) | Ch 1–16 | ✔ (Jazzy) | ✔ | build + run spike passed (talker/listener, isolated domain); grader validation: see registry |
| colcon-common-extensions | all | ✔ | ✔ | ✔ (`--merge-install`; ament_cmake C++ with Ninja + MSVC 14.29; description packages without compiler) |
| vs2019_win-64 (MSVC activation) + ninja | C++ lessons | ✔ | n/a | ✔ rclcpp packages compile; **VS generator fails** (MAX_PATH), Ninja used via `CMAKE_GENERATOR=Ninja` |
| launch_testing_ros | grader | ✔ | ✔ | installed, not yet used by graded lessons |
| rviz2 | Ch 3+ (optional local window) | 14.1.24 | 14.1.24 | — |
| xacro | Ch 3 | 2.1.1 | 2.1.1 | ✔ live preview, launch Command(), grader expansion |
| robot_state_publisher | Ch 3 | 3.3.4 | 3.3.4 | ✔ /robot_description + TF verified numerically against reference FK |
| joint_state_publisher_gui | Ch 3 | 2.4.3 | 2.4.3 | not installed — replaced by the visible /academy_joint_gui node (browser sliders) |
| urdfdom_py (urdf_parser_py) | Ch 3 grader/preview | 1.2.1 | ✔ | ✔ |
| tf2_ros_py | Ch 3 grader | 0.36.23 | ✔ | ✔ TF lookups in tests |
| ros2_control | Ch 4, 11, 13, 15 | 4.49.0 | 4.49.0 | — |
| ros2_controllers | Ch 4, 11, 13, 15 | 4.43.0 | 4.43.0 | ✔ diff_drive_controller, joint_trajectory_controller, joint_state_broadcaster |
| gz-sim 8 (Harmonic, conda-forge) | Ch 4, 8, 12 | 8.10.0 | ✔ | ✔ headless server, RTF ≈ 0.75–0.9 (GUI window not used) |
| ros_gz (ros_gz_sim, ros_gz_bridge) | Ch 4 | 1.0.24 | 1.0.24 | ✔ create + /clock bridge |
| gz_ros2_control | Ch 4 | 1.2.20 | 1.2.20 | ✔ needs `Libraryin` on GZ_SIM_SYSTEM_PLUGIN_PATH; **no mimic joints**; position gain 2.0 |
| moveit / moveit_ros_move_group | Ch 6, 7, 15 | 2.12.4 | 2.12.4 | — |
| moveit_task_constructor_core | Ch 7 (optional) | **none** | 0.1.8 | Linux host only |
| navigation2 / nav2_bringup | Ch 6, 11 | 1.3.13 | 1.3.13 | — |
| slam_toolbox | Ch 6, 11 | 2.8.5 | 2.8.5 | — |
| robot_localization | Ch 11 | 3.8.3 | 3.8.3 | — |
| cv_bridge | Ch 10 | 4.1.0 | 4.1.0 | — |
| image_transport | Ch 10 | 5.1.8 | 5.1.8 | — |
| camera_calibration | Ch 10 | 5.0.13 | 5.0.13 | — |
| pcl_ros / pcl_conversions | Ch 10 | 2.6.5 | 2.6.5 | — |
| depthimage_to_laserscan | Ch 10 | 2.5.1 | 2.5.1 | — |
| usb_cam | Ch 10 | **none** | 0.8.1 | replaced by OpenCV capture node |
| rclcpp_components | Ch 12 | 28.1.22 | 28.1.22 | — |
| pluginlib | Ch 12 | 5.4.6 | 5.4.6 | — |
| rosbag2 | Ch 16 | 0.26.11 | 0.26.11 | — |
| ros2_tracing | Ch 16 | **none** | **none** | LTTng is Linux-only; Windows lab uses executor/callback timing instead |
| ur (Universal_Robots_ROS2_Driver meta) | Ch 15 | 3.9.0 | 3.9.0 | — |
| ur_description | Ch 15 | 3.5.1 | 3.5.1 | — |
| dynamixel_sdk | Ch 7, 9 | 4.0.3 | 4.0.3 | — |
| dynamixel_hardware | Ch 9 | **none** | **none** | build from source / own SystemInterface |
| mavros | Ch 8 | **none** | 2.16.0 | Linux host |
| px4_msgs | Ch 8 | **none** | **none** | build from source pinned to PX4 release |
| webots_ros2 | Ch 5 | **none** | **none** | not needed: the C++ driver calls the Webots C API (`Controller.lib`) directly |
| example_interfaces, image_transport | Ch 5 (simROS2 dependencies) | ✔ | ✔ | ✔ CoppeliaSim's simROS2.dll loads against them |
| micro_ros_agent | Ch 9 | **none** | **none** | build from source (micro-ROS `jazzy` branch) |
| turtlesim | Ch 1 (optional) | 1.8.4 | 1.8.4 | — |

External tools (not conda packages):

| Tool | Version guidance | Windows | Notes |
|---|---|---|---|
| CoppeliaSim Edu | **4.10.0** (Windows zip, per-user, no admin) | ✔ validated | bundled simROS2 links the Jazzy ABI (all rclcpp/rcl/tf2_ros imports resolve against RoboStack); run via the academy's `coppeliasim` launcher (ConPTY log, no conda `QT_PLUGIN_PATH`, remote-API servers off); real-time mode, no `/clock` |
| Webots | **R2025a** (per-user installer, no admin) | ✔ validated | `--batch --no-rendering --minimize` from the academy's `webots` launcher; C++ extern controller links `lib/controller/Controller.lib` (MSVC); grader ground truth via an injected supervisor using Webots' ctypes Python API; integrated Intel GPU works with a warning |
| PX4 Autopilot | pin e.g. v1.15 with matching `px4_msgs` branch | WSL2 | uXRCE-DDS agent required |
| MATLAB ROS Toolbox | release-specific | ✔ | check MathWorks' table of supported ROS 2 distributions; optional, licensed |
| Visual Studio 2019 | 16.11 with "Desktop development with C++" | ✔ | required for C++ packages and custom interfaces |
| Node.js | 22.x (pixi-provided) | ✔ | frontend build only |
