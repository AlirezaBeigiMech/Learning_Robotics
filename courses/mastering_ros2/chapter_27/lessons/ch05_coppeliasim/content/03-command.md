## From `/cmd_vel` to the wheels

A differential-drive robot has two motors, but `/cmd_vel` describes the **body**: forward speed `v` and turn
rate `ω`. Turning one into the other is **inverse kinematics**. With wheel separation `L` and wheel radius `r`:

```
rim speed:     v_left  = v − ω·L/2          v_right = v + ω·L/2
wheel speed:   ω_left  = v_left / r         ω_right = v_right / r        (rad/s)
```

A positive `ω` turns the robot **left** (counter-clockwise seen from above, REP 103), so the right wheel must turn
faster.

In `coppeliasim/diffbot_bridge.lua`:

* **TODO 1**: in `sysCall_init`, subscribe to `/cmd_vel` and store the two numbers in `cmd`. simROS2 hands your
  callback the message as a Lua table that mirrors the ROS message: `msg.linear.x`, `msg.angular.z`.
* **TODO 3**: in `sysCall_actuation`, compute both wheel speeds and command them with
  `sim.setJointTargetVelocity(joint, rad_per_s)`. The wheels were switched to velocity control in `sysCall_init`.

Lua scripts are installed, so **Build** again, then **Stop** and **Run** the launch file. This step completes when
`/sim_ros2_interface` subscribes to `/cmd_vel` in the live graph. Then drive from the **Terminal**:

```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}, angular: {z: 0.5}}"
```

and watch `/ground_truth` in **Topics** change (Ctrl+C stops publishing; the robot stops when `/cmd_vel` says
zero). The Robot tab still does not move: there is no odometry yet.
