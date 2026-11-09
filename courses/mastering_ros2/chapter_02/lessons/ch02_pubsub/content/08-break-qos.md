## Debugging lab: break the link on purpose

Now introduce a **controlled mistake**, a very common real-world ROS 2 bug.

In `number_publisher.cpp`, change the publisher to use **best-effort** delivery:

```cpp
publisher_ = create_publisher<std_msgs::msg::Int32>("numbers", rclcpp::QoS(10).best_effort());
```

Leave the subscriber unchanged: it still asks for the default **RELIABLE** profile. Build, run both
nodes, and observe:

1. **Symptom:** the subscriber logs nothing, yet both nodes are running and the topic name and type match.
2. **Telemetry:** in the ROS Graph, the `/numbers → /number_subscriber` edge turns **red**. Click it
   to see the reason reported by the QoS compatibility check.
3. **Logs:** the subscriber's output shows a warning that a publisher was discovered *offering
   incompatible QoS*, naming the `RELIABILITY` policy.

```academy:qos-matrix
highlight: {publisher: best_effort, subscriber: reliable}
```

Press **Verify** while the mismatch is live. The academy confirms from the real graph that you
reproduced the fault.
