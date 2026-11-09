cmake_minimum_required(VERSION 3.16)
project(diffbot_webots)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(rosgraph_msgs REQUIRED)
find_package(tf2_ros REQUIRED)

# The Webots C API (webots/robot.h ...) and its import library, from the Webots installation.
# WEBOTS_HOME is set by the academy when Webots is installed.
file(TO_CMAKE_PATH "$ENV{WEBOTS_HOME}" WEBOTS_HOME)
if(NOT EXISTS "${WEBOTS_HOME}/lib/controller/Controller.lib")
  message(FATAL_ERROR "Webots not found (WEBOTS_HOME='${WEBOTS_HOME}'). Install Webots R2025a and restart the academy.")
endif()

add_executable(webots_driver src/webots_driver.cpp)
target_include_directories(webots_driver PRIVATE "${WEBOTS_HOME}/include/controller/c")
target_link_libraries(webots_driver "${WEBOTS_HOME}/lib/controller/Controller.lib")
ament_target_dependencies(webots_driver rclcpp geometry_msgs nav_msgs sensor_msgs rosgraph_msgs tf2_ros)

# go_to_goal knows nothing about Webots: only ROS messages
add_executable(go_to_goal src/go_to_goal.cpp)
ament_target_dependencies(go_to_goal rclcpp geometry_msgs nav_msgs)

install(TARGETS webots_driver go_to_goal DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY urdf launch worlds DESTINATION share/${PROJECT_NAME})

ament_package()
