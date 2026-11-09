## Interfaces and controllers

**`urdf/arm.ros2_control.xacro`, TODO 1–2:** the `position_joint` macro writes one joint entry. Add all
seven arm joints and **both** finger joints, then the `<gazebo>` plugin element, as for the diffbot but
pointing at `$(find arm_sim)/config/controllers.yaml`.

**`config/controllers.yaml`, TODO 3–4:**

| Controller | Joints | Command interface |
|---|---|---|
| `arm_controller` | `shoulder_pan_joint`, `shoulder_pitch_joint`, `elbow_roll_joint`, `elbow_pitch_joint`, `wrist_roll_joint`, `wrist_pitch_joint`, `gripper_roll_joint` | position |
| `gripper_controller` | `left_finger_joint`, `right_finger_joint` | position |

Build, **Run ▸ ros2 launch arm_sim sim.launch.xml**, and check the **Controllers** tab: three controllers
**active**, each claiming its joints' `…/position` interfaces. Then **Verify**.

Try it from the **Terminal**:

```
ros2 topic pub --once /gripper_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory '{joint_names: [left_finger_joint, right_finger_joint], points: [{positions: [0.03, 0.03], time_from_start: {sec: 1}}]}'
```

```academy:callout
kind: note
title: "Why controllers.yaml also configures gz_ros_control"
body: |
  gz_ros2_control turns *position* commands into joint velocities through a proportional gain. With the
  default gain (0.1), a finger that has to open **upward against gravity** never leaves its joint limit:
  in some arm poses one finger opens and the other stays shut. The provided
  `gz_ros_control: position_proportional_gain: 2.0` fixes this. It was found by measuring both fingers
  in a gravity-adverse pose. This kind of tuning is part of every simulation; on real hardware the motor
  drivers do it.
```
