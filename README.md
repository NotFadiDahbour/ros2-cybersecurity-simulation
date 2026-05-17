# 🤖🔐 ROS2 Cybersecurity Simulation

> Demonstrating real-world cyberattack vectors against autonomous robotic systems using ROS2 Humble, Gazebo simulation, and a dedicated attacker VM — with hands-on mitigations via SROS2 and QoS rate-limiting.

---

## 📋 Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Attack Phases](#attack-phases)
- [Mitigations](#mitigations)
- [Requirements](#requirements)
- [Documentation](#documentation)
- [Academic Context](#academic-context)

---

## Overview

This project simulates a **realistic multi-stage cyberattack campaign** targeting a TurtleBot3 autonomous robot navigating a Gazebo 3D environment. The robot runs a **Bug2 navigation algorithm** and communicates over **ROS2's DDS middleware** — demonstrating how unprotected robotic systems are vulnerable to network-level attacks.

The setup uses two machines:
- **Host Machine** — runs ROS2, Gazebo, and the robot controller
- **Attacker VM** — simulates an adversary on the same network

The project covers the full attack lifecycle: reconnaissance → eavesdropping → command injection → denial of service, followed by corresponding SROS2-based mitigations.

---

## System Architecture

```
┌──────────────────────────────────────────┐       ┌──────────────────────────┐
│              HOST MACHINE                │       │       ATTACKER VM        │
│         (Ubuntu 22.04 + ROS2)            │       │      (Ubuntu 22.04)      │
│                                          │       │                          │
│  ┌────────────────────────────────────┐  │  LAN  │  network_scanner.py      │
│  │  Gazebo Simulation (TurtleBot3)    │◄─┼───────┤  attack_eavesdropping.py │
│  └─────────────────┬──────────────────┘  │       │  attack_message_         │
│                    │ /scan /odom          │       │    injection.py          │
│  ┌─────────────────▼──────────────────┐  │       │  attack_dos.py           │
│  │  robot_controller_node (Bug2 Nav)  │  │       └──────────────────────────┘
│  └─────────────────┬──────────────────┘  │
│                    │ /cmd_vel             │
│  ┌─────────────────▼──────────────────┐  │
│  │  topic_monitor_node (IDS / Alert)  │  │
│  └────────────────────────────────────┘  │
│                                          │
│  rosbridge_server (port 9090) ───────────┼──── Attacker entry point
└──────────────────────────────────────────┘
```

---

## Project Structure

```
ros2_cybersecurity_project/
│
├── setup_host.sh                        # One-time host setup (ROS2, Gazebo, build)
│
├── ros2_workspace/                      # ROS2 package — runs on HOST
│   └── src/robot_controller/
│       ├── package.xml                  # ROS2 package manifest
│       ├── setup.py                     # colcon build configuration
│       ├── launch/
│       │   ├── robot_launch.py          # Launches all nodes
│       │   └── simple_world_launch.py   # Minimal launch (no Gazebo)
│       └── robot_controller/
│           ├── robot_controller_node.py # Bug2 navigation algorithm
│           └── topic_monitor_node.py    # Anomaly detection / IDS node
│
├── gazebo_worlds/
│   ├── cybersecurity_world.world        # Full walled environment with obstacles
│   └── simple_world.world              # Minimal environment for quick tests
│
├── attacker_vm/                         # Attack scripts — run on ATTACKER VM
│   ├── setup_attacker_vm.sh            # One-time attacker VM setup
│   ├── network_scanner.py              # Phase 1: Reconnaissance
│   ├── attack_eavesdropping.py         # Phase 2: Data interception
│   ├── attack_message_injection.py     # Phase 3: Command spoofing
│   └── attack_dos.py                   # Phase 4: Denial of Service
│
├── mitigation/                          # Defense scripts — run on HOST
│   ├── setup_sros2_security.sh         # Enable SROS2 encryption & auth
│   └── qos_protection_node.py          # Rate-limiting proxy (DoS defense)
│
└── docs/
    ├── HOW_TO_RUN.md                   # Full setup and run guide
    └── FILE_DESCRIPTIONS.md            # Detailed description of every file
```

---

## Quick Start

### 1. Host Machine Setup

```bash
git clone https://github.com/<your-username>/ros2_cybersecurity_project.git
cd ros2_cybersecurity_project
chmod +x setup_host.sh
./setup_host.sh
```

### 2. Attacker VM Setup

```bash
chmod +x attacker_vm/setup_attacker_vm.sh
./attacker_vm/setup_attacker_vm.sh
```

### 3. Launch the Robot

```bash
source /opt/ros/humble/setup.bash
source ros2_workspace/install/setup.bash
ros2 launch robot_controller robot_launch.py
```

> See [`docs/HOW_TO_RUN.md`](docs/HOW_TO_RUN.md) for the complete step-by-step guide.

---

## Attack Phases

| Phase | Script | Attack Type | Effect |
|-------|--------|-------------|--------|
| 1 | `attacker_vm/network_scanner.py` | **Reconnaissance** | Discovers open ROS2 ports and enumerates all active topics/nodes |
| 2 | `attacker_vm/attack_eavesdropping.py` | **Eavesdropping** | Silently intercepts plaintext `/odom`, `/scan`, `/cmd_vel` data |
| 3 | `attacker_vm/attack_message_injection.py` | **Command Spoofing** | Overrides the robot controller with fake velocity commands |
| 4 | `attacker_vm/attack_dos.py` | **Denial of Service** | Floods DDS topics at 500 msg/s, causing the robot to become unresponsive |

### Running Attacks

```bash
# Phase 1 — Reconnaissance
python3 attacker_vm/network_scanner.py --host <HOST_IP>

# Phase 2 — Eavesdropping (30 seconds)
python3 attacker_vm/attack_eavesdropping.py --host <HOST_IP> --duration 30

# Phase 3 — Message Injection (spin mode)
python3 attacker_vm/attack_message_injection.py --host <HOST_IP> --attack spin

# Phase 4 — Denial of Service
python3 attacker_vm/attack_dos.py --host <HOST_IP> --rate 500 --duration 20
```

---

## Mitigations

| Attack | Mitigation | How it Works |
|--------|-----------|--------------|
| Eavesdropping | `mitigation/setup_sros2_security.sh` | Enables SROS2 — generates DDS certificates, activates TLS encryption |
| Message Injection | `mitigation/setup_sros2_security.sh` | Cryptographic node authentication rejects unauthorized publishers |
| Denial of Service | `mitigation/qos_protection_node.py` | Rate-limiting proxy drops messages above 20 Hz; clamps velocity to safe bounds |

### Applying Mitigations

```bash
# Enable SROS2 (covers eavesdropping + injection)
chmod +x mitigation/setup_sros2_security.sh
./mitigation/setup_sros2_security.sh

# Start QoS protection node (covers DoS)
python3 mitigation/qos_protection_node.py
```

---

## Requirements

| Component | Version |
|-----------|---------|
| OS | Ubuntu 22.04 LTS |
| ROS2 | Humble Hawksbill |
| Gazebo | Classic 11 |
| Python | 3.10+ |
| TurtleBot3 | `turtlebot3_gazebo` package |
| rosbridge | `rosbridge_suite` |
| Attacker VM | Python 3, `roslibpy`, `nmap`, `wireshark`, `tcpdump` |

---

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/HOW_TO_RUN.md`](docs/HOW_TO_RUN.md) | Full step-by-step setup, run, and attack guide |
| [`docs/FILE_DESCRIPTIONS.md`](docs/FILE_DESCRIPTIONS.md) | Detailed explanation of every file in the project |

---

## Academic Context

This project was developed as part of a cybersecurity study on **vulnerabilities in ROS2-based autonomous robotic systems**. It provides a reproducible research environment for demonstrating:

- The attack surface exposed by unprotected DDS/ROS2 middleware
- The effectiveness of SROS2 as a cryptographic defense layer
- Intrusion detection via anomaly monitoring at the topic level
- Rate-based denial-of-service defense using QoS policies

---

## ⚠️ Disclaimer

This project is intended **strictly for educational and research purposes**. All attack scripts are designed to target systems you own and control. Never run these scripts against systems without explicit written authorization.

---

## License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE) for details.
