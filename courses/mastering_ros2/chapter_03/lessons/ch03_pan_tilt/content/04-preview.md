## Inspect it in 3D

In the **Robot** tab (Preview mode):

* **drag** to orbit, **scroll** to zoom, **right-drag** to pan;
* move the **joint sliders**. In Preview the browser computes the kinematics from your file;
* toggle **Collision** to see the collision shapes (orange wireframe), and **Frames** to see every link
  frame (red = x, green = y, blue = z);
* **click a link** to inspect its geometry, mass and inertia, and the joint that holds it (origin, axis,
  limits).

Check that the tilt joint's axis really is y. With the pan at 0, tilting should pitch the head
forward and back, not sideways.

```academy:callout
kind: note
title: Preview vs. Live
body: |
  **Preview** is your file drawn by the browser. **Live** is what ROS actually publishes: the robot
  description and TF from a running robot_state_publisher. A robotics engineer trusts Live. You switch
  to it in the next steps.
```
