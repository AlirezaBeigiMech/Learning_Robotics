## Start CoppeliaSim

Open `launch/sim.launch.xml`. It starts two things:

* **robot_state_publisher** with `urdf/diffbot.urdf`, as in Chapter 3;
* **CoppeliaSim**, with options that make it load your scripts:

| Option | Meaning |
|---|---|
| `-h` | headless: no window (drop it with `headless:=false` to see CoppeliaSim on your desktop) |
| `-s0` | start the simulation immediately and run until stopped |
| `-a…/diffbot_bridge.lua` | load your bridge as an add-on |
| `-b…/ground_truth.lua` | load the ground-truth publisher (provided, do not edit) |
| `-Gdiffbot.urdf=…` | a named parameter the bridge reads with `sim.getNamedStringParam('diffbot.urdf')` |

**Build**, then **Run ▸ ros2 launch diffbot_coppelia sim.launch.xml**. Within about 10 seconds the output shows the
URDF importer creating the six links and `diffbot bridge ready`. Then:

1. **Topics**: `/ground_truth` is updating. It is the robot's true pose, straight from the simulator.
2. **ROS Graph**: the node `/sim_ros2_interface` is CoppeliaSim itself. Every simROS2 call in your scripts
   belongs to this one node.
3. **Robot** tab ▸ **Live**: the model from `/robot_description`. The robot is not placed in `odom` yet, because
   nothing publishes `odom → base_link`. That is your job in step 4.

```academy:callout
kind: note
title: The window
body: |
  Run `ros2 launch diffbot_coppelia sim.launch.xml headless:=false` in the **Terminal** to open CoppeliaSim's own
  window on your desktop. It is the same simulation with a 3D view and the script editor. Stop it with **Stop** in
  the academy (closing the window also works).
```

`coppeliasim` in the launch file is the academy's launcher for the CoppeliaSim you installed. It streams
CoppeliaSim's log to the output panel line by line, so an error in your Lua code shows up at once with its line
number.
