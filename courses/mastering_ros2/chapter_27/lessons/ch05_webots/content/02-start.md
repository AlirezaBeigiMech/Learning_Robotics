## Start Webots

Look at the three files that set up the simulation:

* `worlds/diffbot.wbt`: the world in Webots' text format. The robot is built from Webots nodes (`HingeJoint`,
  `RotationalMotor`, `Lidar`…) with the URDF's dimensions. Note `DEF DIFFBOT`, `controller "<extern>"` and the
  device names. Your C++ code looks devices up by these names.
* `launch/sim.launch.xml`: starts `webots` (the academy's launcher for your Webots installation) in batch mode,
  your `webots_driver` with `WEBOTS_CONTROLLER_URL = ipc://<port>/diffbot`, and robot_state_publisher.
* `src/webots_driver.cpp`: device set-up, the step loop, `/clock` and `/joint_states` are given. The rest is yours.

**Build** (this compiles against the Webots C API), then **Run ▸ ros2 launch diffbot_webots sim.launch.xml**. The
output shows Webots waiting for the extern controller, then `connected to Webots robot 'diffbot'`.

1. **Topics**: `/clock` advances in simulated time and `/joint_states` reports both wheels. `/odom` and `/scan`
   exist but stay empty or zero for now.
2. **Robot** tab ▸ **Live**: the model, with its wheels driven by `/joint_states` through robot_state_publisher.

```academy:callout
kind: note
title: Seeing Webots itself
body: |
  `ros2 launch diffbot_webots sim.launch.xml headless:=false` in the **Terminal** opens the Webots window, with
  the 3D view, the scene tree and the world editor. Webots warns about "an old unsupported Intel GPU" on integrated
  graphics. It still runs, and the academy hides that notice in headless runs.
```

```academy:callout
kind: note
title: A harmless warning
body: |
  robot_state_publisher logs "The root link base_link has an inertia specified … KDL does not support". The model's
  root is base_link because CoppeliaSim cannot import a URDF whose root link is empty. KDL only does kinematics, so
  ignoring the root's mass changes nothing it computes. The simulators, which need that mass, read it.
```
