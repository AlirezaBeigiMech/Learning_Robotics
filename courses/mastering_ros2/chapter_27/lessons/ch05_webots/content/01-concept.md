## Webots and extern controllers

**Webots** is the book's second simulator. In Webots, every robot has a **controller**: a program that reads the
robot's sensors and commands its actuators through the **Webots controller API**. Normally Webots starts that
program itself. With `controller "<extern>"` it waits for you to start it. Here that program is a ROS 2 node, so
it can publish and subscribe as well.

```
 ┌───────── Webots (headless, real time) ──────────┐         ┌──────── webots_driver (your C++ node) ────────┐
 │  world: floor, wall, box                        │  IPC    │  loop:                                        │
 │  DEF DIFFBOT Robot  controller "<extern>"  ◀────┼────────▶│    wb_robot_step(16 ms)   ← Webots advances   │
 │    left/right_wheel_motor   (RotationalMotor)   │         │    /clock                                     │
 │    left/right_wheel_sensor  (PositionSensor)    │         │    /cmd_vel  → wb_motor_set_velocity           │
 │    laser                    (Lidar)             │         │    encoders  → /joint_states, /odom, /tf      │
 └─────────────────────────────────────────────────┘         │    lidar     → /scan                          │
                                                             └───────────────────────────────────────────────┘
```

The key call is `wb_robot_step(16)`. It hands control to Webots, which simulates 16 ms and returns. Between two
steps your node reads sensors, publishes, and handles the ROS messages that arrived (`rclcpp::spin_some`). So the
**simulation sets the pace**, and the node publishes `/clock` so every other node runs on simulated time, as
Gazebo's clock bridge did in Chapter 4.

| Webots C API | Purpose |
|---|---|
| `wb_robot_init()`, `wb_robot_step(ms)`, `wb_robot_get_time()` | connect, advance, simulated time |
| `wb_robot_get_device("name")` | a device handle, by the name in the world file |
| `wb_motor_set_position(m, INFINITY)` + `wb_motor_set_velocity(m, rad_s)` | velocity control |
| `wb_position_sensor_enable` / `_get_value` | wheel encoder angle (rad) |
| `wb_lidar_enable` / `wb_lidar_get_range_image` | one range per beam |

```academy:callout
kind: compare
title: ROS 1 → ROS 2
body: |
  The book's ROS 1 `webots_ros` package exposed every device as ROS **services** (`/e_puck/left_wheel_motor/set_velocity`…),
  with a generic controller inside Webots. ROS 2 uses **webots_ros2_driver**, a C++ driver with per-robot plugins that
  call this same C API. The driver you write here is a hand-made version of that design. webots_ros2 itself is not
  built for Windows, but the Webots C API is, so your node links `Controller.lib` from the Webots installation
  (see `CMakeLists.txt`).
```

The second half of the lesson brings back the **adapter contract** from the CoppeliaSim lesson. Once your driver
implements it, a controller written against `/cmd_vel` and `/odom` drives either simulator, and you will run one on
both.
