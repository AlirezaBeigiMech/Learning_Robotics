## Check the controllers

**Check: Arm & gripper controllers** starts your simulation and sends trajectories **from the grader**:
a random arm pose, and opening the gripper. It then reads the simulated joints from `/joint_states`.
Every joint must arrive within 0.03 rad.

This tests your **configuration**: interfaces, controller joint lists and plugin. Your own node comes next.
