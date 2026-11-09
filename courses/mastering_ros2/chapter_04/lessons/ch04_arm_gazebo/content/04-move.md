## Write `move_arm` (C++)

Open `src/move_arm.cpp`. The node sends **one** trajectory to `/arm_controller/joint_trajectory`:

```cpp
trajectory_msgs::msg::JointTrajectory traj;
traj.joint_names = joints_;
trajectory_msgs::msg::JointTrajectoryPoint point;
point.positions = positions_;                                        // 7 values from the parameter
point.time_from_start = rclcpp::Duration::from_seconds(duration_);   // arrive after `duration` s
traj.points.push_back(point);
pub_->publish(traj);
```

**Publish only once someone is listening.** A message published before the controller's subscription is
connected is simply lost. Poll from a 200 ms timer until `pub_->get_subscription_count() > 0`, then send.

Parameters: `positions` (7 angles, rad) and `duration` (s). Try a pose from the **Terminal**:

```
ros2 run arm_sim move_arm --ros-args -p "positions:=[0.8,0.6,0.0,0.9,0.0,0.5,0.0]" -p duration:=3.0
```

**Check: move_arm reaches its target** runs your node with the default pose and with a grader-chosen pose.
