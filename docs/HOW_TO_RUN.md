# HOW TO RUN — Cybersecurity in ROS2 and Gazebo Simulation

## Project Overview

This project simulates cyberattacks on an autonomous robot (TurtleBot3) running in Gazebo,
using a separate Attacker VM to demonstrate ROS2 communication vulnerabilities.

---

## System Requirements

| Machine       | OS            | Software                              |
|---------------|---------------|---------------------------------------|
| Host Machine  | Ubuntu 22.04  | ROS2 Humble, Gazebo, VMware           |
| Attacker VM   | Ubuntu 22.04  | Python 3, roslibpy, nmap, Wireshark   |

---

## Directory Structure

```
ros2_cybersecurity_project/
│
├── setup_host.sh                         ← HOST: One-time setup script
│
├── ros2_workspace/                       ← HOST: All ROS2 code
│   └── src/
│       └── robot_controller/
│           ├── package.xml               ← ROS2: Package manifest
│           ├── setup.py                  ← ROS2: Build configuration
│           ├── resource/                 ← ROS2: Package resource marker
│           ├── launch/
│           │   └── robot_launch.py       ← ROS2: Launches all nodes together
│           └── robot_controller/
│               ├── __init__.py           ← ROS2: Python package init
│               ├── robot_controller_node.py  ← ROS2: Main robot movement logic
│               └── topic_monitor_node.py     ← ROS2: Anomaly detection monitor
│
├── gazebo_worlds/
│   └── cybersecurity_world.world         ← GAZEBO: 3D simulation environment
│
├── attacker_vm/                          ← ATTACKER VM: All attack scripts
│   ├── setup_attacker_vm.sh              ← ATTACKER VM: One-time setup
│   ├── network_scanner.py                ← ATTACKER VM: Phase 1 - Reconnaissance
│   ├── attack_eavesdropping.py           ← ATTACKER VM: Phase 2 - Eavesdropping
│   ├── attack_message_injection.py       ← ATTACKER VM: Phase 3 - Spoofing
│   └── attack_dos.py                     ← ATTACKER VM: Phase 4 - DoS Flood
│
├── mitigation/
│   ├── setup_sros2_security.sh           ← HOST: Enable SROS2 encryption
│   └── qos_protection_node.py            ← HOST: Rate-limiting proxy node
│
└── docs/
    ├── HOW_TO_RUN.md                     ← (this file)
    └── FILE_DESCRIPTIONS.md              ← Detailed file reference
```

---

## PART 1 — HOST MACHINE SETUP

### Step 1.1 — Run the automated setup script

```bash
cd ros2_cybersecurity_project/
chmod +x setup_host.sh
./setup_host.sh
```

This installs: ROS2 Humble, Gazebo, TurtleBot3, rosbridge, and builds the workspace.

### Step 1.2 — Source the workspace (new terminals)

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_cybersecurity_project/ros2_workspace/install/setup.bash
export TURTLEBOT3_MODEL=burger
```

> **Tip:** Add these lines to `~/.bashrc` so they run automatically.

### Step 1.3 — Find your Host IP address

```bash
hostname -I
```

Note this IP — you will enter it in the Attacker VM scripts.

---

## PART 2 — ATTACKER VM SETUP

### Step 2.1 — VMware Network Configuration

In VMware Workstation:
1. Go to **VM → Settings → Network Adapter**
2. Set network mode to **Bridged** (so the VM is on the same network as the Host)
3. Or use **Host-Only** if you want full isolation

### Step 2.2 — Run the attacker setup script

```bash
cd attacker_vm/
chmod +x setup_attacker_vm.sh
./setup_attacker_vm.sh
```

### Step 2.3 — Verify connectivity

```bash
# Replace with your actual Host IP
ping 192.168.1.100
```

---

## PART 3 — RUNNING THE SIMULATION

Open **4 separate terminals** on the HOST machine:

### Terminal 1 — Launch Gazebo Simulation

```bash
source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py
```

Wait for Gazebo to open and the TurtleBot3 robot to appear in the world.

### Terminal 2 — Launch ROS2 Robot Nodes

```bash
source /opt/ros/humble/setup.bash
source ros2_cybersecurity_project/ros2_workspace/install/setup.bash
ros2 launch robot_controller robot_launch.py
```

You should see the robot start moving in Gazebo.

### Terminal 3 — Start ROS Bridge (for Attacker VM)

```bash
source /opt/ros/humble/setup.bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

This opens port **9090** — the bridge between the Attacker VM and ROS2.

### Terminal 4 — Monitor Topics (optional verification)

```bash
source /opt/ros/humble/setup.bash
ros2 topic list          # See all active topics
ros2 topic hz /cmd_vel   # Monitor /cmd_vel message rate
```

---

## PART 4 — RUNNING THE ATTACKS (on Attacker VM)

### Attack 0 — Reconnaissance (Network Scanner)

```bash
python3 network_scanner.py --host 192.168.1.100
```

**Expected:** Lists open ROS ports, active nodes, and available topics.

---

### Attack 1 — Eavesdropping

```bash
python3 attack_eavesdropping.py --host 192.168.1.100 --duration 30
```

**Expected:** Prints stolen robot position (`/odom`) and LiDAR data (`/scan`) in real-time.
Saved to `stolen_data.json`.

---

### Attack 2 — Message Injection (Spoofing)

```bash
# Make the robot spin uncontrollably
python3 attack_message_injection.py --host 192.168.1.100 --attack spin --duration 15

# Make the robot drive in reverse
python3 attack_message_injection.py --host 192.168.1.100 --attack reverse --duration 15
```

**Expected:** Robot in Gazebo starts spinning or reversing against its programmed logic.

---

### Attack 3 — Denial of Service

```bash
# Flood single topic
python3 attack_dos.py --host 192.168.1.100 --rate 500 --duration 20

# Flood all topics simultaneously
python3 attack_dos.py --host 192.168.1.100 --mode multi --duration 20
```

**Expected:** The `topic_monitor_node` on the HOST prints ALERT messages.
Robot movement becomes unstable or stops responding.

---

## PART 5 — MITIGATION (Back on HOST)

### Mitigation 1 — Enable SROS2 Encryption

```bash
chmod +x mitigation/setup_sros2_security.sh
./mitigation/setup_sros2_security.sh
```

Re-run the attacks. Eavesdropping and injection attacks should now fail.

### Mitigation 2 — Enable QoS Rate Limiting

```bash
# Run the QoS protection proxy node
python3 mitigation/qos_protection_node.py
```

Re-run the DoS attack. Excess messages will be blocked and logged.

---

## PART 6 — Wireshark Traffic Analysis

On the Attacker VM, capture ROS2 DDS traffic:

```bash
# List network interfaces
ip a

# Capture on your bridged interface (e.g., ens33)
sudo wireshark &

# Or via tcpdump
sudo tcpdump -i ens33 -w ros2_capture.pcap udp port 7400
```

**What to look for:**
- **Without SROS2:** DDS messages visible in plain UDP — robot data readable
- **With SROS2:** DDS traffic encrypted — content unreadable

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Gazebo won't launch | Run `killall gzserver gzclient` then retry |
| `ros2: command not found` | Run `source /opt/ros/humble/setup.bash` |
| Attacker can't connect | Check `ros2 launch rosbridge_server` is running, check firewall: `sudo ufw allow 9090` |
| TurtleBot3 not found | Run `export TURTLEBOT3_MODEL=burger` |
| `roslibpy` not found on VM | Run `pip3 install roslibpy` |
| Robot not moving in Gazebo | Check Terminal 2 shows robot_controller running |

---

## Quick Reference — ROS2 Topics

| Topic      | Type                        | Description                        |
|------------|-----------------------------|------------------------------------|
| `/cmd_vel` | `geometry_msgs/Twist`       | Robot velocity commands (attacked) |
| `/scan`    | `sensor_msgs/LaserScan`     | LiDAR sensor data (eavesdropped)   |
| `/odom`    | `nav_msgs/Odometry`         | Robot position and velocity        |
