cmake_minimum_required(VERSION 3.16)
project(pan_tilt_description NONE)

find_package(ament_cmake REQUIRED)

# A description package contains no compiled code: it installs model and launch files
# into share/pan_tilt_description, where $(find-pkg-share pan_tilt_description) and xacro's $(find pan_tilt_description) look.
install(DIRECTORY urdf launch DESTINATION share/${PROJECT_NAME})

ament_package()
