## Publish it with robot_state_publisher

Read `launch/display.launch.xml`. It is an **XML launch file**, the same idea as the book's ROS 1
`.launch` files, with ROS 2 substitutions:

| Piece | Meaning |
|---|---|
| `<node pkg="robot_state_publisher" exec="robot_state_publisher">` | start one node (ROS 1 used `type=`, ROS 2 uses `exec=`) |
| `$(find-pkg-share pan_tilt_description)` | the package's **installed** share folder |
| `$(command 'xacro …')` | run xacro now and use its output as the value |
| `<param name="robot_description" type="str" …/>` | a **parameter of this node** (ROS 2 has no global parameter server) |

`CMakeLists.txt` installs `urdf/` and `launch/` into `share/pan_tilt_description`, so **always build after
editing**.

1. **Build**.
2. **Run ▸ ros2 launch pan_tilt_description display.launch.xml**.
3. Open the **ROS Graph**: `/robot_state_publisher` publishes `/robot_description`, `/tf_static` and
   `/tf`, and subscribes to `/joint_states`.
4. Press **Verify**.

In the **TF Tree** tab you will see only `camera_link` under `tilt_link`. Fixed joints are published
once on `/tf_static`, but the moving joints have no TF yet. Why? Nobody has said what their angles are.

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
