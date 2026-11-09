// Reference solution: drive a given distance with odometry feedback, then hold still.

#include <algorithm>
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
    cmd_pub_ = create_publisher<geometry_msgs::msg::TwistStamped>("/diff_drive_controller/cmd_vel", 10);
    odom_sub_ = create_subscription<nav_msgs::msg::Odometry>(
      "/diff_drive_controller/odom", 10, [this](const nav_msgs::msg::Odometry & msg) {on_odom(msg);});
  }

private:
  void on_odom(const nav_msgs::msg::Odometry & msg)
  {
    const auto & p = msg.pose.pose.position;
    if (!have_start_) {
      start_x_ = p.x;
      start_y_ = p.y;
      have_start_ = true;
      RCLCPP_INFO(get_logger(), "Driving %.2f m at %.2f m/s", distance_, speed_);
    }
    const double travelled = std::hypot(p.x - start_x_, p.y - start_y_);
    const double remaining = distance_ - travelled;

    geometry_msgs::msg::TwistStamped cmd;
    cmd.header.stamp = now();
    if (remaining > 0.005 && !reached_) {
      cmd.twist.linear.x = std::min(speed_, 0.02 + 0.5 * remaining);  // slow down near the goal
    } else if (!reached_) {
      reached_ = true;
      RCLCPP_INFO(get_logger(), "Goal reached: travelled %.3f m", travelled);
    }
    cmd_pub_->publish(cmd);
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
