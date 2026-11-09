## Topics: named, typed data streams

A ROS 2 application is a set of **nodes**: small programs, each with one job. Nodes do not call
each other directly. A node that produces data **publishes** it on a **topic**. Any node that needs
the data **subscribes** to the same topic. The topic is defined by two things:

* a **name**, such as `/numbers`
* a **message type**, such as `std_msgs/msg/Int32`, a struct with one `int32 data` field

A publisher and a subscriber connect only when **both the name and the type match**. Even then,
their **Quality of Service (QoS)** policies must be compatible. You will break and repair that
last condition yourself later in this lesson.

```academy:pubsub-diagram
publishers: [number_publisher]
subscribers: [number_subscriber]
topic: /numbers
type: std_msgs/msg/Int32
```

### No master: discovery
ROS 1 needed a central `roscore` to introduce nodes to each other. ROS 2 has no master. Every node
is a DDS *participant* that announces its publishers and subscribers. Participants in the same
**domain** (`ROS_DOMAIN_ID`) discover each other and connect directly.

The academy gives you a private domain and limits discovery to your own computer
(`ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`). Your nodes therefore never interfere with anyone else's.

```academy:callout
kind: compare
title: ROS 1 → ROS 2
body: |
  ROS 1 used `ros::Rate` with `while (ros::ok()) { publish; spinOnce(); sleep(); }`.
  In ROS 2 you create a **wall timer**, and the **executor** inside `rclcpp::spin()` calls your callback at
  the right time. Timers, subscriptions, services and actions all run through the same executor.
```

Try the diagram above. Add a second subscriber, then switch the publisher's reliability to
`BEST_EFFORT` and see which connections survive. The diagram is a *concept model*. Later steps show
the **live** graph of your own running code in the *ROS Graph* tab.
