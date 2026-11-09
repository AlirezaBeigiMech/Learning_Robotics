// Reference solution: number subscriber.

#include <memory>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/int32.hpp"

class NumberSubscriber : public rclcpp::Node
{
public:
  NumberSubscriber()
  : Node("number_subscriber")
  {
    subscription_ = create_subscription<std_msgs::msg::Int32>(
      "numbers", 10, [this](const std_msgs::msg::Int32 & msg) {on_number(msg);});
  }

private:
  void on_number(const std_msgs::msg::Int32 & msg)
  {
    RCLCPP_INFO(get_logger(), "Received: %d", msg.data);
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
