## Submit

The final submission re-runs the three checkpoints, plus hidden tests:

* `go_to_goal` with a **different goal** passed as parameters;
* the **command time-out**: the grader drives the robot, then goes silent without sending a stop;
* the odometry's **twist** while driving.

It submits this package together with `diffbot_coppelia` from the previous lesson, since the portable check runs
both.

**Chapter 5 recap.** You connected one robot model to three simulators: Gazebo through ros2_control (Chapter 4),
CoppeliaSim through a simROS2 script, and Webots through a C++ driver on its C API. Behind one contract, the robot
software above them did not change. Chapter 6 builds on this with MoveIt 2 and Nav2.
