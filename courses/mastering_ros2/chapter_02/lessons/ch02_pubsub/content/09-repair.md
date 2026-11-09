## Diagnose and repair

You know the symptom and you have the evidence. Now fix the problem. You have two valid options:

* make the **publisher RELIABLE** again, or
* make the **subscriber BEST_EFFORT**. A best-effort reader accepts data from either kind of writer.

Which is better here? Counting numbers is data where every sample matters, so **reliable** is the
better match. Best-effort suits high-rate sensor streams, where a fresh sample beats a retransmitted
old one.

Repair the publisher, rebuild, and run **Check: Publisher ↔ subscriber integration**. The grader runs
*both* of your nodes together. It checks that their QoS profiles are compatible and that your subscriber
received an unbroken sequence from your publisher.

```academy:callout
kind: note
title: The general method
body: |
  1. Reproduce. 2. Observe the symptom. 3. Collect telemetry (graph, QoS, logs).
  4. Form a hypothesis. 5. Change one thing. 6. Verify by behaviour, not by reading the code.
```
