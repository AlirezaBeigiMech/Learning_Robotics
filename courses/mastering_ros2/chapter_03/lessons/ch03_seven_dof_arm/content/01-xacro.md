## Why xacro

The arm has 7 joints, 11 links and a gripper. Written as raw URDF, every link repeats the same
`<visual>`/`<collision>`/`<inertial>` block with slightly different numbers. That copy-paste is where
bugs come from. **xacro** (XML macros) is a preprocessor that turns a short description into a full
URDF:

| Feature | Example |
|---|---|
| property | `<xacro:property name="effort" value="30"/>` … `effort="${effort}"` |
| math | `${m * (3*r*r + h*h) / 12}`, `${pi/2}` |
| macro | `<xacro:macro name="wheel" params="side y_sign"> … </xacro:macro>` |
| block parameter | `params="m *origin"` … `<xacro:insert_block name="origin"/>` |
| include | `<xacro:include filename="inertial.xacro"/>` |
| condition | `<xacro:if value="${side == 'right'}"> … </xacro:if>` |

Xacro runs **before** ROS sees the model. The launch file calls `xacro` and passes the generated URDF
to robot_state_publisher. The Robot tab's preview runs the same tool, so what you see is what ROS gets.

```academy:callout
kind: compare
title: ROS 1 → ROS 2
body: |
  `xacro --inorder` is gone (in-order processing is now the default). `$(find pkg)` still works and
  resolves through the ament index of your **installed** workspace.
```
