## Run it and see it in the graph

**Build**, then **Run ▸ first_node_lab/hello_node**. Open the **ROS Graph** tab: `/hello_node`
appears within a couple of seconds. It has no topics of its own, but every node also publishes on
`/rosout` (logging) and `/parameter_events`. Toggle *show system topics* to see them.

Press **Verify** while it runs. The check reads the live graph.

In the **Terminal** you can confirm with the real CLI:

```
ros2 node list --no-daemon --spin-time 3
ros2 node info /hello_node --no-daemon --spin-time 3
```

Stop the node and watch it leave the graph.
