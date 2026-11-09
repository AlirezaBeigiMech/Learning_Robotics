cmake_minimum_required(VERSION 3.16)
project(arm_description NONE)

find_package(ament_cmake REQUIRED)

# A description package contains no compiled code: it installs model and launch files
# into share/arm_description, where $(find-pkg-share arm_description) and xacro's $(find arm_description) look.
install(DIRECTORY urdf launch DESTINATION share/${PROJECT_NAME})

ament_package()
