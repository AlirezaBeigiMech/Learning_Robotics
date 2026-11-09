## Mass and inertia

RViz ignores `<inertial>`, but **physics simulators do not**. In Chapter 4 Gazebo will integrate these
numbers. A missing, zero or impossible inertia makes a link explode, jitter or fall through the floor.

For a uniform solid of mass m:

| Shape | ixx | iyy | izz |
|---|---|---|---|
| box x × y × z | m(y²+z²)/12 | m(x²+z²)/12 | m(x²+y²)/12 |
| cylinder r, h (axis z) | m(3r²+h²)/12 | m(3r²+h²)/12 | m r²/2 |
| sphere r | 2mr²/5 | 2mr²/5 | 2mr²/5 |

A real inertia tensor is **positive-definite**, and its principal moments satisfy the **triangle
inequality** (no moment is larger than the sum of the other two). The Robot tab's diagnostics check
both. `urdf/inertial.xacro` implements these formulas as macros, so you never type them by hand.
