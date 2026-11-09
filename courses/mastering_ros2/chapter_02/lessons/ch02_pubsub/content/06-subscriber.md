## Write the subscriber

Open `src/number_subscriber.cpp`. A subscription needs a message type, a topic, a QoS and a callback:

```cpp
subscription_ = create_subscription<std_msgs::msg::Int32>(
  "numbers", 10, [this](const std_msgs::msg::Int32 & msg) {on_number(msg);});
```

and the callback that receives each message:

```cpp
void on_number(const std_msgs::msg::Int32 & msg)
{
  RCLCPP_INFO(get_logger(), "Received: %d", msg.data);
}
```

Why store the result in `subscription_`? `create_subscription` returns a `SharedPtr`. If nobody keeps it,
the subscription is destroyed at the end of the constructor, and your callback silently never runs.

**Check: Subscriber behaviour** starts only your subscriber. The grader then publishes **numbers you
cannot predict** and checks that every one of them appears in your node's log.
