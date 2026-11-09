## Submit

The hidden test sends an unseen pose with a long `duration`. The arm must still be on its way partway
through, then arrive. That checks that your node really uses the timing you asked for.

Chapter 6 replaces hand-written joint angles with **MoveIt 2**, which plans collision-free trajectories
to a gripper *pose* and then sends them through this same `arm_controller`.
