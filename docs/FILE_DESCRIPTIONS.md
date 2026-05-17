# FILE DESCRIPTIONS — Cybersecurity in ROS2 and Gazebo

This document describes every file in the project, where it runs, and what it does.

---

## ROOT LEVEL

### `setup_host.sh`
- **Runs on:** HOST Machine (Ubuntu with ROS2)
- **Type:** Bash setup script
- **Purpose:** One-time automated installer. Sets up ROS2 Humble, Gazebo, TurtleBot3,
  rosbridge, and builds the ROS2 workspace. Run this first on a fresh Ubuntu install.
- **Command:** `./setup_host.sh`

---

## ros2_workspace/ — ROS2 Package (HOST Machine)

All files in this directory run on the **HOST machine** as part of the ROS2 ecosystem.

### `src/robot_controller/package.xml`
- **Runs on:** HOST (used by colcon build system)
- **Type:** ROS2 Package Manifest (XML)
- **Purpose:** Declares the package name, version, and ROS2 dependencies
  (`rclpy`, `geometry_msgs`, `sensor_msgs`, `nav_msgs`). Required by colcon to
  resolve dependencies before building.

### `src/robot_controller/setup.py`
- **Runs on:** HOST (used by colcon build system)
- **Type:** Python setuptools configuration
- **Purpose:** Tells colcon how to install the Python package and registers
  two executable entry points: `robot_controller` and `topic_monitor`.

### `src/robot_controller/resource/robot_controller`
- **Runs on:** HOST (used by ament index)
- **Type:** Empty marker file
- **Purpose:** Required by the ROS2 ament index system to register the package.
  Without this file, `ros2 pkg list` won't find the package.

### `src/robot_controller/launch/robot_launch.py`
- **Runs on:** HOST
- **Type:** ROS2 Launch File (Python)
- **Purpose:** Starts both `robot_controller_node` and `topic_monitor_node` together
  in a single command. This is the main entry point for running the robot system.
- **Command:** `ros2 launch robot_controller robot_launch.py`

### `src/robot_controller/robot_controller/__init__.py`
- **Runs on:** HOST
- **Type:** Python package initializer
- **Purpose:** Makes the `robot_controller` directory a proper Python package,
  required for ROS2 to find and load the node modules.

### `src/robot_controller/robot_controller/robot_controller_node.py`
- **Runs on:** HOST
- **Type:** ROS2 Node (Python)
- **Purpose:** The main robot brain. Publishes velocity commands to `/cmd_vel`
  every 0.5 seconds. Subscribes to `/scan` (LiDAR) to detect obstacles and
  `/odom` to track position. This is the **legitimate controller** that the
  attacker will try to disrupt.
- **Topics used:**
  - Publishes: `/cmd_vel`
  - Subscribes: `/scan`, `/odom`

### `src/robot_controller/robot_controller/topic_monitor_node.py`
- **Runs on:** HOST
- **Type:** ROS2 Node (Python)
- **Purpose:** Security monitor that watches all robot topics for anomalies.
  Detects abnormal message rates (DoS), extreme velocity values (injection),
  and prints statistics every 5 seconds. Acts as the **defender/IDS** in the simulation.
- **Detection capabilities:**
  - DoS: triggers ALERT if message rate exceeds 50 msg/s
  - Injection: warns if velocity commands exceed safe thresholds

---

## gazebo_worlds/ — Gazebo Simulation (HOST Machine)

### `cybersecurity_world.world`
- **Runs on:** HOST (loaded by Gazebo)
- **Type:** Gazebo World File (SDF/XML)
- **Purpose:** Defines the 3D simulation environment — a walled room with two
  obstacles and a TurtleBot3 Burger robot. This is the virtual space where you
  visually observe the impact of cyberattacks on robot behavior.
- **Command:** `gazebo gazebo_worlds/cybersecurity_world.world`
  (or use the TurtleBot3 launch file which loads its own world)

---

## attacker_vm/ — Attack Scripts (ATTACKER VM)

All files in this directory run on the **Attacker VM** (Ubuntu in VMware).
They require `rosbridge` to be running on the HOST machine.

### `setup_attacker_vm.sh`
- **Runs on:** ATTACKER VM
- **Type:** Bash setup script
- **Purpose:** One-time setup for the attacker VM. Installs Python 3, roslibpy,
  nmap, Wireshark, and tcpdump. Run this first on a fresh VM install.
- **Command:** `./setup_attacker_vm.sh`

### `network_scanner.py`
- **Runs on:** ATTACKER VM
- **Type:** Python reconnaissance script
- **Purpose:** **Phase 1 — Reconnaissance.** Scans the target network for open
  ROS2-related ports (9090 for rosbridge, 7400 for DDS), then connects to rosbridge
  to enumerate all active nodes and topics. This is the discovery phase before
  launching active attacks.
- **Command:** `python3 network_scanner.py --host <HOST_IP>`
- **Output:** `recon_results.json` with all discovered information

### `attack_eavesdropping.py`
- **Runs on:** ATTACKER VM
- **Type:** Python attack script
- **Purpose:** **Phase 2 — Eavesdropping.** Silently subscribes to `/odom`, `/scan`,
  and `/cmd_vel` topics to steal robot position, LiDAR environment data, and movement
  commands. Demonstrates that without SROS2, all robot data is transmitted in plaintext
  over the network.
- **Command:** `python3 attack_eavesdropping.py --host <HOST_IP> --duration 30`
- **Output:** `stolen_data.json` with intercepted robot data

### `attack_message_injection.py`
- **Runs on:** ATTACKER VM
- **Type:** Python attack script
- **Purpose:** **Phase 3 — Message Injection / Spoofing.** Publishes fake velocity
  commands to `/cmd_vel` at high frequency to override the legitimate robot controller.
  Offers two modes: `spin` (forces continuous rotation) and `reverse` (drives robot
  backward). Visually observable in Gazebo.
- **Command:** `python3 attack_message_injection.py --host <HOST_IP> --attack spin`

### `attack_dos.py`
- **Runs on:** ATTACKER VM
- **Type:** Python attack script
- **Purpose:** **Phase 4 — Denial of Service.** Floods ROS2 topics with hundreds
  of messages per second using multiple threads, saturating the DDS communication
  layer. Causes legitimate commands to be dropped, increasing latency and making
  the robot unresponsive. The `topic_monitor_node` on HOST will detect and alert.
- **Command:** `python3 attack_dos.py --host <HOST_IP> --rate 500 --duration 20`

---

## mitigation/ — Defense Scripts (HOST Machine)

### `setup_sros2_security.sh`
- **Runs on:** HOST
- **Type:** Bash mitigation script
- **Purpose:** Enables SROS2 (Secure ROS2) by generating a security keystore,
  creating DDS certificates for each node, and exporting environment variables
  that activate encryption and authentication. After running this, the eavesdropping
  and injection attacks will fail because DDS traffic is encrypted and unauthorized
  publishers are rejected.
- **Command:** `./mitigation/setup_sros2_security.sh`
- **Mitigates:** Eavesdropping, Message Injection

### `qos_protection_node.py`
- **Runs on:** HOST
- **Type:** ROS2 Node (Python)
- **Purpose:** A rate-limiting proxy node that acts as a firewall for `/cmd_vel`.
  It sits between the network and the robot controller, dropping messages that exceed
  20 Hz, clamping velocity values to safe limits, and logging alerts when flooding
  is detected. Effectively neutralizes the DoS attack.
- **Command:** `python3 mitigation/qos_protection_node.py`
- **Mitigates:** DoS (Topic Flooding)

---

## docs/

### `HOW_TO_RUN.md`
- Step-by-step instructions to set up and run the entire project,
  from initial installation through all attack phases and mitigations.

### `FILE_DESCRIPTIONS.md`
- This file. Reference guide for every file in the project.

---

## Attack vs. Mitigation Summary

| Attack Script              | What It Demonstrates          | Mitigation File               |
|----------------------------|-------------------------------|-------------------------------|
| `network_scanner.py`       | Open port / topic discovery   | Network isolation / firewalls |
| `attack_eavesdropping.py`  | Plaintext DDS data leakage    | `setup_sros2_security.sh`     |
| `attack_message_injection.py` | Unauthenticated publishing  | `setup_sros2_security.sh`     |
| `attack_dos.py`            | Topic flooding / DoS          | `qos_protection_node.py`      |
