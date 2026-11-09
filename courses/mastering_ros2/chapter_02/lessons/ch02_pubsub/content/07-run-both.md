## Run both nodes

Build, then run **number_publisher** and **number_subscriber**. Each has its own output tab.
The subscriber should log `Received: …` about ten times per second.

In the **ROS Graph** you now have a complete data path:

```
/number_publisher ──▶ /numbers ──▶ /number_subscriber
```

Edges are coloured from **real QoS data**: green means compatible. Press **Verify** while both are
running.

Try starting the subscriber *before* the publisher. Nothing breaks. Discovery is dynamic, so either
side can come and go at any time. That is a property of ROS 2 you will rely on constantly.
