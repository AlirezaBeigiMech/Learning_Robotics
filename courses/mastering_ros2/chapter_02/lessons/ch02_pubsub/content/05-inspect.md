## Inspect the messages

Click the `/numbers` topic, in the graph or in the **Topic Inspector** tab. The inspector subscribes
to the topic and shows:

* the **message type** and each publisher's/subscriber's **QoS**
* the **measured rate** (it should hover around 10 Hz)
* the latest messages as structured data
* a live **chart** of every numeric field. Here that is `data`, a straight rising line.

Things to try:

* Stop the publisher. The rate drops to 0 and the node disappears from the graph within ~3 s.
* Change the timer period to `500ms`, rebuild, run again and watch the rate change.
  Put it back to `100ms` before you continue.

```academy:callout
kind: note
title: Measuring vs. trusting
body: |
  The rate shown here is measured from real message arrival times. It is the same kind of evidence
  the grader collects. If your code says 10 Hz but the inspector says 5 Hz, the inspector is right.
```
