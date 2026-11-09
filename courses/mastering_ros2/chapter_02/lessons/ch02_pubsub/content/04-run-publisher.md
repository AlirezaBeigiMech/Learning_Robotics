## Run it and find it in the graph

1. **Build** (needed after every change: the installed copy is what runs).
2. **Run ▸ topics_lab/number_publisher.** A process tab opens and shows the node's own log lines.
3. Open the **ROS Graph** tab on the right. Within a couple of seconds you should see
   `/number_publisher → /numbers`.

The graph is not a drawing. A hidden introspection node in your domain asks the DDS layer which
participants, publishers and subscriptions exist, about once per second.

Then press **Verify** on this step. The academy checks the *live* graph to confirm your node is
publishing on `/numbers` right now.

You can also use the real CLI in the **Terminal** tab:

```
ros2 node list --no-daemon --spin-time 3
ros2 topic info /numbers --verbose --no-daemon --spin-time 3
```

```academy:callout
kind: note
title: Why --no-daemon?
body: |
  The ros2 CLI normally starts a background daemon that caches the graph. On Windows that daemon can
  outlive your command and hold its output pipes open. `--no-daemon` queries DDS directly.
  A fresh CLI node needs a moment to discover the others; `--spin-time 3` waits 3 s (measured on Windows:
  without it the node was found in 2 of 5 runs, with it in 5 of 5).
```
