// Your first ROS 2 node, in C++.
//
// Specification (the grader checks this behaviour, not your exact code):
//   * node name : hello_node
//   * behaviour : every 0.5 s, log a heartbeat containing an increasing counter,
//                 e.g. "Hello ROS 2 #1", "Hello ROS 2 #2", ...
//   * it keeps running until it is stopped (it spins)

#include <chrono>
#include <memory>

#include "rclcpp/rclcpp.hpp"

using namespace std::chrono_literals;

class HelloNode : public rclcpp::Node
{
public:
  // TODO 1: give the node its name by passing "hello_node" to the rclcpp::Node constructor.
  HelloNode()
  : Node("change_me")
  {
    // TODO 2: create a wall timer that calls heartbeat() every 500 ms and keep it in timer_.
    //         (hint: create_wall_timer(<period>, <callback>); a lambda can call heartbeat())
  }

private:
  void heartbeat()
  {
    // TODO 3: increase count_ and log "Hello ROS 2 #<count>" with RCLCPP_INFO(get_logger(), ...).
  }

  rclcpp::TimerBase::SharedPtr timer_;
  int count_ = 0;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<HelloNode>();
  // TODO 4: hand control to the executor so the timer can fire (hint: rclcpp::spin).
  (void)node;
  rclcpp::shutdown();
  return 0;
}
