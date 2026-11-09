## Trajectories and position control

A manipulator is commanded by **joint trajectories**: a list of waypoints, each holding joint positions
and a time. The **joint_trajectory_controller** interpolates smoothly between them and drives each joint's
**position** command interface, the same way on a simulated or a real arm.

```
            ┌──────────── Gazebo (gz sim -s, headless physics) ─────────────┐
            │  robot model  ◀─ joint commands ──  gz_ros2_control plugin    │
            │  (from URDF)  ── joint states   ─▶  └─ controller_manager ───┼──▶ /joint_states, /odom, TF
            └───────────────────────────────────────────▲──────────────────┘
                                                        │ /cmd_vel, trajectories
                                              your C++ nodes
```

Two simulation details in `urdf/seven_dof_arm.urdf.xacro` (already done for you):

* **Anchoring:** a massless `world` link is fixed to `base_link`, so Gazebo bolts the arm to the ground.
  This also removes Chapter 3's *"root link has an inertia"* warning.
* **No mimic joint in simulation:** on Windows, gz_ros2_control (Jazzy) fails to start when a joint uses
  `<mimic>`. Both fingers are therefore real joints here, and the gripper controller commands both.

```academy:callout
kind: compare
title: ROS 1 → ROS 2
body: |
  ROS 1 used `position_controllers/JointTrajectoryController` through `gazebo_ros_control` and a
  `<transmission>` per joint. ROS 2 has no transmissions in this role: the `<ros2_control>` tag declares
  each joint's interfaces directly, and controllers say which interfaces they claim.
```
