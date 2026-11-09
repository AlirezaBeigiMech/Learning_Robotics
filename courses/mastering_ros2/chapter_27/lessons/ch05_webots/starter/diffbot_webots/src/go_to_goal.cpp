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
    // TODO 6: cmd_pub_ = a geometry_msgs::msg::Twist publisher on "/cmd_vel" (depth 10), and odom_sub_ = a
    //         nav_msgs::msg::Odometry subscription on "/odom" (depth 10) whose callback calls on_odom(msg).
    RCLCPP_INFO(get_logger(), "Going to (%.2f, %.2f) in the odom frame", goal_x_, goal_y_);
  }

private:
  void on_odom(const nav_msgs::msg::Odometry & msg)
  {
    const auto & p = msg.pose.pose.position;
    const auto & q = msg.pose.pose.orientation;
    const double yaw = std::atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z));
    (void)p;
    (void)yaw;
    // TODO 7: a go-to-point controller, evaluated on every odometry message:
    //   * distance to the goal, and the heading error = direction to the goal − yaw, wrapped to [-pi, pi];
    //   * while farther than tolerance_: turn towards the goal (angular.z proportional to the heading error, limited
    //     to ±max_turn_) and drive forward proportionally to the distance (limited to max_speed_), scaled by
    //     max(0, cos(heading error)) so the robot does not drive away while it is still facing the wrong way;
    //   * once within tolerance_: set reached_, log "Goal reached" ONCE, and from then on command zero.
    // Publish a Twist on every message (zero when there is nothing to do).
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
