# Reading list: robotics real-time / systems role

Requirement numbers (R1–R8) refer to the job description:
R1 real-time C++ / PREEMPT_RT · R2 concurrency & distributed systems · R3 ros2_control · R4 fieldbus ·
R5 multi-host DDS · R6 Linux systems · R7 Ansible/Docker/K8s · R8 x86 RT benchmarking.

## Downloaded here (free, official sources)

| File | Covers | Source |
|---|---|---|
| Drepper_What_Every_Programmer_Should_Know_About_Memory.pdf | R8 caches, NUMA, cache contention | akkadia.org (author) |
| Gregg_Systems_Performance_2E_publisher_sample.pdf | Sample pages + full TOC of *Systems Performance* | ciscopress.com (publisher) |
| ODVA_EtherNetIP_Technology_Overview_PUB00138R8.pdf | R4 EtherNet/IP | odva.org |
| ODVA_CIP_Brochure_PUB00122R2.pdf | R4 CIP (the protocol family behind EtherNet/IP) | odva.org |

## Free, but download manually in a browser (sites blocked scripted downloads)

| Document | Covers | URL |
|---|---|---|
| *Linux Kernel Programming 2E*, free online Chapter 1 | R6 | http://www.packtpub.com/sites/default/files/downloads/9781803232225_Online_Chapter.pdf |
| ETG brochure "EtherCAT – the Ethernet Fieldbus" | R4 | https://ethercat.org/en/downloads/downloads_07CC7DD0539B4C0EB526ADD5D4BC25CD.htm |
| Red Hat "Optimizing RHEL 9 for Real Time for low latency operation" (PDF button on the page) | R1, R8 BIOS/IRQ/isolation | https://docs.redhat.com/en/documentation/red_hat_enterprise_linux_for_real_time/9 |

## Web-only official docs (read online)

**Real-time (R1, R3, R8)**
- ROS 2 Real-Time Working Group: https://ros-realtime.github.io
- Shuhao Wu, "Real-time programming with Linux" (4 parts): https://shuhaowu.com/blog/2022/01-linux-rt-appdev-part1.html
- Linux Foundation realtime wiki: https://wiki.linuxfoundation.org/realtime/start
- Kernel docs: rtla / timerlat / osnoise: https://docs.kernel.org/tools/rtla/index.html
- Kernel parameters (isolcpus, nohz_full, irqaffinity): https://docs.kernel.org/admin-guide/kernel-parameters.html
- IRQ affinity: https://docs.kernel.org/core-api/irq/irq-affinity.html
- resctrl (Intel RDT cache allocation): https://docs.kernel.org/arch/x86/resctrl.html
- Intel TCC (Time Coordinated Computing): search "Intel TCC Tools documentation" on intel.com

**ros2_control (R3)**
- https://control.ros.org/jazzy/ (Writing a Hardware Component, Writing a new controller)
- https://github.com/ros-controls/ros2_control_demos
- https://github.com/ros-controls/realtime_tools

**ROS 2 / DDS (R2, R5)**
- Executors: https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Executors.html
- Callback groups: https://docs.ros.org/en/jazzy/How-To-Guides/Using-callback-groups.html
- QoS: https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html
- DDS tuning: https://docs.ros.org/en/jazzy/How-To-Guides/DDS-tuning.html
- Discovery range / static peers: https://docs.ros.org/en/jazzy/Tutorials/Advanced/Improved-Dynamic-Discovery.html
- Cyclone DDS: https://cyclonedds.io/docs/
- Fast DDS: https://fast-dds.docs.eprosima.com/
- ros2_tracing: https://github.com/ros2/ros2_tracing

**Fieldbus (R4)**
- SocketCAN: https://docs.kernel.org/networking/can.html
- ros2_canopen: https://ros-industrial.github.io/ros2_canopen/manual/rolling/
- ethercat_driver_ros2: https://icube-robotics.github.io/ethercat_driver_ros2/
- CSS Electronics CAN / CANopen guides: https://www.csselectronics.com/pages/can-bus-simple-intro-tutorial

**Linux & infrastructure (R6, R7)**
- netplan: https://netplan.readthedocs.io
- cgroup v2: https://docs.kernel.org/admin-guide/cgroup-v2.html
- Dynamic debug: https://docs.kernel.org/admin-guide/dynamic-debug-howto.html
- Ansible getting started: https://docs.ansible.com/ansible/latest/getting_started/index.html
- Docker get started: https://docs.docker.com/get-started/
- Kubernetes basics: https://kubernetes.io/docs/tutorials/kubernetes-basics/

## Books to buy (not freely available)

| Book | ISBN | Notes |
|---|---|---|
| *Mastering ROS 2 for Robotics Programming*, 4th ed., Joseph & Cacace (Packt, 2025) | 978-1836209010 | Code: github.com/PacktPublishing/Mastering-ROS-2-for-Robotics-Programming |
| *Linux Kernel Programming*, 2nd ed., Billimoria (Packt, 2024) | 978-1803232225 | Code: github.com/PacktPublishing/Linux-Kernel-Programming_2E |
| *Systems Performance*, 2nd ed., Gregg (Pearson, 2020) | 978-0136820154 | Tools: github.com/brendangregg/perf-tools |
| Optional: *C++ Concurrency in Action*, 2nd ed., Williams (Manning, 2019) | 978-1617294693 | Only gap for R2 user-space concurrency |
