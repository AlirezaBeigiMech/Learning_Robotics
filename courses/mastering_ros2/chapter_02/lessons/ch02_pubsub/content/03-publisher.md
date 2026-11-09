## Write the publisher

Open `src/number_publisher.cpp` and complete the three TODOs. The node must:

1. be called **`number_publisher`** (already done in the constructor's initialiser list);
2. publish `std_msgs/msg/Int32` on **`numbers`**. A name without a leading `/` is relative, so with no
   namespace it resolves to `/numbers`;
3. publish **10 times per second** using a wall timer;
4. send `0, 1, 2, …`, increasing by one each time.

The building blocks:

```cpp
publisher_ = create_publisher<std_msgs::msg::Int32>("numbers", 10);
timer_     = create_wall_timer(100ms, [this]() {publish_next();});

std_msgs::msg::Int32 msg;
msg.data = count_;
publisher_->publish(msg);
RCLCPP_INFO(get_logger(), "Publishing: %d", msg.data);
```

The `10` passed as QoS is shorthand for `rclcpp::QoS(10)`, the default profile: keep the last 10
messages, **RELIABLE** delivery, **VOLATILE** durability. Members such as `publisher_` and `timer_` must
live as long as the node. A local variable would be destroyed when the constructor returns, and the
timer would never fire.

When it compiles, press **Check: Publisher behaviour**. The grader builds a copy of your package in an
isolated sandbox, runs your node and measures:

* is the node and topic present with the right type?
* what is the real message rate?
* do the values count up without gaps?
* is the QoS RELIABLE?

It tests **behaviour**, not wording, so any correct implementation passes.
