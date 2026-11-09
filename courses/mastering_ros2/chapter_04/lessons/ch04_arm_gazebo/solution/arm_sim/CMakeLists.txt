cmake_minimum_required(VERSION 3.16)
project(arm_sim)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(trajectory_msgs REQUIRED)

add_executable(move_arm src/move_arm.cpp)
ament_target_dependencies(move_arm rclcpp trajectory_msgs)

install(TARGETS move_arm DESTINATION lib/${PROJECT_NAME})
# model, launch, controller configuration and world are found via $(find-pkg-share arm_sim)
install(DIRECTORY urdf launch config worlds DESTINATION share/${PROJECT_NAME})

ament_package()
