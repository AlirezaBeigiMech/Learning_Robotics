// Reference solution: first ROS 2 node with a timer heartbeat.

#include <chrono>
#include <memory>

#include "rclcpp/rclcpp.hpp"

using namespace std::chrono_literals;

class HelloNode : public rclcpp::Node
{
public:
  HelloNode()
  : Node("hello_node")
  {
    timer_ = create_wall_timer(500ms, [this]() {heartbeat();});
  }

private:
  void heartbeat()
  {
    ++count_;
    RCLCPP_INFO(get_logger(), "Hello ROS 2 #%d", count_);
  }

  rclcpp::TimerBase::SharedPtr timer_;
  int count_ = 0;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<HelloNode>());
  rclcpp::shutdown();
  return 0;
}
