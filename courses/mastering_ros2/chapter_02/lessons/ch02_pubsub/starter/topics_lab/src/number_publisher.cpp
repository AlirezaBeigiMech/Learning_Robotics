// Number publisher — your first ROS 2 publisher (C++).
//
// Specification (the grader checks this behaviour, not your exact code):
//   * node name : number_publisher
//   * topic     : /numbers  (std_msgs/msg/Int32)
//   * rate      : 10 Hz  -> a wall timer with a 100 ms period
//   * values    : 0, 1, 2, 3, ...  (one more than the previous message)
//   * QoS       : queue depth 10 (the default profile: RELIABLE, VOLATILE)

#include <chrono>
#include <memory>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/int32.hpp"

using namespace std::chrono_literals;

class NumberPublisher : public rclcpp::Node
{
public:
  NumberPublisher()
  : Node("number_publisher")
  {
    // TODO 1: create a publisher for std_msgs::msg::Int32 on the topic "numbers" with a queue
    //         depth of 10, and keep it in publisher_.  (hint: create_publisher<MsgType>(topic, qos))

    // TODO 2: create a wall timer that calls publish_next() every 100 ms and keep it in timer_.
  }

private:
  void publish_next()
  {
    // TODO 3: fill a std_msgs::msg::Int32 with count_, publish it, log it with RCLCPP_INFO,
    //         then increase count_ by one.
  }

  rclcpp::Publisher<std_msgs::msg::Int32>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
  int count_ = 0;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<NumberPublisher>());  // the executor runs timers and callbacks from here
  rclcpp::shutdown();
  return 0;
}
