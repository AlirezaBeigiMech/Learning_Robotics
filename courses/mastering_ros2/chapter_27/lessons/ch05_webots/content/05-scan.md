## The laser in ROS conventions

A simulator's sensor data is rarely in ROS's format. Converting it correctly is half of an adapter's job, and the
mistakes are easy to miss: a mirrored scan looks perfectly plausible.

`sensor_msgs/msg/LaserScan` describes a fan of beams by **angles**, measured **counter-clockwise** from the sensor's
x axis (REP 103):

| Field | Meaning |
|---|---|
| `angle_min`, `angle_max` | angle of the first and last beam |
| `angle_increment` | angle between neighbouring beams (> 0: counter-clockwise) |
| `ranges[i]` | distance along the beam at `angle_min + i · angle_increment` (`inf`: nothing hit) |

Webots' `wb_lidar_get_range_image` returns `n` ranges ordered **left to right**, i.e. **clockwise**, starting at
`+fov/2`. Here `n = 360` and `fov = 2π`: one beam per degree.

**TODO 5**: fill `angle_increment`, `angle_min` (the **centre** of the first beam, `−fov/2 + increment/2`) and
`angle_max`, then copy the ranges **in ROS order**.

Test it against the world. There is a wall 2 m ahead (1.92 m from the laser, which sits 8 cm forward) and a box
1.2 m to the **left**. In **Topics**, echo `/scan` and look at the beam at index 270 (angle ≈ +90°). It should be
about 1.2 m. If the box shows up at index 90 (−90°, the right) instead, your scan is mirrored.
