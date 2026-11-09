## Write the arm

Open `urdf/seven_dof_arm.urdf.xacro`. The base, the `cylinder_segment` macro and the first segment
(`shoulder_pan`) are done. Every joint sits at the top of the previous link, and every link extends up
its own z axis.

**TODO 1:** write the `box_segment` macro. **TODO 2:** add the six remaining segments:

| Segment (→ `<name>_joint`, `<name>_link`) | Shape | Size (m) | joint_z | Axis | Lower, upper | Mass | Colour |
|---|---|---|---|---|---|---|---|
| shoulder_pan *(given)* | cylinder | r 0.04, h 0.08 | 0.05 | 0 0 1 | −2.6, 2.6 | 0.5 | blue |
| shoulder_pitch | box | 0.04 × 0.04 × 0.14 | 0.08 | 0 1 0 | −1.2, 1.9 | 0.4 | grey |
| elbow_roll | cylinder | r 0.02, h 0.06 | 0.14 | 0 0 1 | −2.6, 2.6 | 0.2 | blue |
| elbow_pitch | box | 0.04 × 0.04 × 0.22 | 0.06 | 0 1 0 | −1.6, 1.9 | 0.4 | grey |
| wrist_roll | cylinder | r 0.02, h 0.04 | 0.22 | 0 0 1 | −2.6, 2.6 | 0.1 | blue |
| wrist_pitch | box | 0.04 × 0.04 × 0.06 | 0.04 | 0 1 0 | −1.6, 1.9 | 0.15 | grey |
| gripper_roll | cylinder | r 0.04, h 0.02 | 0.06 | 0 0 1 | −2.6, 2.6 | 0.1 | blue |

All revolute joints use effort 30 and velocity 1.0 (the `effort`/`velocity` properties).

**TODO 3, gripper:** two prismatic fingers on `gripper_roll_link`. The left finger is at
(0, 0.01, 0.02) with axis (0, 1, 0). The right finger is at (0, −0.01, 0.02) with axis (0, −1, 0) and
**mimics** `left_finger_joint`. Both have limits 0 … 0.03 m, effort 10, velocity 0.5, and are orange
0.01 × 0.01 × 0.08 boxes standing on the joint, mass 0.02 kg.

**TODO 4:** `grasp_frame`, fixed 0.10 m above `gripper_roll_link`. With all joints at zero it should
sit 0.75 m above the base.

Watch the **Robot** tab preview as you add segments. The arm grows with every save, or even before
you save.
