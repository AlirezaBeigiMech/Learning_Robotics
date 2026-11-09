## Write `drive_forward` (C++)

Open `src/drive_forward.cpp`. The node must drive the robot **exactly `distance` metres** (default 1.0)
and then **stop**, using odometry as feedback:

```cpp
cmd_pub_ = create_publisher<geometry_msgs::msg::TwistStamped>("/diff_drive_controller/cmd_vel", 10);
odom_sub_ = create_subscription<nav_msgs::msg::Odometry>(
  "/diff_drive_controller/odom", 10, [this](const nav_msgs::msg::Odometry & msg) {on_odom(msg);});
```

Every odometry message is one step of a **control loop**:

1. remember the first position (`msg.pose.pose.position`);
2. compute the distance travelled with `std::hypot(dx, dy)`;
3. command `speed_` while short of the goal, then **zero**. Slowing down near the goal reduces overshoot.

Build, start the simulation, then **Run ▸ ros2 run diffbot_sim drive_forward** and watch the Robot tab.

The grader does not trust your odometry. **Check: drive_forward reaches 1 m** measures the distance with
Gazebo's ground truth (±10 %) and checks that the robot stays stopped afterwards.
