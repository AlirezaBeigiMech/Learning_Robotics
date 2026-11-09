## Write `hello_node`

Open `src/hello_node.cpp` and complete the TODOs:

1. name the node **`hello_node`**, the string passed to `rclcpp::Node`;
2. create a **wall timer** with a **500 ms** period;
3. in the callback, increase a counter and **log** `Hello ROS 2 #<n>`;
4. keep the node alive with **`rclcpp::spin(node)`**.

The building blocks:

```cpp
timer_ = create_wall_timer(500ms, [this]() {heartbeat();});   // needs: using namespace std::chrono_literals;
RCLCPP_INFO(get_logger(), "Hello ROS 2 #%d", count_);       // printf-style logging macro
```

Then press **Build**. Compiler errors appear in the Output panel and are underlined in the editor. Then press
**Check: Node behaviour**. The grader compiles your package in an isolated sandbox, starts your executable,
watches the ROS graph for `/hello_node`, and reads its heartbeat.

```academy:callout
kind: compare
title: ROS 1 → ROS 2
body: |
  ROS 1 C++ nodes used `ros::NodeHandle` and a `while (ros::ok())` loop with `ros::Rate`. In ROS 2 a node
  *is* an object (`class HelloNode : public rclcpp::Node`), and periodic work is a timer callback run by the
  executor inside `rclcpp::spin()`.
```
