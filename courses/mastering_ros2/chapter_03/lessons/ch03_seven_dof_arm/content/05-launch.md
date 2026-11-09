## Publish and move it

**Build**, then **Run ▸ ros2 launch arm_description display.launch.xml**. In the Robot tab switch to
**Live** and enable **Publish /joint_states**.

There are only 8 sliders for 9 moving joints. `right_finger_joint` is a mimic, and robot_state_publisher
computes it from `left_finger_joint`, so publishing a value for it would be wrong.

Open the **TF Tree**. The chain from `base_link` down to `grasp_frame` is 9 frames deep. Press
**Verify** while publishing.

```academy:callout
kind: note
title: "The KDL warning in the launch output"
body: |
  robot_state_publisher prints *"The root link base_link has an inertia specified in the URDF, but KDL does not
  support a root link with an inertia."* KDL, the kinematics library it uses, ignores the root's inertia.
  That is harmless for TF. Physics simulators care, though, so in Chapter 4 you will add a massless root link
  (for example `world` or `base_footprint`) above `base_link`. The differential-drive robot already
  has one, so it does not show this warning.
```
