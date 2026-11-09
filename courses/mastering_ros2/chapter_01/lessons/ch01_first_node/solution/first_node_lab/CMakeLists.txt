cmake_minimum_required(VERSION 3.16)
project(first_node_lab)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)

# One executable per node: add_executable(<name> <source>) + its ROS dependencies.
add_executable(hello_node src/hello_node.cpp)
ament_target_dependencies(hello_node rclcpp)

# Install executables into lib/<package>, which is where `ros2 run <package> <executable>` looks.
install(TARGETS hello_node
  DESTINATION lib/${PROJECT_NAME})

ament_package()
