## From a model to a simulated robot

In Chapter 3 your robot was **kinematic**: TF said where its parts were, but nothing had mass or friction.
Now it moves under **physics**. **Gazebo Harmonic** integrates forces, contacts and inertia, using the
`<inertial>` and `<collision>` elements you wrote.

Your code never talks to Gazebo directly. **ros2_control** sits in between:

```
            ┌──────────── Gazebo (gz sim -s, headless physics) ─────────────┐
            │  robot model  ◀─ joint commands ──  gz_ros2_control plugin    │
            │  (from URDF)  ── joint states   ─▶  └─ controller_manager ───┼──▶ /joint_states, /odom, TF
            └───────────────────────────────────────────▲──────────────────┘
                                                        │ /cmd_vel, trajectories
                                              your C++ nodes
```

| Piece | Role |
|---|---|
| `<ros2_control>` in the URDF | declares the **hardware**: here `gz_ros2_control/GazeboSimSystem`, plus per joint which **command** and **state** interfaces exist |
| `gz_ros2_control` Gazebo plugin | runs a **controller_manager** inside the simulation and connects it to the simulated joints |
| `controllers.yaml` | which **controllers** to load and how they are configured |
| `diff_drive_controller` | turns `cmd_vel` (body velocity) into wheel speeds, and wheel motion into **odometry** |
| `joint_state_broadcaster` | publishes `/joint_states`, so robot_state_publisher can compute TF |

On the real robot (Chapter 11) only the `<hardware>` plugin changes. The same controllers and the same
`cmd_vel` drive the real motors.

```academy:callout
kind: compare
title: ROS 1 → ROS 2
body: |
  ROS 1 used Gazebo Classic with `libgazebo_ros_diff_drive.so` (a Gazebo plugin doing the kinematics) or
  `gazebo_ros_control`. Gazebo Classic is end-of-life. ROS 2 Jazzy uses **Gazebo Harmonic** + **gz_ros2_control**,
  with the same `diff_drive_controller` you would run on hardware.
```

```academy:callout
kind: note
title: How the academy runs Gazebo
body: |
  Gazebo runs **headless** (`gz sim -s`): physics only, no window. The **Robot** tab draws the simulated
  robot from real TF, so what you see is what the simulation computed, not an animation. On Windows the academy
  also isolates your Gazebo instance (its own partition, localhost only) and fixes the plugin search path.
```
