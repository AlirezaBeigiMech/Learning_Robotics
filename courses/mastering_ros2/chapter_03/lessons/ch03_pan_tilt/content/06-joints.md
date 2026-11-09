## Drive the joints through /joint_states

robot_state_publisher needs joint **positions** to compute TF for moving joints. On a real robot they
come from encoders, via a driver or ros2_control. Here you provide them yourself:

1. In the **Robot** tab switch the source to **Live**. The model now comes from `/robot_description`,
   and every link is placed from **TF**, exactly as RViz does it.
2. Enable **Publish /joint_states**. A node named `/academy_joint_gui` appears in the ROS Graph,
   publishing `sensor_msgs/msg/JointState` at 10 Hz. It does the same job as `joint_state_publisher_gui`.
3. Move the sliders. The browser sends values to that node, the node publishes them,
   robot_state_publisher recomputes TF, and the 3D view follows TF.

Open the **TF Tree** tab. `pan_link` and `tilt_link` are now dynamic frames updating at about 10 Hz.
Press **Verify** while the sliders are publishing.

```academy:callout
kind: warning
title: Two publishers, one topic
body: |
  If two nodes publish /joint_states with different values, the robot flickers between them. When you
  later run a real driver or a simulator, turn the sliders' publishing off.
```
