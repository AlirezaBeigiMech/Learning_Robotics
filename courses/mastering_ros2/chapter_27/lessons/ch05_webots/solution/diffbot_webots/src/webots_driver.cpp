// webots_driver: the Webots side of the simulator-adapter contract, written against the Webots C API.
//
// Webots runs the physics; this node is the robot's "<extern>" controller. Every call to wb_robot_step()
// advances the simulation by one basic time step (16 ms), and between two steps the node:
//   in : /cmd_vel       geometry_msgs/msg/Twist     -> wheel motor speeds (stop if no command for 0.5 s)
//   out: /clock         rosgraph_msgs/msg/Clock     simulated time: all stamps below use it
//   out: /joint_states  sensor_msgs/msg/JointState  wheel encoder angles (robot_state_publisher -> wheel TF)
//   out: /odom + /tf    nav_msgs/msg/Odometry       dead reckoning from the encoders, odom -> base_link
//   out: /scan          sensor_msgs/msg/LaserScan   the lidar, in ROS angle order (counter-clockwise)

#include <webots/lidar.h>
#include <webots/motor.h>
#include <webots/position_sensor.h>
#include <webots/robot.h>

#include <algorithm>
#include <cmath>
#include <memory>

#include "geometry_msgs/msg/transform_stamped.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rosgraph_msgs/msg/clock.hpp"
#include "sensor_msgs/msg/joint_state.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"
#include "tf2_ros/transform_broadcaster.h"

constexpr double kWheelRadius = 0.05;     // m
constexpr double kWheelSeparation = 0.32; // m
constexpr double kCmdTimeout = 0.5;       // s of simulated time without /cmd_vel -> stop

class WebotsDriver : public rclcpp::Node
{
public:
  WebotsDriver()
  : Node("webots_driver")
  {
    step_ms_ = static_cast<int>(wb_robot_get_basic_time_step());
    left_motor_ = wb_robot_get_device("left_wheel_motor");
    right_motor_ = wb_robot_get_device("right_wheel_motor");
    left_encoder_ = wb_robot_get_device("left_wheel_sensor");
    right_encoder_ = wb_robot_get_device("right_wheel_sensor");
    lidar_ = wb_robot_get_device("laser");
    // velocity control: an infinite target position, then a speed
    for (WbDeviceTag m : {left_motor_, right_motor_}) {
      wb_motor_set_position(m, INFINITY);
      wb_motor_set_velocity(m, 0.0);
    }
    wb_position_sensor_enable(left_encoder_, step_ms_);
    wb_position_sensor_enable(right_encoder_, step_ms_);
    wb_lidar_enable(lidar_, step_ms_);

    clock_pub_ = create_publisher<rosgraph_msgs::msg::Clock>("/clock", 10);
    joint_pub_ = create_publisher<sensor_msgs::msg::JointState>("/joint_states", 10);
    odom_pub_ = create_publisher<nav_msgs::msg::Odometry>("/odom", 10);
    scan_pub_ = create_publisher<sensor_msgs::msg::LaserScan>("/scan", rclcpp::SensorDataQoS());
    tf_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);
    cmd_sub_ = create_subscription<geometry_msgs::msg::Twist>(
      "/cmd_vel", 10, [this](const geometry_msgs::msg::Twist & msg) {
        cmd_ = msg;
        last_cmd_time_ = wb_robot_get_time();
      });
    RCLCPP_INFO(get_logger(), "connected to Webots robot '%s', time step %d ms", wb_robot_get_name(), step_ms_);
  }

  // One simulation step. Returns false when Webots quits or resets the controller.
  bool step()
  {
    if (wb_robot_step(step_ms_) == -1) {
      return false;
    }
    const double t = wb_robot_get_time();
    const rclcpp::Time stamp(static_cast<int64_t>(std::llround(t * 1e9)));
    rosgraph_msgs::msg::Clock clock;
    clock.clock = stamp;
    clock_pub_->publish(clock);

    actuate(t);
    sense(t, stamp);
    publish_scan(stamp);
    return true;
  }

private:
  void actuate(double t)
  {
    double v = cmd_.linear.x, w = cmd_.angular.z;
    if (t - last_cmd_time_ > kCmdTimeout) {  // the commanding node stopped or crashed: do not drive on blindly
      v = w = 0.0;
    }
    // inverse kinematics: body velocity -> wheel angular speeds (rad/s)
    wb_motor_set_velocity(left_motor_, (v - w * kWheelSeparation / 2) / kWheelRadius);
    wb_motor_set_velocity(right_motor_, (v + w * kWheelSeparation / 2) / kWheelRadius);
  }

  void sense(double t, const rclcpp::Time & stamp)
  {
    const double ql = wb_position_sensor_get_value(left_encoder_);
    const double qr = wb_position_sensor_get_value(right_encoder_);
    if (std::isnan(ql) || std::isnan(qr)) {
      return;  // encoders deliver their first value one step after being enabled
    }
    double vl = 0.0, vr = 0.0;
    if (have_last_ && t > last_t_) {
      const double dt = t - last_t_;
      const double dl = (ql - last_ql_) * kWheelRadius, dr = (qr - last_qr_) * kWheelRadius;
      const double ds = (dl + dr) / 2, dyaw = (dr - dl) / kWheelSeparation;
      x_ += ds * std::cos(yaw_ + dyaw / 2);
      y_ += ds * std::sin(yaw_ + dyaw / 2);
      yaw_ = std::atan2(std::sin(yaw_ + dyaw), std::cos(yaw_ + dyaw));
      v_ = ds / dt;
      w_ = dyaw / dt;
      vl = (ql - last_ql_) / dt;
      vr = (qr - last_qr_) / dt;
    }
    last_ql_ = ql;
    last_qr_ = qr;
    last_t_ = t;
    have_last_ = true;

    sensor_msgs::msg::JointState js;
    js.header.stamp = stamp;
    js.name = {"left_wheel_joint", "right_wheel_joint"};
    js.position = {ql, qr};
    js.velocity = {vl, vr};
    joint_pub_->publish(js);

    nav_msgs::msg::Odometry odom;
    odom.header.stamp = stamp;
    odom.header.frame_id = "odom";
    odom.child_frame_id = "base_link";
    odom.pose.pose.position.x = x_;
    odom.pose.pose.position.y = y_;
    odom.pose.pose.orientation.z = std::sin(yaw_ / 2);
    odom.pose.pose.orientation.w = std::cos(yaw_ / 2);
    odom.twist.twist.linear.x = v_;
    odom.twist.twist.angular.z = w_;
    odom_pub_->publish(odom);

    geometry_msgs::msg::TransformStamped tf;
    tf.header = odom.header;
    tf.child_frame_id = "base_link";
    tf.transform.translation.x = x_;
    tf.transform.translation.y = y_;
    tf.transform.translation.z = kWheelRadius;  // base_link is at axle height
    tf.transform.rotation = odom.pose.pose.orientation;
    tf_->sendTransform(tf);
  }

  void publish_scan(const rclcpp::Time & stamp)
  {
    const float * image = wb_lidar_get_range_image(lidar_);
    const int n = wb_lidar_get_horizontal_resolution(lidar_);
    if (image == nullptr || n <= 0) {
      return;
    }
    const double fov = wb_lidar_get_fov(lidar_);
    sensor_msgs::msg::LaserScan scan;
    scan.header.stamp = stamp;
    scan.header.frame_id = "laser_link";
    // Webots orders the range image from LEFT to RIGHT (clockwise seen from above, starting at +fov/2);
    // ROS scans go counter-clockwise from angle_min. Same beams, reversed order.
    scan.angle_increment = fov / n;
    scan.angle_min = -fov / 2 + scan.angle_increment / 2;
    scan.angle_max = scan.angle_min + (n - 1) * scan.angle_increment;
    scan.range_min = static_cast<float>(wb_lidar_get_min_range(lidar_));
    scan.range_max = static_cast<float>(wb_lidar_get_max_range(lidar_));
    scan.scan_time = static_cast<float>(step_ms_ / 1000.0);
    scan.ranges.assign(image, image + n);
    std::reverse(scan.ranges.begin(), scan.ranges.end());
    scan_pub_->publish(scan);
  }

  int step_ms_{16};
  WbDeviceTag left_motor_{0}, right_motor_{0}, left_encoder_{0}, right_encoder_{0}, lidar_{0};
  geometry_msgs::msg::Twist cmd_;
  double last_cmd_time_{-1e9};
  bool have_last_{false};
  double last_ql_{0.0}, last_qr_{0.0}, last_t_{0.0};
  double x_{0.0}, y_{0.0}, yaw_{0.0}, v_{0.0}, w_{0.0};
  rclcpp::Publisher<rosgraph_msgs::msg::Clock>::SharedPtr clock_pub_;
  rclcpp::Publisher<sensor_msgs::msg::JointState>::SharedPtr joint_pub_;
  rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr odom_pub_;
  rclcpp::Publisher<sensor_msgs::msg::LaserScan>::SharedPtr scan_pub_;
  std::unique_ptr<tf2_ros::TransformBroadcaster> tf_;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr cmd_sub_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  wb_robot_init();  // connects to Webots (WEBOTS_CONTROLLER_URL); waits until the simulation is ready
  auto node = std::make_shared<WebotsDriver>();
  // Webots sets the pace: one step, then handle whatever ROS messages arrived meanwhile.
  while (rclcpp::ok() && node->step()) {
    rclcpp::spin_some(node);
  }
  wb_robot_cleanup();
  rclcpp::shutdown();
  return 0;
}
