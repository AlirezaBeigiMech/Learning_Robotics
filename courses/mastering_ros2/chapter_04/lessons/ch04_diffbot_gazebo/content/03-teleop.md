## Drive it by hand

With the simulation running, open the **Robot** tab in **Live** mode. The view follows the `odom` frame,
so the robot moves across the grid as it drives, and its path is drawn as a trail. In the **Terminal**:

```
ros2 topic pub -r 10 /diff_drive_controller/cmd_vel geometry_msgs/msg/TwistStamped '{twist: {linear: {x: 0.2}, angular: {z: 0.4}}}'
```

The robot drives a circle. Stop with **Ctrl+C**. Within half a second it stops by itself: the controller's
`cmd_vel_timeout` is a safety feature.

Watch the **status line** in the Robot tab. **Sim time** advances, and the **real-time factor** (RTF) tells
you how fast the physics runs compared with the wall clock. Everything in the simulation runs on
simulation time (`use_sim_time`).

```academy:callout
kind: compare
title: ROS 1 → ROS 2
body: |
  In Jazzy, `diff_drive_controller` takes a **TwistStamped** on `~/cmd_vel` (ROS 1: a plain `Twist` on
  `/cmd_vel`). Tools like teleop_twist_keyboard can publish stamped twists.
```
