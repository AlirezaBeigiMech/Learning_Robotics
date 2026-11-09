## Workspaces, packages and colcon

A **workspace** is a folder with a `src/` directory full of **packages**. `colcon build` turns it into:

```
ws/
├─ src/        ← your packages (what you edit)
├─ build/      ← intermediate build files (CMake, object files)
├─ install/    ← what actually runs (setup scripts, executables, libraries)
└─ log/        ← build logs
```

A **package** is the unit of building, sharing and dependency management. A C++ package has three parts:

| File | Purpose |
|---|---|
| `package.xml` | name, version, dependencies (`rclcpp`), `<build_type>ament_cmake</build_type>` |
| `CMakeLists.txt` | how to compile: `find_package(rclcpp)`, `add_executable(hello_node src/hello_node.cpp)`, `install(TARGETS …)` |
| `src/*.cpp` | your node's source code |

The academy runs `colcon build --merge-install` with the **Ninja** generator and the **MSVC** compiler. On
Windows this keeps paths short; the default Visual Studio generator breaks on ROS's deeply nested build folders.
The first C++ build of a package takes a few seconds longer than later ones.

**Overlays:** your `install/setup.bat` (or `local_setup.ps1`) *overlays* your packages on top of the ROS 2
installation (the *underlay*). The academy sources it for you when it runs your nodes. Its terminal
already has the underlay active, so after a build you source just your overlay:

```
. .\install\local_setup.ps1
ros2 pkg list --no-daemon | Select-String first_node_lab
```
