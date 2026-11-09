"""Grader-side Webots supervisor (run as a separate process by adapters.WebotsTruth).
Prints the true planar pose of `DEF <name>` as JSON lines: {"t": sim time, "x", "y", "yaw"} every 50 ms of sim time."""

import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.environ["WEBOTS_HOME"], "lib", "controller", "python"))
from controller import Supervisor  # noqa: E402  (Webots' own Python API: ctypes over Controller.dll)

name = sys.argv[1] if len(sys.argv) > 1 else "DIFFBOT"
sup = Supervisor()
node = sup.getFromDef(name)
if node is None:
    print(f"no node 'DEF {name}' in the world", flush=True)
    sys.exit(2)
step = int(sup.getBasicTimeStep())
every = max(1, round(50 / step))
n = 0
while sup.step(step) != -1:
    n += 1
    if n % every:
        continue
    x, y, _ = node.getPosition()
    r = node.getOrientation()  # 3x3 rotation matrix, row-major
    print(json.dumps({"t": round(sup.getTime(), 4), "x": x, "y": y, "yaw": math.atan2(r[3], r[0])}), flush=True)
