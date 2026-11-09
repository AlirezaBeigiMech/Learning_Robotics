## Odometry and TF

You wrote this in Lua for CoppeliaSim. Now write it in C++:

* **TODO 3**: in `sense()`, the dead-reckoning update from `dl`, `dr` and `dt` (`x_`, `y_`, `yaw_`, `v_`, `w_`).
* **TODO 4**: publish `nav_msgs::msg::Odometry` (frame `odom`, child `base_link`, pose and twist) and broadcast the
  same pose as `odom → base_link`, at `z = kWheelRadius`, with `tf_->sendTransform`.

Every stamp is the **simulated** time of the step (`stamp`). robot_state_publisher runs with `use_sim_time`, so the
TF tree is consistent.

After a rebuild and restart, drive in a circle. The **Robot** tab (fixed frame `odom`) shows the robot moving, and
**TF Tree** shows `odom → base_link → {wheels, casters, laser_link}`.

Webots' wheels hardly slip when driving straight, so odometry matches the truth almost exactly there. Turning on the
spot still costs a few degrees: a 2.5 cm wide wheel scrubs as it pivots. **Check: Drive, odometry, joint states and
clock** compares your odometry with the true motion. The truth comes from a **supervisor**, a privileged Webots
controller that the grader adds to a copy of your world and that can read any node's real pose.
