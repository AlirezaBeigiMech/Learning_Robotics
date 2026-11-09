cmake_minimum_required(VERSION 3.16)
project(diffbot_sim)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)

add_executable(drive_forward src/drive_forward.cpp)
ament_target_dependencies(drive_forward rclcpp geometry_msgs nav_msgs)

install(TARGETS drive_forward DESTINATION lib/${PROJECT_NAME})
# model, launch, controller configuration and world are found via $(find-pkg-share diffbot_sim)
install(DIRECTORY urdf launch config worlds DESTINATION share/${PROJECT_NAME})

ament_package()
