"""Course validation through the REAL grader (no mocks).

For every lesson:
  * the reference solution must pass every checkpoint, including hidden tests;
  * the untouched starter must FAIL the final checkpoint (otherwise the exercise teaches nothing);
  * lesson-specific mutants (known-wrong programs) must fail the checkpoint that should catch them.

Usage:  pixi run test-course            (all lessons)
        pixi run test-course ch02_pubsub
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from academy.assessment.grader import grade  # noqa: E402
from academy.config import settings  # noqa: E402
from academy.content.loader import load_course, read_tree  # noqa: E402


PUB = "topics_lab/src/number_publisher.cpp"


def best_effort_publisher(files: dict[str, str]) -> dict[str, str]:
    """The ch02 debugging-lab fault: publisher BEST_EFFORT vs. a RELIABLE subscriber."""
    return replace_in(PUB, 'create_publisher<std_msgs::msg::Int32>("numbers", 10)',
                      'create_publisher<std_msgs::msg::Int32>("numbers", rclcpp::QoS(10).best_effort())')(files)


def wrong_rate_publisher(files: dict[str, str]) -> dict[str, str]:
    return replace_in(PUB, "create_wall_timer(100ms,", "create_wall_timer(500ms,")(files)


def compile_error_publisher(files: dict[str, str]) -> dict[str, str]:
    return replace_in(PUB, "msg.data = count_;", "msg.dat = count_;")(files)


def replace_in(key: str, old: str, new: str):
    def mutate(files: dict[str, str]) -> dict[str, str]:
        assert old in files[key], f"mutant anchor not found in {key}: {old}"
        return {**files, key: files[key].replace(old, new, 1)}
    return mutate


PT = "pan_tilt_description/urdf/pan_tilt.urdf"
ARM = "arm_description/urdf/seven_dof_arm.urdf.xacro"
DIFF = "diffbot_description/urdf/diffbot.urdf.xacro"
D4Y = "diffbot_sim/config/controllers.yaml"
D4N = "diffbot_sim/src/drive_forward.cpp"
A4Y = "arm_sim/config/controllers.yaml"
A4N = "arm_sim/src/move_arm.cpp"
CB = "diffbot_coppelia/coppeliasim/diffbot_bridge.lua"
WD = "diffbot_webots/src/webots_driver.cpp"
WG = "diffbot_webots/src/go_to_goal.cpp"

MUTANTS = {
    "ch05_webots": [
        ("encoder angles used as distances (radius forgotten)",
         replace_in(WD, "const double dl = (ql - last_ql_) * kWheelRadius, dr = (qr - last_qr_) * kWheelRadius;",
                    "const double dl = ql - last_ql_, dr = qr - last_qr_;"), "driver"),
        ("scan left in Webots order (mirrored)",
         replace_in(WD, "    std::reverse(scan.ranges.begin(), scan.ranges.end());\n", ""), "scan"),
        ("no command time-out",
         replace_in(WD, "    if (t - last_cmd_time_ > kCmdTimeout) {  // the commanding node stopped or crashed: do not drive on blindly\n"
                        "      v = w = 0.0;\n    }\n", ""), "final"),
        ("go_to_goal ignores the goal parameters",
         lambda f: replace_in(WG, 'goal_x_ = declare_parameter<double>("goal_x", 1.2);',
                              'declare_parameter<double>("goal_x", 1.2);\n    goal_x_ = 1.2;')(
             replace_in(WG, 'goal_y_ = declare_parameter<double>("goal_y", -0.6);',
                        'declare_parameter<double>("goal_y", -0.6);\n    goal_y_ = -0.6;')(f)), "final"),
    ],
    "ch05_coppeliasim": [
        ("bridge turns the wrong way (wheel formulas swapped)",
         lambda f: replace_in(CB, "local vl = (cmd.v - cmd.w * WHEEL_SEPARATION / 2) / WHEEL_RADIUS",
                              "local vl = (cmd.v + cmd.w * WHEEL_SEPARATION / 2) / WHEEL_RADIUS")(
             replace_in(CB, "local vr = (cmd.v + cmd.w * WHEEL_SEPARATION / 2) / WHEEL_RADIUS",
                        "local vr = (cmd.v - cmd.w * WHEEL_SEPARATION / 2) / WHEEL_RADIUS")(f)), "bridge"),
        ("odometry uses half the wheel separation",
         replace_in(CB, "local dyaw = (dr - dl) / WHEEL_SEPARATION", "local dyaw = (dr - dl) / (WHEEL_SEPARATION / 2)"), "bridge"),
        ("TF puts base_link on the ground (z = 0)",
         replace_in(CB, "transform = {translation = {x = odom.x, y = odom.y, z = WHEEL_RADIUS}, rotation = q}})",
                    "transform = {translation = {x = odom.x, y = odom.y, z = 0}, rotation = q}})"), "bridge"),
        ("odometry integrates along x only (ignores the heading)",
         replace_in(CB, "odom.x = odom.x + ds * math.cos(odom.yaw + dyaw / 2)\n        odom.y = odom.y + ds * math.sin(odom.yaw + dyaw / 2)",
                    "odom.x = odom.x + ds"), "final"),
    ],
    "ch02_pubsub": [
        ("publisher BEST_EFFORT (QoS mismatch)", best_effort_publisher, "integration"),
        ("publisher at 2 Hz", wrong_rate_publisher, "publisher"),
        ("C++ compile error (msg.dat)", compile_error_publisher, "publisher"),
    ],
    "ch03_pan_tilt": [
        ("tilt axis x instead of y", replace_in(PT, '<axis xyz="0 1 0"/>', '<axis xyz="1 0 0"/>'), "model"),
        ("tilt axis x — caught live through TF", replace_in(PT, '<axis xyz="0 1 0"/>', '<axis xyz="1 0 0"/>'), "tf"),
        ("pan column visual not lifted (centred on joint)",
         replace_in(PT, '<origin xyz="0 0 0.15" rpy="0 0 0"/>\n      <geometry><cylinder radius="0.03"',
                    '<origin xyz="0 0 0" rpy="0 0 0"/>\n      <geometry><cylinder radius="0.03"'), "model"),
    ],
    "ch03_seven_dof_arm": [
        ("elbow_pitch joint placed 2 cm too high",
         replace_in(ARM, 'name="elbow_pitch" parent="elbow_roll_link" joint_z="0.06"',
                    'name="elbow_pitch" parent="elbow_roll_link" joint_z="0.08"'), "model"),
        ("right finger without mimic",
         replace_in(ARM, '<mimic joint="left_finger_joint" multiplier="1" offset="0"/>', ''), "model"),
    ],
    "ch04_diffbot_gazebo": [
        ("wheel_radius doubled in controllers.yaml", replace_in(D4Y, "wheel_radius: 0.05", "wheel_radius: 0.10"), "sim"),
        ("wheel_separation wrong in controllers.yaml", replace_in(D4Y, "wheel_separation: 0.32", "wheel_separation: 0.55"), "sim"),
        ("drive_forward ignores the distance (drives at full speed, never stops)",
         lambda f: replace_in(D4N, "std::min(speed_, 0.02 + 0.5 * remaining)", "speed_")(
             replace_in(D4N, "if (remaining > 0.005 && !reached_) {", "if (true) {")(f)), "drive"),
    ],
    "ch04_arm_gazebo": [
        ("gripper_controller commands only one finger",
         replace_in(A4Y, 'joints: ["left_finger_joint", "right_finger_joint"]', 'joints: ["left_finger_joint"]'), "sim"),
        ("move_arm publishes before the controller listens",
         replace_in(A4N, "if (sent_ || pub_->get_subscription_count() == 0) {", "if (sent_) {"), "move"),
        ("move_arm ignores the duration parameter",
         replace_in(A4N, "rclcpp::Duration::from_seconds(duration_)", "rclcpp::Duration::from_seconds(2.0)"), "final"),
    ],
    "ch03_diff_drive": [
        ("wheel inertia not rotated with the wheel",
         replace_in(DIFF, '<xacro:cylinder_inertial m="${wheel_mass}" r="${wheel_radius}" h="${wheel_width}">\n'
                          '        <origin xyz="0 0 0" rpy="${pi/2} 0 0"/>',
                    '<xacro:cylinder_inertial m="${wheel_mass}" r="${wheel_radius}" h="${wheel_width}">\n'
                    '        <origin xyz="0 0 0" rpy="0 0 0"/>'), "model"),
        ("robot sunk into the ground (base_link at z=0)",
         replace_in(DIFF, '<origin xyz="0 0 ${wheel_radius}" rpy="0 0 0"/>', '<origin xyz="0 0 0" rpy="0 0 0"/>'), "final"),
    ],
}


def run(label: str, files: dict, loaded, checkpoint: str, expect_pass: bool) -> bool:
    t0 = time.time()
    res = grade(files, loaded, checkpoint, settings.grader_dir / f"validate-{loaded.lesson.id}-{checkpoint}")
    s = res["summary"]
    passed = res["build"]["ok"] and s["total"] and s["failed"] == 0
    ok = bool(passed) == expect_pass
    print(f"  [{'OK ' if ok else 'BAD'}] {label:<45} checkpoint={checkpoint:<12} "
          f"{s['passed']}/{s['total']} passed, build={'ok' if res['build']['ok'] else 'FAILED'}  ({time.time() - t0:.0f}s)")
    if not res["build"]["ok"] and res["build"].get("diagnostics"):
        d = res["build"]["diagnostics"][0]
        print(f"        compiler diagnostic: {d['path']}:{d['line']}:{d['column']} {d['message'][:90]}")
    if not ok:
        if not res["build"]["ok"]:
            print(res["build"]["log_tail"])
        for t in res["tests"]:
            if (t["status"] != "passed") == expect_pass:
                print(f"        - {t['id']}: {t['status']}  expected={t['expected']} observed={t['observed']} msg={t['message']}")
        print("\n".join(res.get("log", "").splitlines()[-30:]))
    else:
        for t in res["tests"]:
            if t["status"] != "passed":
                print(f"        · {t['id']}: {t['status']} (observed: {t['observed']})")
    return ok


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    only = set(sys.argv[1:])
    course = load_course()
    all_ok = True
    for lid, loaded in course.lessons.items():
        if only and lid not in only:
            continue
        print(f"\n== {lid}: {loaded.lesson.title}")
        installed = {"webots": settings.webots_home, "coppeliasim": settings.coppeliasim_root}
        missing = [r for r in loaded.lesson.requires if not installed[r]]
        if missing:
            print(f"  [SKIPPED] needs {', '.join(missing)}, which is not installed")
            continue
        # packages used from earlier lessons: their reference solutions, graded together like a real submission
        used: dict[str, str] = {}
        for pkg in loaded.lesson.workspace.uses:
            provider = next(other for other in course.lessons.values() if other.lesson.workspace.package == pkg)
            used.update({k: v for k, v in read_tree(provider.solution_dir).items() if k.startswith(f"{pkg}/")})
        solution = {**used, **read_tree(loaded.solution_dir)}
        starter = {**used, **read_tree(loaded.level_dir("guided"))}
        for cp in loaded.lesson.checkpoints:
            all_ok &= run("reference solution", solution, loaded, cp.id, expect_pass=True)
        final = loaded.lesson.completion.checkpoint
        all_ok &= run("untouched starter", starter, loaded, final, expect_pass=False)
        for label, mutate, cp in MUTANTS.get(lid, []):
            all_ok &= run(f"mutant: {label}", mutate(solution), loaded, cp, expect_pass=False)
    print("\nRESULT:", "ALL CHECKS PASSED" if all_ok else "FAILURES")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
