// go_to_goal: drive the robot to a point given in the odometry frame, then stop.
//
// It uses ONLY the simulator-adapter contract (/odom in, /cmd_vel out), so the very same binary drives the robot
// in Webots (through webots_driver) and in CoppeliaSim (through diffbot_bridge.lua), or a real robot.
//
// Parameters: goal_x, goal_y (m, in the odom frame; default 1.2, -0.6), tolerance (m, 0.05),
//             max_speed (m/s, 0.25), max_turn (rad/s, 1.0).

#include <algorithm>
#include <cmath>
#include <memory>

#include "geometry_msgs/msg/twist.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "rclcpp/rclcpp.hpp"

class GoToGoal : public rclcpp::Node
{
public:
  GoToGoal()
  : Node("go_to_goal")
  {
    goal_x_ = declare_parameter<double>("goal_x", 1.2);
    goal_y_ = declare_parameter<double>("goal_y", -0.6);
    tolerance_ = declare_parameter<double>("tolerance", 0.05);
    max_speed_ = declare_parameter<double>("max_speed", 0.25);
    max_turn_ = declare_parameter<double>("max_turn", 1.0);
    cmd_pub_ = create_publisher<geometry_msgs::msg::Twist>("/cmd_vel", 10);
    odom_sub_ = create_subscription<nav_msgs::msg::Odometry>(
      "/odom", 10, [this](const nav_msgs::msg::Odometry & msg) {on_odom(msg);});
    RCLCPP_INFO(get_logger(), "Going to (%.2f, %.2f) in the odom frame", goal_x_, goal_y_);
  }

private:
  void on_odom(const nav_msgs::msg::Odometry & msg)
  {
    const auto & p = msg.pose.pose.position;
    const auto & q = msg.pose.pose.orientation;
    const double yaw = std::atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z));
    const double dx = goal_x_ - p.x, dy = goal_y_ - p.y;
    const double distance = std::hypot(dx, dy);

    geometry_msgs::msg::Twist cmd;  // zero unless we still have to move
    if (distance > tolerance_ && !reached_) {
      double heading_error = std::atan2(dy, dx) - yaw;
      heading_error = std::atan2(std::sin(heading_error), std::cos(heading_error));
      // turn towards the goal; drive forward only as far as we are already facing it
      cmd.angular.z = std::clamp(2.0 * heading_error, -max_turn_, max_turn_);
      cmd.linear.x = std::clamp(0.8 * distance, 0.0, max_speed_) * std::max(0.0, std::cos(heading_error));
    } else if (!reached_) {
      reached_ = true;
      RCLCPP_INFO(get_logger(), "Goal reached: (%.3f, %.3f), %.3f m from the goal", p.x, p.y, distance);
    }
    cmd_pub_->publish(cmd);
  }

  double goal_x_{1.2}, goal_y_{-0.6}, tolerance_{0.05}, max_speed_{0.25}, max_turn_{1.0};
  bool reached_{false};
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_pub_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<GoToGoal>());
  rclcpp::shutdown();
  return 0;
}
