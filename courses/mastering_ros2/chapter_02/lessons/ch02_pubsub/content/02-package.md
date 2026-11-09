## The `topics_lab` package

Your workspace already contains a starter package in `src/topics_lab`. It is an **ament_cmake** package, the
standard layout for C++ nodes:

| File | Purpose |
|---|---|
| `package.xml` | name, version, dependencies (`rclcpp`, `std_msgs`) and `<build_type>ament_cmake</build_type>` |
| `CMakeLists.txt` | `find_package(...)` for each dependency, then one `add_executable` + `ament_target_dependencies` per node |
| `CMakeLists.txt` → `install(TARGETS …)` | copies executables to `lib/topics_lab`, which is where `ros2 run` looks |
| `src/*.cpp` | your node code: one file per executable |

Open `CMakeLists.txt` and find the two executables, `number_publisher` and `number_subscriber`. Adding a third
node later means adding a source file and two lines here.

```academy:callout
kind: warning
title: Two real pitfalls
body: |
  * A dependency used in code but missing from `find_package` / `ament_target_dependencies` gives a
    compiler or linker error naming the missing header or symbol. Missing from `package.xml`, it builds
    on your PC but breaks for anyone installing your package.
  * If `package.xml` is invalid (for example a malformed maintainer e-mail), colcon may not recognise
    the folder as a ROS package at all. The editor checks `package.xml` as you save.
```

### Build it
Press **Build** in the toolbar. That runs, for real:

```
colcon build --merge-install          # Ninja generator + MSVC compiler
```

Watch the **Output** panel. The first build compiles all of rclcpp's templates for your nodes and takes
around 15–30 s. Later builds only recompile what changed. When it finishes, `install/` contains
`number_publisher.exe` and `number_subscriber.exe`. They run, but they do nothing yet: that is your job in
the next step.
