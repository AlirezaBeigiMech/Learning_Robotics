## Connect the wheels to ros2_control

**TODO 1–2 in `urdf/diffbot.ros2_control.xacro`.** Declare the hardware and the two wheel joints:

```xml
<ros2_control name="GazeboSimSystem" type="system">
  <hardware><plugin>gz_ros2_control/GazeboSimSystem</plugin></hardware>
  <joint name="left_wheel_joint">
    <command_interface name="velocity"/>
    <state_interface name="position"/>
    <state_interface name="velocity"/>
  </joint>
  <!-- … right wheel … -->
</ros2_control>
```

…and the Gazebo plugin that hosts the `controller_manager`, pointing it at your controller configuration:

```xml
<gazebo>
  <plugin filename="gz_ros2_control-system" name="gz_ros2_control::GazeboSimROS2ControlPlugin">
    <parameters>$(find diffbot_sim)/config/controllers.yaml</parameters>
  </plugin>
</gazebo>
```

**TODO 3–4 in `config/controllers.yaml`.** Name the wheel joints and give the controller the robot's
geometry. These two numbers are its entire kinematic model:

| Parameter | Value | Where it comes from |
|---|---|---|
| `wheel_separation` | distance between the wheel joints | `wheel_separation` property in `diffbot.urdf.xacro` |
| `wheel_radius` | wheel radius | `wheel_radius` property |

Then **Build**, **Run ▸ ros2 launch diffbot_sim sim.launch.xml**, open the **Controllers** tab and
**Verify**. Both controllers must be **active**.
