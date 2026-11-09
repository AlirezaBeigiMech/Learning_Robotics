// Number subscriber — receives the numbers and reports them (C++).
//
// Specification:
//   * node name : number_subscriber
//   * topic     : /numbers  (std_msgs/msg/Int32), queue depth 10
//   * behaviour : for every message, log a line containing the received number,
//                 e.g.  "Received: 42"

#include <memory>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/int32.hpp"

class NumberSubscriber : public rclcpp::Node
{
public:
  NumberSubscriber()
  : Node("number_subscriber")
  {
    // TODO 1: subscribe to std_msgs::msg::Int32 on "numbers" (queue depth 10) with on_number as the
    //         callback, and keep the subscription in subscription_ (otherwise it is destroyed).
    //         (hint: create_subscription<MsgType>(topic, qos, callback); a lambda can call on_number)
  }

private:
  void on_number([[maybe_unused]] const std_msgs::msg::Int32 & msg)
  {
    // TODO 2: log the received value, e.g. RCLCPP_INFO(get_logger(), "Received: %d", msg.data);
  }

  rclcpp::Subscription<std_msgs::msg::Int32>::SharedPtr subscription_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<NumberSubscriber>());
  rclcpp::shutdown();
  return 0;
}
