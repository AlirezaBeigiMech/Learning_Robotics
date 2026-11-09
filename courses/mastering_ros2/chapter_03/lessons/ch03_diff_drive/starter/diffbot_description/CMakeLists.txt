cmake_minimum_required(VERSION 3.16)
project(diffbot_description NONE)

find_package(ament_cmake REQUIRED)

# A description package contains no compiled code: it installs model and launch files
# into share/diffbot_description, where $(find-pkg-share diffbot_description) and xacro's $(find diffbot_description) look.
install(DIRECTORY urdf launch DESTINATION share/${PROJECT_NAME})

ament_package()
