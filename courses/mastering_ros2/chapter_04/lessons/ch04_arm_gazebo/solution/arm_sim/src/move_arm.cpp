// Reference solution: send one joint trajectory to the arm controller.

#include <chrono>
#include <memory>
#include <string>
#include <vector>

#include "rclcpp/rclcpp.hpp"
#include "trajectory_msgs/msg/joint_trajectory.hpp"

using namespace std::chrono_literals;

class MoveArm : public rclcpp::Node
{
public:
  MoveArm()
  : Node("move_arm")
  {
    positions_ = declare_parameter<std::vector<double>>("positions", {0.0, 0.5, 0.0, 1.0, 0.0, 0.5, 0.0});
    duration_ = declare_parameter<double>("duration", 2.0);
    pub_ = create_publisher<trajectory_msgs::msg::JointTrajectory>("/arm_controller/joint_trajectory", 10);
    timer_ = create_wall_timer(200ms, [this]() {try_send();});
  }

private:
  void try_send()
  {
    if (sent_ || pub_->get_subscription_count() == 0) {
      return;
    }
    if (positions_.size() != joints_.size()) {
      RCLCPP_ERROR(get_logger(), "Expected %zu positions, got %zu", joints_.size(), positions_.size());
      sent_ = true;
      return;
    }
    trajectory_msgs::msg::JointTrajectory traj;
    traj.joint_names = joints_;
    trajectory_msgs::msg::JointTrajectoryPoint point;
    point.positions = positions_;
    point.time_from_start = rclcpp::Duration::from_seconds(duration_);
    traj.points.push_back(point);
    pub_->publish(traj);
    sent_ = true;
    RCLCPP_INFO(get_logger(), "Sent a trajectory reaching the target in %.1f s", duration_);
  }

  const std::vector<std::string> joints_{
    "shoulder_pan_joint", "shoulder_pitch_joint", "elbow_roll_joint", "elbow_pitch_joint",
    "wrist_roll_joint", "wrist_pitch_joint", "gripper_roll_joint"};
  std::vector<double> positions_;
  double duration_{2.0};
  bool sent_{false};
  rclcpp::Publisher<trajectory_msgs::msg::JointTrajectory>::SharedPtr pub_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<MoveArm>());
  rclcpp::shutdown();
  return 0;
}
