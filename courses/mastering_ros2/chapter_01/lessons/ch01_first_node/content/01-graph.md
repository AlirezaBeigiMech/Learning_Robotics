## The ROS 2 graph without a master

A running ROS 2 system is a **graph**. The vertices are **nodes**, which are processes or parts of
processes. The edges are the communication channels between them:

| Channel | Pattern | Typical use |
|---|---|---|
| **Topic** | many-to-many, asynchronous stream | sensor data, commands, state |
| **Service** | request → response | quick queries and configuration |
| **Action** | goal → feedback… → result, cancellable | long-running tasks like "move to pose" |
| **Parameter** | per-node typed settings | tuning, configuration |

```academy:pubsub-diagram
publishers: [camera_driver]
subscribers: [detector, recorder]
topic: /image
type: sensor_msgs/msg/Image
```

### Discovery replaces `roscore`
In ROS 1 every node registered with a central **master**. If the master died, no new connections
could be made. ROS 2 builds on **DDS**: each node announces itself and its endpoints, and peers that
share a **domain** (`ROS_DOMAIN_ID`, 0–232) find each other. There is no single point of failure,
and discovery is **dynamic**: nodes can join and leave at any time.

```academy:callout
kind: note
title: Your private domain
body: |
  The academy assigns you your own ROS_DOMAIN_ID and limits discovery to this computer, so the graph
  you see contains only your nodes.
```
