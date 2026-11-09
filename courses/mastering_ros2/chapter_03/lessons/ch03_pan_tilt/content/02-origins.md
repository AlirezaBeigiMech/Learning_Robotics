## Origins: where frames and shapes sit

Every `<origin xyz="x y z" rpy="roll pitch yaw"/>` is a **rigid transform**. It holds a translation in
metres and a rotation in radians, written as roll about X, pitch about Y and yaw about Z. These are
**fixed axes**, applied in that order, so `R = Rz(yaw)·Ry(pitch)·Rx(roll)`.

There are two different kinds of `<origin>`, and mixing them up is the most common URDF bug:

| Where | Places what | Relative to |
|---|---|---|
| inside `<joint>` | the **child link's frame** | the parent link's frame |
| inside `<visual>`/`<collision>`/`<inertial>` | the **shape / centre of mass** | the link's own frame |

A cylinder is centred on its origin, with its axis along local z. A 0.30 m column that should *stand*
on its joint therefore needs `<origin xyz="0 0 0.15"/>` in its visual.

Play with a transform. The matrix is exactly what TF computes for one joint:

```academy:transform-playground
title: Child frame relative to parent
```

Stacking joints multiplies these matrices. The pose of `camera_link` in `base_link` is
`T(pan_joint) · R(pan) · T(tilt_joint) · R(tilt) · T(camera_joint)`. That is forward kinematics,
which robot_state_publisher computes for you.
