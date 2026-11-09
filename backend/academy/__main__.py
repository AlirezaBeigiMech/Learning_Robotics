import os
import sys

import uvicorn

from .config import settings

MAX_SAFE_WS_PATH = 130  # leaves ~130 characters for CMake/MSVC internals below the 260 limit


def main() -> None:
    if sys.platform != "win32":
        sys.exit("This build of the academy targets native Windows (RoboStack ROS 2 Jazzy).")
    if not os.environ.get("ROS_DISTRO"):
        sys.exit("ROS 2 environment not active. Start the academy with:  pixi run start")
    print(f"Mastering ROS 2 Academy on http://localhost:{settings.port}  (ROS 2 {os.environ['ROS_DISTRO']})")
    # MSVC's linker is not long-path aware: CMake's compiler check inside a workspace adds ~110 characters
    # (build\<pkg>\CMakeFiles\CMakeScratch\TryCompile-xxxxxx\CMakeFiles\cmTC_xxxxx.dir\...). Warn early
    # instead of letting students meet "LNK1104: cannot open file ... intermediate.manifest".
    ws_root = settings.workspaces_dir / "100" / "ws" / "build" / "a_package_name_of_20c"
    if len(str(ws_root)) > MAX_SAFE_WS_PATH:
        print(f"WARNING: the data folder is deep ({len(str(settings.data_dir))} characters): C++ builds may fail with\n"
              "         LNK1104 because Windows/MSVC limit paths to 260 characters. Move the academy to a shorter\n"
              "         folder or set ACADEMY_DATA_DIR to a short path such as C:\\ros2-academy-data.")
    uvicorn.run("academy.app:app", host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
