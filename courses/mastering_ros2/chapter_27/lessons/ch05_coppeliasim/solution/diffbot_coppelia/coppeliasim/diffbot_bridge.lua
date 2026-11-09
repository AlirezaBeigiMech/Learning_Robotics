-- diffbot_bridge.lua: a CoppeliaSim add-on that connects the simulated diffbot to ROS 2 through simROS2.
--
-- The simulator-adapter contract (the same one the Webots driver implements in the next lesson):
--   in : /cmd_vel   geometry_msgs/msg/Twist      linear.x (m/s) and angular.z (rad/s)
--   out: /odom      nav_msgs/msg/Odometry        frame "odom", child "base_link"; pose AND twist, from the
--                                                wheel encoders (never from the simulator's true pose)
--   out: /tf        odom -> base_link            the same pose; base_link is at axle height (z = 0.05)
--   out: /tf        base_link -> *_wheel_link    wheel rotation (simROS2 has no sensor_msgs/JointState)
--
-- CoppeliaSim calls the sysCall_* functions: init once, then every simulation step (10 ms) actuation
-- (command the joints) followed by sensing (read the sensors, publish).
sim = require 'sim'
simROS2 = require 'simROS2'
simURDF = require 'simURDF'

local WHEEL_RADIUS = 0.05     -- m
local WHEEL_SEPARATION = 0.32 -- m, distance between the wheel contact points

local left, right
local cmd = {v = 0.0, w = 0.0}
local odom = {x = 0.0, y = 0.0, yaw = 0.0, v = 0.0, w = 0.0}
local lastLeft, lastRight, lastTime
local cmdSub, odomPub

local function wrap(a) return math.atan(math.sin(a), math.cos(a)) end

function sysCall_init()
    -- simROS2 has no rosgraph_msgs/Clock, so ROS cannot follow simulation time: run the simulation in
    -- real time and stamp messages with ROS (system) time instead.
    sim.setBoolProperty(sim.handle_scene, 'realtimeSimulation', true)
    sim.setFloatProperty(sim.handle_scene, 'timeStep', 0.01)  -- 100 Hz physics: less wheel slip than the default 50 ms

    -- The robot: imported from the same URDF that robot_state_publisher publishes (passed by the launch file).
    simURDF.import(sim.getNamedStringParam('diffbot.urdf'), 0)
    left = sim.getObject('/base_link_respondable/left_wheel_joint')
    right = sim.getObject('/base_link_respondable/right_wheel_joint')
    for _, joint in ipairs({left, right}) do  -- the wheels are speed-controlled motors
        sim.setObjectInt32Param(joint, sim.jointintparam_dynctrlmode, sim.jointdynctrl_velocity)
        sim.setJointTargetVelocity(joint, 0)  -- the importer leaves a non-zero target: the robot would creep away
    end
    for _, caster in ipairs({'/base_link_respondable/caster_front_joint/caster_front_link_respondable',
                             '/base_link_respondable/caster_back_joint/caster_back_link_respondable'}) do
        sim.setEngineFloatParam(sim.bullet_body_friction, sim.getObject(caster), 0)  -- ball casters roll freely
    end

    cmdSub = simROS2.createSubscription('/cmd_vel', 'geometry_msgs/msg/Twist', function(msg)
        cmd.v, cmd.w = msg.linear.x, msg.angular.z
    end)
    odomPub = simROS2.createPublisher('/odom', 'nav_msgs/msg/Odometry')
    sim.addLog(sim.verbosity_scriptinfos, 'diffbot bridge ready: /cmd_vel -> wheels, wheels -> /odom + /tf')
end

function sysCall_actuation()
    -- differential-drive inverse kinematics: body velocity (v, w) -> wheel angular speeds (rad/s)
    local vl = (cmd.v - cmd.w * WHEEL_SEPARATION / 2) / WHEEL_RADIUS
    local vr = (cmd.v + cmd.w * WHEEL_SEPARATION / 2) / WHEEL_RADIUS
    sim.setJointTargetVelocity(left, vl)
    sim.setJointTargetVelocity(right, vr)
end

local function publishWheelTransforms(stamp, ql, qr)
    -- wheel link poses: fixed offset +-0.16 m along y, rotated about y by the joint angle
    local tfs = {}
    for _, w in ipairs({{'left_wheel_link', 0.16, ql}, {'right_wheel_link', -0.16, qr}}) do
        tfs[#tfs + 1] = {header = {stamp = stamp, frame_id = 'base_link'}, child_frame_id = w[1],
            transform = {translation = {x = 0, y = w[2], z = 0}, rotation = {x = 0, y = math.sin(w[3] / 2), z = 0, w = math.cos(w[3] / 2)}}}
    end
    simROS2.sendTransforms(tfs)
end

function sysCall_sensing()
    local t = sim.getSimulationTime()
    local ql, qr = sim.getJointPosition(left), sim.getJointPosition(right)
    if lastTime and t > lastTime then
        -- distance rolled by each wheel during this step (angles wrap at +-pi)
        local dl = wrap(ql - lastLeft) * WHEEL_RADIUS
        local dr = wrap(qr - lastRight) * WHEEL_RADIUS
        -- forward kinematics, integrated at the middle of the step's rotation
        local ds = (dl + dr) / 2
        local dyaw = (dr - dl) / WHEEL_SEPARATION
        odom.x = odom.x + ds * math.cos(odom.yaw + dyaw / 2)
        odom.y = odom.y + ds * math.sin(odom.yaw + dyaw / 2)
        odom.yaw = wrap(odom.yaw + dyaw)
        odom.v = ds / (t - lastTime)
        odom.w = dyaw / (t - lastTime)
    end
    lastLeft, lastRight, lastTime = ql, qr, t

    local stamp = simROS2.getSystemTime()
    local q = {x = 0, y = 0, z = math.sin(odom.yaw / 2), w = math.cos(odom.yaw / 2)}
    simROS2.publish(odomPub, {
        header = {stamp = stamp, frame_id = 'odom'}, child_frame_id = 'base_link',
        pose = {pose = {position = {x = odom.x, y = odom.y, z = 0}, orientation = q}},
        twist = {twist = {linear = {x = odom.v, y = 0, z = 0}, angular = {x = 0, y = 0, z = odom.w}}},
    })
    simROS2.sendTransform({header = {stamp = stamp, frame_id = 'odom'}, child_frame_id = 'base_link',
        transform = {translation = {x = odom.x, y = odom.y, z = WHEEL_RADIUS}, rotation = q}})
    publishWheelTransforms(stamp, ql, qr)
end

function sysCall_cleanup()
    if cmdSub then simROS2.shutdownSubscription(cmdSub) end
    if odomPub then simROS2.shutdownPublisher(odomPub) end
end
