cmake_minimum_required(VERSION 3.16)
project(diffbot_coppelia)

find_package(ament_cmake REQUIRED)

# No C++ here: CoppeliaSim runs the Lua add-ons itself. Installing them lets the launch file find
# them with $(find-pkg-share diffbot_coppelia), like the model and the launch file.
install(DIRECTORY urdf launch coppeliasim DESTINATION share/${PROJECT_NAME})

ament_package()
