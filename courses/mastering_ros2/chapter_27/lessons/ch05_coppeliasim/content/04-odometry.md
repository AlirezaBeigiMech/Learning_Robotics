## Odometry from the wheels

The bridge must report where the robot is. It may **not** read the simulator's true pose: a real robot has no
such thing. It has **wheel encoders**. Each step, `sysCall_sensing` already computes how far each wheel rolled,
`dl` and `dr`. **Forward kinematics** turns them into body motion:

```
ds   = (dl + dr) / 2            distance the centre moved
dyaw = (dr − dl) / L            how much the robot turned
```

**Dead reckoning** adds the motions up. The centre moved along the heading it had **halfway through** the step:

```
x   += ds · cos(yaw + dyaw/2)
y   += ds · sin(yaw + dyaw/2)
yaw  = wrap(yaw + dyaw)
v = ds / Δt      ω = dyaw / Δt
```

* **TODO 2**: create the `/odom` publisher (`nav_msgs/msg/Odometry`).
* **TODO 4**: the integration above.
* **TODO 5**: publish the odometry: frame `odom`, child `base_link`, the pose (yaw as a quaternion about z) **and**
  the twist (`linear.x = v`, `angular.z = ω`).
* **TODO 6**: `simROS2.sendTransform` the same pose as `odom → base_link`, with `z = 0.05` (base_link sits at axle
  height).

Rebuild, restart and drive again. Now the **Robot** tab (fixed frame `odom`) moves with the simulation and draws
the path. Compare `/odom` with `/ground_truth` in **Topics** after a few turns: they drift apart. The wheels slip a
little, especially when turning, and odometry cannot see slip. A real robot drifts the same way, which is why
Chapter 6 corrects odometry with a map.

**Check: Drive, turn and report odometry** drives the robot 4 s straight and 3 s on the spot. It measures the true
motion from `/ground_truth` and compares your `/odom` and TF with it.
