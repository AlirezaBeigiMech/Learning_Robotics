## One robot, many simulators

In Chapter 4 the diffbot ran in Gazebo, and `gz_ros2_control` + `diff_drive_controller` connected it to ROS.
Gazebo is not the only simulator. The book's Chapter 5 uses two others: **CoppeliaSim** (this lesson) and
**Webots** (next lesson). Each talks to ROS in its own way, so the question for this chapter is how to keep your
**robot software** the same when the **simulator** changes.

The answer is a **simulator adapter**: a thin layer that speaks the simulator's API on one side and a fixed set
of ROS topics on the other. This chapter uses one **contract** for every simulator:

| Direction | Topic | Type | Meaning |
|---|---|---|---|
| in | `/cmd_vel` | `geometry_msgs/msg/Twist` | desired body velocity: `linear.x` (m/s), `angular.z` (rad/s) |
| out | `/odom` | `nav_msgs/msg/Odometry` | pose and velocity **estimated from the wheel encoders** (frame `odom` → `base_link`) |
| out | `/tf` | `odom → base_link`, wheels | the same pose as a transform, so TF users (RViz, Nav2, the Robot tab) see the robot move |

Any node that only uses this contract runs unchanged on CoppeliaSim, Webots or, through a different adapter,
the real robot. You will prove that at the end of the next lesson.

### CoppeliaSim and simROS2

```
 ┌──────────────── CoppeliaSim (headless, real time) ─────────────────┐
 │  diffbot model  ◀── simURDF.import(diffbot.urdf)                    │
 │      ▲ joint target velocities        │ joint positions             │
 │      │                                ▼                             │
 │   diffbot_bridge.lua  (your add-on: sysCall_actuation / _sensing)    │
 │      ▲ simROS2 subscription           │ simROS2 publisher, TF       │
 └──────┼────────────────────────────────┼─────────────────────────────┘
        │ /cmd_vel                       ▼ /odom, /tf          ground_truth.lua ─▶ /ground_truth
```

CoppeliaSim runs Lua (or Python) scripts **inside** the simulator. The **simROS2** plugin gives those scripts ROS 2
publishers, subscriptions, services and TF. Your bridge is an **add-on** (a script loaded at start-up) with three
callbacks:

| Callback | When | Your job |
|---|---|---|
| `sysCall_init` | once | import the robot, create the ROS interfaces |
| `sysCall_actuation` | every step, before physics | command the wheel motors from the latest `/cmd_vel` |
| `sysCall_sensing` | every step, after physics | read the wheel encoders, update and publish odometry |

```academy:callout
kind: compare
title: ROS 1 → ROS 2
body: |
  The book used the ROS 1 **RosInterface** plugin (`simROS`) and scene child scripts saved inside a `.ttt` scene.
  Here the same idea uses **simROS2**, and the scripts are plain `.lua` files in your ROS package, loaded with
  CoppeliaSim's `-a` option, so you can edit, version and grade them like any other source file.
```

```academy:callout
kind: note
title: What simROS2 cannot do
body: |
  simROS2 is compiled for a fixed list of message types. In CoppeliaSim 4.10 the list has no
  `rosgraph_msgs/Clock` and no `sensor_msgs/JointState`. So this bridge runs the simulation in **real time** and stamps
  messages with ROS time instead of simulated time, and it publishes the wheels' rotation directly as TF. Webots,
  driven from C++, has no such limits. Different simulators give an adapter different tools.
```
