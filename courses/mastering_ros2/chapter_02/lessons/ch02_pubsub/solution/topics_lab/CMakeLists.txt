cmake_minimum_required(VERSION 3.16)
project(topics_lab)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)

# One executable per node: add_executable(<name> <source>) + its ROS dependencies.
add_executable(number_publisher src/number_publisher.cpp)
ament_target_dependencies(number_publisher rclcpp std_msgs)

add_executable(number_subscriber src/number_subscriber.cpp)
ament_target_dependencies(number_subscriber rclcpp std_msgs)

# Install executables into lib/<package>, which is where `ros2 run <package> <executable>` looks.
install(TARGETS number_publisher number_subscriber
  DESTINATION lib/${PROJECT_NAME})

ament_package()
