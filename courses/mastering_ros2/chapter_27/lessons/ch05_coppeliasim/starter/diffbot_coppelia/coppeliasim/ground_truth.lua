-- ground_truth.lua: the simulator's TRUE pose of the robot, published on /ground_truth (nav_msgs/msg/Odometry,
-- frame "world"). Odometry only estimates this pose from the wheels; comparing the two shows the estimate's error.
-- Provided by the course (do not edit): the grader uses it to check your bridge, like Gazebo's own pose in Chapter 4.
sim = require 'sim'
simROS2 = require 'simROS2'

local base, pub

function sysCall_init()
    pub = simROS2.createPublisher('/ground_truth', 'nav_msgs/msg/Odometry')
end

function sysCall_sensing()
    if not base then  -- the robot is imported by diffbot_bridge.lua; look it up once it exists
        base = sim.getObject('/base_link_respondable', {noError = true})
        if base == -1 then base = nil return end
    end
    local p = sim.getObjectPosition(base, sim.handle_world)
    local q = sim.getObjectQuaternion(base, sim.handle_world)  -- {x, y, z, w}
    simROS2.publish(pub, {
        header = {stamp = simROS2.getSystemTime(), frame_id = 'world'}, child_frame_id = 'base_link',
        pose = {pose = {position = {x = p[1], y = p[2], z = p[3]}, orientation = {x = q[1], y = q[2], z = q[3], w = q[4]}}},
    })
end

function sysCall_cleanup()
    simROS2.shutdownPublisher(pub)
end
