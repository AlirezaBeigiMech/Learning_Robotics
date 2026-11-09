## One controller, two simulators

Now the payoff. `src/go_to_goal.cpp` drives the robot to a point and stops. It knows nothing about Webots or
CoppeliaSim: it reads `/odom` and writes `/cmd_vel`, the contract both of your adapters implement.

* **TODO 6**: the `/cmd_vel` publisher and the `/odom` subscription.
* **TODO 7**: the controller. On every odometry message:

```
distance      = |goal − position|
heading_error = wrap(atan2(goal_y − y, goal_x − x) − yaw)
angular.z     = clamp(2.0 · heading_error, ±max_turn)
linear.x      = clamp(0.8 · distance, 0, max_speed) · max(0, cos(heading_error))
```

The `cos` factor makes the robot turn on the spot when the goal is behind it, and drive faster the better it is
aligned. Within `tolerance` it stops for good and logs `Goal reached`.

Try it in both simulators, with the same binary:

1. Run `ros2 launch diffbot_webots sim.launch.xml`, then **Run ▸ ros2 run diffbot_webots go_to_goal**.
2. **Stop** everything, run `ros2 launch diffbot_coppelia sim.launch.xml` (your previous lesson's bridge), then
   **Run ▸ ros2 run diffbot_webots go_to_goal** again.

**Check: One controller, two simulators** runs exactly that. Each simulator's ground truth must put the robot
within 18 cm of the goal. Your controller stops when the **odometry** says 5 cm, but the robot is really wherever
the drift has put it. Compare the two simulators: Webots typically ends 5–8 cm off, CoppeliaSim 10–13 cm, because
its wheels roll about 3 % short of what their encoders report (watch `/odom` against `/ground_truth`). A real robot's
tyres do the same. Odometry alone never gets you exactly there; Chapter 6 adds a map to correct it.
