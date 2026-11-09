## Odometry vs. ground truth

Odometry is the robot's *own estimate* of its motion, computed from wheel rotation, wheel radius and wheel
separation. If those numbers are wrong, the estimate is wrong, and every map, path and goal built on it
inherits the error.

**Check: Controllers & odometry vs. physics** drives your simulated robot straight, then turns it. It
compares your controller's odometry with Gazebo's **ground-truth** pose, read from the physics engine:

* distance ratio odometry / truth must be within 0.85–1.15, which tests `wheel_radius`;
* rotation ratio must be within 0.75–1.25, which tests `wheel_separation`.

The match will not be perfect even with correct numbers. Real physics has wheel slip, especially when
turning. That slip is why real robots fuse odometry with other sensors (Chapters 6 and 11).
