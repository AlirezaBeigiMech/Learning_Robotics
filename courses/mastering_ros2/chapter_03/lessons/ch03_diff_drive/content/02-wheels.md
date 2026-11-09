## Write the wheels and laser

Open `urdf/diffbot.urdf.xacro`. The parameters, base, and the `caster` macro (used twice, front and back)
are done.

| Part | Joint (type) | Joint origin (relative to base_link) | Axis | Link geometry | Mass |
|---|---|---|---|---|---|
| left wheel | `left_wheel_joint` (continuous) | 0, +wheel_separation/2, 0 | 0 1 0 | cylinder r = wheel_radius, length = wheel_width, rolled π/2 | wheel_mass |
| right wheel | `right_wheel_joint` (continuous) | 0, −wheel_separation/2, 0 | 0 1 0 | same | wheel_mass |
| laser | `laser_joint` (fixed) | 0.08, 0, base_length/2 + 0.015 | – | cylinder r 0.03, length 0.03 | 0.1 |

Links are named `left_wheel_link`, `right_wheel_link` and `laser_link`. Use the **properties**, not
literal numbers. Then change `wheel_separation` in the preview and watch both wheels move. That is the
point of xacro.

Note that the **joint** frame keeps the base's orientation (axis y = the axle). Only the **shape** is
rolled, so that the cylinder's axis lines up with y.
