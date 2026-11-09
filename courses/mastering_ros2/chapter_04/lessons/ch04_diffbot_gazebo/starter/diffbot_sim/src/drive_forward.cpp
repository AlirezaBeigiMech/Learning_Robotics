// drive_forward: drive the simulated robot forward a given distance using ODOMETRY feedback, then stop.
//
// Specification (checked by the grader against Gazebo's ground truth):
//   * parameter "distance" (m, default 1.0) and "speed" (m/s, default 0.2)
//   * publishes geometry_msgs/msg/TwistStamped on /diff_drive_controller/cmd_vel
//   * subscribes nav_msgs/msg/Odometry on /diff_drive_controller/odom
//   * remembers the first odometry position, drives until it has travelled `distance`, then commands
//     zero velocity and keeps the robot stopped.

#include <cmath>
#include <memory>

#include "geometry_msgs/msg/twist_stamped.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "rclcpp/rclcpp.hpp"

class DriveForward : public rclcpp::Node
{
public:
  DriveForward()
  : Node("drive_forward")
  {
    distance_ = declare_parameter<double>("distance", 1.0);
    speed_ = declare_parameter<double>("speed", 0.2);

    // TODO 1: create cmd_pub_, a TwistStamped publisher on "/diff_drive_controller/cmd_vel" (depth 10).

    // TODO 2: create odom_sub_, an Odometry subscription on "/diff_drive_controller/odom" (depth 10)
    //         whose callback calls on_odom(msg).
  }

private:
  void on_odom([[maybe_unused]] const nav_msgs::msg::Odometry & msg)
  {
    // TODO 3: on the first message, store the start position (msg.pose.pose.position) in start_x_/start_y_.
    // TODO 4: compute the distance travelled from the start (std::hypot).
    // TODO 5: publish a TwistStamped: linear.x = speed_ while travelled < distance_, else 0
    //         (log once when the goal is reached). Slowing down near the goal reduces overshoot.
  }

  double distance_{1.0};
  double speed_{0.2};
  bool have_start_{false};
  bool reached_{false};
  double start_x_{0.0};
  double start_y_{0.0};
  rclcpp::Publisher<geometry_msgs::msg::TwistStamped>::SharedPtr cmd_pub_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<DriveForward>());
  rclcpp::shutdown();
  return 0;
}
