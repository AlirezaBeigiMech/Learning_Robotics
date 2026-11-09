"""Fast unit tests (no ROS processes). Real-ROS checks live in e2e_workflow.py and scripts/validate_course.py."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from academy.assessment.grader import parse_junit
from academy.content.loader import load_course
from academy.content.schema import Lesson
from academy.workspace.manager import StudentWorkspace, WorkspaceError, diagnose


@pytest.fixture
def ws(tmp_path: Path) -> StudentWorkspace:
    w = StudentWorkspace(user_id=1, root=tmp_path / "u1", domain_id=5)
    w.src.mkdir(parents=True)
    (w.src / "pkg").mkdir()
    (w.src / "pkg" / "package.xml").write_text("<package/>", encoding="utf-8")
    return w


@pytest.mark.parametrize("bad", ["../x.py", "..\\x.py", "/etc/passwd", "C:/Windows/win.ini", "pkg/../../x", "pkg/.git/config",
                                 "pkg/__pycache__/a.pyc", "", "a" * 400])
def test_path_traversal_rejected(ws: StudentWorkspace, bad: str) -> None:
    with pytest.raises(WorkspaceError):
        ws.resolve(bad)


def test_write_read_roundtrip_and_limits(ws: StudentWorkspace) -> None:
    ws.write("pkg/pkg/node.py", "print('hi')\n", create=True)
    assert ws.read("pkg/pkg/node.py") == "print('hi')\n"
    with pytest.raises(WorkspaceError):
        ws.write("pkg/pkg/node.py", "x", create=True)  # exists
    with pytest.raises(WorkspaceError):
        ws.write("pkg/evil.exe", "x", create=True)  # disallowed type
    with pytest.raises(WorkspaceError):
        ws.write("pkg/big.py", "x" * (300 * 1024), create=True)


def test_snapshot_only_contains_package(ws: StudentWorkspace) -> None:
    ws.write("pkg/pkg/a.py", "a = 1\n", create=True)
    (ws.src / "other").mkdir()
    (ws.src / "other" / "b.py").write_text("b", encoding="utf-8")
    snap = ws.snapshot_package("pkg")
    assert set(snap) == {"pkg/package.xml", "pkg/pkg/a.py"}


def test_diagnostics_python_and_package_xml() -> None:
    assert diagnose("p/x.py", "def f(:\n")[0]["severity"] == "error"
    assert diagnose("p/x.py", "x = 1\n") == []
    bad = textwrap.dedent("""\
        <?xml version="1.0"?>
        <package format="3"><name>p</name><version>0.0.1</version><description>d</description>
        <maintainer email="a@b.c">a</maintainer><license>MIT</license>
        <export><build_type>ament_python</build_type></export></package>""")
    d = diagnose("p/package.xml", bad)
    assert d and "email" in d[0]["message"].lower() and "ROS package" in d[0]["message"]


def test_course_content_is_valid() -> None:
    c = load_course()
    assert sorted(c.chapters) == list(range(1, 29))
    assert {comp.id for comp in c.course.competencies} == {
        comp for ch in c.chapters.values() for comp in ch.competencies}, "every job competency is taught somewhere"
    assert {"ch01_first_node", "ch02_pubsub"} <= set(c.lessons)
    for loaded in c.lessons.values():
        assert loaded.solution_dir.is_dir(), "every lesson ships a reference solution"
        assert any(cp.final for cp in loaded.lesson.checkpoints)
        for step in loaded.lesson.steps:
            assert len(step.hints) <= 4  # level 5 is always the reference solution


def test_schema_rejects_dangling_checkpoint() -> None:
    with pytest.raises(ValueError):
        Lesson.model_validate({
            "id": "x", "title": "t", "description": "d", "book_reference": {"chapter": 1}, "difficulty": "beginner",
            "estimated_minutes": 1, "objectives": [], "lab_tabs": ["graph"], "workspace": {"package": "p"},
            "steps": [{"id": "s", "title": "s", "kind": "code", "content": "c.md", "completion": {"type": "checkpoint", "checkpoint": "nope"}}],
            "checkpoints": [{"id": "final", "title": "f", "tests": ["t.py"], "final": True}], "completion": {"checkpoint": "final"},
        })


def test_junit_parsing_hides_hidden_test_details(tmp_path: Path) -> None:
    xml = tmp_path / "junit.xml"
    xml.write_text(textwrap.dedent("""\
        <testsuites><testsuite>
          <testcase classname="test_pub" name="test_rate" time="1.2">
            <properties><property name="title" value="Rate is 10 Hz"/><property name="hidden" value="0"/>
              <property name="expected" value="8-13 Hz"/><property name="observed" value="2.0 Hz"/>
              <property name="suggestion" value="use 0.1 s"/></properties>
            <failure message="assert 2.0 &gt;= 8.0">trace</failure>
          </testcase>
          <testcase classname="test_hidden" name="test_hidden_values" time="0.5">
            <properties><property name="title" value="Secret inputs"/><property name="hidden" value="1"/>
              <property name="observed" value="missing 31337"/></properties>
            <failure message="assert 31337 in output">trace</failure>
          </testcase>
          <testcase classname="test_pub" name="test_ok" time="0.1"/>
        </testsuite></testsuites>"""), encoding="utf-8")
    tests = {t["id"]: t for t in parse_junit(xml)}
    assert tests["test_rate"]["status"] == "failed" and tests["test_rate"]["observed"] == "2.0 Hz"
    assert tests["test_rate"]["suggestion"] == "use 0.1 s"
    hidden = tests["test_hidden_values"]
    assert hidden["hidden"] and hidden["observed"] is None and hidden["message"] is None  # inputs never leak
    assert tests["test_ok"]["status"] == "passed" and tests["test_ok"]["suggestion"] is None


def test_terminal_replay_strips_queries_but_keeps_output() -> None:
    from academy.runtime.terminal import QUERY_RE

    replay = "\x1b[1t\x1b[c\x1b[>0c\x1b[6n\x1b[?1004hros2 \x1b[36mready\x1b[0m> "
    cleaned = QUERY_RE.sub("", replay)
    assert cleaned == "\x1b[?1004hros2 \x1b[36mready\x1b[0m> "


@pytest.mark.parametrize("host,ok", [("localhost:8000", True), ("127.0.0.1:8010", True), ("[::1]:8000", True),
                                     ("attacker.example:8000", False), ("localhost.evil.com", False), (None, False)])
def test_local_host_guard(host, ok) -> None:
    from academy.security import host_is_local

    assert host_is_local(host) is ok


@pytest.mark.parametrize("origin,ok", [(None, True), ("http://localhost:8000", True), ("http://127.0.0.1:3000", True),
                                       ("https://evil.example", False), ("null", False)])
def test_local_origin_guard(origin, ok) -> None:
    from academy.security import origin_is_local

    assert origin_is_local(origin) is ok


def test_compiler_diagnostics_map_to_student_files(tmp_path: Path) -> None:
    from academy.runtime.session import compiler_diagnostics

    src = tmp_path / "src"
    (src / "pkg" / "src").mkdir(parents=True)
    cpp = src / "pkg" / "src" / "pub.cpp"
    cpp.write_text("x", encoding="utf-8")
    (src / "pkg" / "CMakeLists.txt").write_text("x", encoding="utf-8")
    lines = [
        f"{cpp}(25,9): error C2039: 'dat': is not a member of 'Int32' [{tmp_path}{chr(92)}build{chr(92)}pkg.vcxproj]",
        f"{tmp_path}{chr(92)}ros{chr(92)}node.hpp(12): warning C4996: deprecated thing in a ROS header",
        "CMake Error at CMakeLists.txt:7 (find_package):",
    ]
    diags = compiler_diagnostics(lines, src)
    assert diags[0] == {"path": "pkg/src/pub.cpp", "line": 25, "column": 9, "severity": "error",
                        "message": "C2039: 'dat': is not a member of 'Int32'", "source": "compiler"}
    assert diags[1]["path"] == "pkg/CMakeLists.txt" and diags[1]["line"] == 7  # CMake paths are package-relative
    assert len(diags) == 2  # warnings in files outside the student's sources are ignored


def test_python_package_is_backed_up_when_lesson_becomes_cpp(ws: StudentWorkspace, tmp_path: Path) -> None:
    def pkg_xml(build_type: str) -> str:
        return (f'<?xml version="1.0"?><package format="3"><name>topics_lab</name><version>0.1.0</version>'
                f'<description>d</description><maintainer email="s@example.com">s</maintainer><license>MIT</license>'
                f'<export><build_type>{build_type}</build_type></export></package>')

    old = ws.src / "topics_lab"
    (old / "topics_lab").mkdir(parents=True)
    (old / "package.xml").write_text(pkg_xml("ament_python"), encoding="utf-8")
    (old / "topics_lab" / "number_publisher.py").write_text("# my python work", encoding="utf-8")
    starter = tmp_path / "starter"
    (starter / "topics_lab" / "src").mkdir(parents=True)
    (starter / "topics_lab" / "package.xml").write_text(pkg_xml("ament_cmake"), encoding="utf-8")
    (starter / "topics_lab" / "src" / "number_publisher.cpp").write_text("// cpp", encoding="utf-8")

    backup = ws.migrate_if_build_type_changed("topics_lab", starter)
    assert backup is not None and (backup / "topics_lab" / "number_publisher.py").read_text() == "# my python work"
    assert (ws.src / "topics_lab" / "src" / "number_publisher.cpp").is_file()
    assert ws.migrate_if_build_type_changed("topics_lab", starter) is None  # already C++: untouched


def test_keep_awake_power_request_is_accepted_and_released() -> None:
    from academy.runtime.winjob import keep_awake

    with keep_awake("academy unit test") as active:
        assert active  # Windows accepted the system/execution-required power requests
    with keep_awake("academy unit test, nested use is fine") as again:
        assert again
