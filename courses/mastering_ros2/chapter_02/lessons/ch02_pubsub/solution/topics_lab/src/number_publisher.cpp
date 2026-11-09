// Reference solution: number publisher (10 Hz, std_msgs/Int32 on /numbers).

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
    publisher_ = create_publisher<std_msgs::msg::Int32>("numbers", 10);
    timer_ = create_wall_timer(100ms, [this]() {publish_next();});
  }

private:
  void publish_next()
  {
    std_msgs::msg::Int32 msg;
    msg.data = count_;
    publisher_->publish(msg);
    RCLCPP_INFO(get_logger(), "Publishing: %d", msg.data);
    ++count_;
  }

  rclcpp::Publisher<std_msgs::msg::Int32>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
  int count_ = 0;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<NumberPublisher>());
  rclcpp::shutdown();
  return 0;
}
