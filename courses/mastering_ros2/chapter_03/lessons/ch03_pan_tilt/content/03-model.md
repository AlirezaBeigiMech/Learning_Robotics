## Complete the pan-tilt URDF

Open `urdf/pan_tilt.urdf`. `base_link` and `pan_joint` are done. Write the rest from this specification:

| Element | Type | Parent → child | Joint origin xyz | Axis | Limits (lower, upper, effort, velocity) |
|---|---|---|---|---|---|
| `pan_joint` | revolute | base_link → pan_link | 0 0 0.02 | 0 0 1 | −2.6, 2.6, 5, 1.5 *(given)* |
| `tilt_joint` | revolute | pan_link → tilt_link | 0 0 0.30 | 0 1 0 | −1.2, 1.2, 5, 1.5 |
| `camera_joint` | fixed | tilt_link → camera_link | 0.125 0 0.03 | – | – |

| Link | Shape (visual = collision) | Shape origin xyz | Colour | Mass | ixx, iyy, izz |
|---|---|---|---|---|---|
| `pan_link` | cylinder r 0.03, length 0.30 | 0 0 0.15 | blue | 0.4 | 0.00309, 0.00309, 0.00018 |
| `tilt_link` | box 0.25 × 0.08 × 0.06 | 0 0 0.03 | orange | 0.3 | 0.00025, 0.0016525, 0.0017225 |
| `camera_link` | none | – | – | – | – |

The `<inertial>` origin is the centre of mass. For a uniform body it equals the shape origin.
Off-diagonal inertia terms are 0.

### Live preview
Open the **Robot** tab. In **Preview** mode it runs the real `xacro` tool on the file you are editing,
**including unsaved changes**, and draws the result. Use it while you type: parse errors appear above
the 3D view, and the last valid model stays on screen.

Press **Check: Pan-tilt model** when it looks right. The grader expands your *installed* file, so build
first. It then compares every frame position, axis, limit, shape and inertia against the
specification.
