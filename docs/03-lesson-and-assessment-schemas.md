# 3. Course, Lesson and Assessment Schemas

The Pydantic models in `backend/academy/content/schema.py` are the normative definition; this
document explains them. Course content is plain files: no code changes are needed to add a lesson.

## 3.1 Course and chapter

```yaml
# courses/mastering_ros2/course.yaml
id: mastering_ros2
title: Mastering ROS 2 — Interactive Robotics Programming
ros_distro: jazzy
sections:
  - {id: essentials, title: ROS Programming Essentials, chapters: [1, 2]}
  ...
# courses/mastering_ros2/chapter_02/chapter.yaml
number: 2
title: Getting Started with ROS 2 Programming
book_chapter: {number: 2, title: "Getting Started with ROS Programming"}
summary: ...
status: available | planned        # planned chapters render in the tree but cannot be opened
lessons: [ch02_pubsub]             # ordered lesson directory names
final_project: ...
```

## 3.2 Lesson (`lessons/<id>/lesson.yaml`)

```yaml
id: ch02_pubsub
title: Building a ROS 2 Publisher and Subscriber
description: ...
book_reference: {chapter: 2, sections: ["Creating a ROS package", "Applications of topics ..."]}
difficulty: beginner                # beginner | intermediate | advanced
estimated_minutes: 60
objectives: [...]
prerequisites: [ch01_first_node]    # lesson ids
ros_dependencies: [rclpy, std_msgs]
skills: [ros2.package.ament_python, ros2.topics.publish, ros2.topics.subscribe, ros2.qos.compatibility]
lab_tabs: [graph, topics, terminal, tests]
workspace:
  package: topics_lab               # package materialised into ws/src from starter/
levels:                             # multiple difficulty levels = different starter scaffolds
  guided: starter                   # TODOs inside mostly-written files
  challenge: starter_challenge      # only package skeleton + spec (optional per lesson)
steps:
  - id: concept
    title: What is a topic?
    kind: read                      # read | code | run | observe | debug | submit
    content: content/01-topics.md   # markdown with ```academy:<widget>``` blocks (interactive)
    completion: {type: manual}
  - id: write_publisher
    kind: code
    content: content/02-publisher.md
    focus_file: topics_lab/topics_lab/number_publisher.py
    hints:                          # exactly levels 1..4 as text; level 5 = reference solution
      - "Conceptual nudge ..."
      - "Which API ..."
      - "Near-code ..."
      - "Pseudo-code ..."
    completion: {type: checkpoint, checkpoint: publisher}
  - id: run_publisher
    kind: run
    completion: {type: graph, node: /number_publisher, publishes: /numbers}
  ...
checkpoints:
  - id: publisher
    title: Publisher behaves correctly
    tests: [test_publisher.py]      # files in tests/, executed only by the grader
  - id: final
    title: Final submission
    tests: [test_publisher.py, test_subscriber.py, test_integration.py, test_hidden.py]
    final: true
completion: {checkpoint: final}     # lesson completes when the final checkpoint passes
```

### Completion types
| type | verified by | meaning |
|---|---|---|
| `manual` | student click | reading steps only |
| `checkpoint` | grader | the named checkpoint's tests all passed in an isolated grader run |
| `graph` | server, from the student's **live** telemetry snapshot | e.g. node X publishes on topic Y (real running code) |
| `graph_qos_mismatch` | server, live snapshot | a publisher/subscriber pair on a topic currently has incompatible QoS (used in the debugging step to confirm the fault was reproduced) |

### Interactive content blocks
Inside markdown, fenced blocks with language `academy:<widget>` and a YAML body become React widgets:
`academy:pubsub-diagram` (animated conceptual graph, editable QoS), `academy:qos-matrix`,
`academy:callout`. Widgets that are *conceptual* are visibly labelled "Concept model — not live data".

## 3.3 Hidden tests and the grader contract

Tests are ordinary pytest files using the `academy_grader` helper library (shipped with the grader,
`backend/grader_support/`). Tests exercise **behaviour** by running the student's built executables:

```python
def test_publisher_rate(ros, evidence):
    with ros.run("topics_lab", "number_publisher"):
        msgs = ros.collect("/numbers", "std_msgs/msg/Int32", seconds=3.0)
    rate = ros.rate(msgs)
    evidence(expected="8–13 Hz", observed=f"{rate:.1f} Hz",
             suggestion="Create the timer with a 0.1 s period.")
    assert 8.0 <= rate <= 13.0
```

`evidence(...)` stores `expected/observed/suggestion` as JUnit `<property>` elements; the grader parses
`junit.xml` into the `results` JSON (doc 02 §2.4). Test ids prefixed `test_hidden_` are reported as
hidden (title shown, inputs not). The grader:

1. Snapshots the student's package source into `data/grader/<submission>/ws/src` (size-limited).
2. Copies `academy_grader` + the checkpoint's test files into a sibling `tests/` dir (never into the student workspace).
3. `colcon build --merge-install` → build failure yields a single `build` result with the log tail.
4. Runs `pytest --junitxml` with a reserved `ROS_DOMAIN_ID`, `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`,
   a Job Object, and a wall-clock timeout; kills the whole tree afterwards.
5. Stores the submission (file snapshot + results) and updates progress/skills.

Grading never inspects source text for specific lines; assertions are on observable ROS behaviour
(graph, messages, rates, QoS, logs as a last resort with grader-chosen hidden values).
