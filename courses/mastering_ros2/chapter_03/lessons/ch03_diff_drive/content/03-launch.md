## Publish and spin the wheels

**Build**, then **Run ▸ ros2 launch diffbot_description display.launch.xml**. In the **Robot** tab
choose **Live** and enable **Publish /joint_states**, then spin the wheel sliders. In the TF Tree,
`left_wheel_link` and `right_wheel_link` are dynamic, and the casters and laser are static.

On the real robot (Chapter 11), wheel encoders drive these joints, and the same wheel radius and
separation turn wheel speeds into odometry. A wrong number here becomes a wrong odometry estimate there.
