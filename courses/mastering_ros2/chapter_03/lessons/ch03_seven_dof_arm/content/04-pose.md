## Pose the arm

In Preview, move the sliders and convince yourself of the pattern **roll – pitch – roll – pitch …**:

* the **roll** joints (axis z) spin the rest of the arm about its own length;
* the **pitch** joints (axis y) bend it.

Alternating roll and pitch axes is what gives a 7-DOF arm a redundant degree of freedom. The gripper
can keep the same pose while the elbow swings. Chapter 7 uses that redundancy when planning around
obstacles.

Click `left_finger_link`: its joint is **prismatic**. Move its slider and the right finger follows,
because of the mimic joint.
