// move_arm: send ONE joint trajectory to the arm controller, so the simulated arm moves to a target pose.
//
// Specification (checked by the grader on the simulated joints):
//   * parameter "positions": 7 target joint angles (rad), shoulder_pan ... gripper_roll
//                            (default: [0.0, 0.5, 0.0, 1.0, 0.0, 0.5, 0.0])
//   * parameter "duration" : seconds to reach the target (default 2.0)
//   * publishes trajectory_msgs/msg/JointTrajectory on /arm_controller/joint_trajectory
//   * waits until the controller is subscribed before publishing (otherwise the message is lost)

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

    // TODO 1: create pub_, a JointTrajectory publisher on "/arm_controller/joint_trajectory" (depth 10).

    // TODO 2: create a 200 ms wall timer (timer_) that calls try_send().
  }

private:
  void try_send()
  {
    // TODO 3: if already sent, or nobody is subscribed yet (pub_->get_subscription_count() == 0), return.
    // TODO 4: build a JointTrajectory: joint_names = the seven joints below, ONE point whose positions are
    //         positions_ and whose time_from_start is duration_ (rclcpp::Duration::from_seconds(...)).
    // TODO 5: publish it, log it, and remember that it was sent.
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
