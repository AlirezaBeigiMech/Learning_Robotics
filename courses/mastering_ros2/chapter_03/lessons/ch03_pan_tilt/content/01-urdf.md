## A robot is a tree of rigid bodies

The **Unified Robot Description Format (URDF)** describes a robot's mechanical structure as XML:

* a **link** is a rigid body. It has a coordinate frame and, optionally, how it **looks** (`<visual>`),
  what it **collides** with (`<collision>`) and how it **moves under forces** (`<inertial>`);
* a **joint** connects a **parent** link to a **child** link and defines *where the child frame is*
  and *how it may move* relative to the parent.

Every link except one (the **root**) is the child of exactly one joint, so a URDF is always a **tree**.
URDF cannot describe closed kinematic loops.

| Joint type | Motion of the child | Typical use |
|---|---|---|
| `fixed` | none | sensors, tool frames, rigidly bolted parts |
| `revolute` | rotation about `<axis>`, between limits | arm joints, pan/tilt |
| `continuous` | unlimited rotation about `<axis>` | wheels |
| `prismatic` | translation along `<axis>`, between limits | grippers, linear stages |

### From model to TF
A URDF file is static data. To get live coordinate frames, ROS 2 runs **robot_state_publisher**:

```
URDF ──(parameter)──▶ robot_state_publisher ──▶ /tf_static  (fixed joints)
/joint_states ──────▶ robot_state_publisher ──▶ /tf         (moving joints)
                                            └─▶ /robot_description
```

```academy:callout
kind: compare
title: ROS 1 → ROS 2
body: |
  In ROS 1 the URDF lived on the global parameter server as `/robot_description`. ROS 2 has no global
  parameters: `robot_description` is a **parameter of robot_state_publisher**, which also republishes it
  on the **`/robot_description` topic** (latched with TRANSIENT_LOCAL durability) for tools like RViz.
```

In this lesson you build a pan-tilt unit with two revolute joints and one fixed camera frame, the
classic first URDF.
