## Commands to motors, with a time-out

This is the same job as the Lua bridge's `sysCall_actuation`, in C++:

* **TODO 1**: subscribe to `/cmd_vel` (`geometry_msgs::msg::Twist`). In the callback, store the message in `cmd_`
  and the **simulated** time it arrived, `wb_robot_get_time()`, in `last_cmd_time_`.
* **TODO 2**: in `actuate(t)`, run the inverse kinematics and command both motors with `wb_motor_set_velocity`.

There is one addition: a **command time-out**. If the node that sends `/cmd_vel` crashes while the robot is
moving, the last command would otherwise stay in force and the robot would drive on until it hits something. Real
drivers stop the robot when commands stop arriving (Chapter 4's `diff_drive_controller` has `cmd_vel_timeout`).
Here: if `t − last_cmd_time_ > kCmdTimeout` (0.5 s), command zero.

```academy:callout
kind: note
title: Why simulated time?
body: |
  The time-out is measured on the simulator's clock, like everything the driver does. If Webots runs slower than
  real time (a busy laptop), 0.5 s of simulated time is still 0.5 s from the robot's point of view.
```

**Build**, **Stop**, **Run** again. This step completes when `/webots_driver` subscribes to `/cmd_vel`. Then drive
from the **Terminal**:

```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}, angular: {z: 0.4}}"
```

In the **Robot** tab the wheels turn (`/joint_states`), but the robot stays put: nothing publishes
`odom → base_link` yet. Stop the publisher with Ctrl+C. The robot stops by itself half a second later: that's the
time-out at work.
