#!/bin/bash
#
# FILE: setup_host.sh
# TYPE: HOST Machine Script (runs on HOST machine - Ubuntu with ROS2)
# PURPOSE: One-time setup script for the HOST machine.
#          Installs ROS2 Humble, Gazebo, TurtleBot3, rosbridge, and builds
#          the ROS2 workspace for this project.
#
# HOW TO RUN:
#   chmod +x setup_host.sh
#   ./setup_host.sh

set -e

echo "=================================================="
echo "  HOST MACHINE SETUP - ROS2 Cybersecurity Project"
echo "=================================================="

# ── Step 1: ROS2 Humble ──────────────────────────────
echo ""
echo "[SETUP] Step 1: Installing ROS2 Humble..."
if ! command -v ros2 &> /dev/null; then
    sudo apt-get install -y software-properties-common curl
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
        -o /usr/share/keyrings/ros-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
        http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
        | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y ros-humble-desktop python3-colcon-common-extensions
    echo "  ✓ ROS2 Humble installed"
else
    echo "  ✓ ROS2 already installed"
fi

# ── Step 2: Source ROS2 ──────────────────────────────
if ! grep -q "source /opt/ros/humble/setup.bash" ~/.bashrc; then
    echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
fi
source /opt/ros/humble/setup.bash

# ── Step 3: Gazebo ───────────────────────────────────
echo ""
echo "[SETUP] Step 2: Installing Gazebo Classic..."
sudo apt-get install -y gazebo ros-humble-gazebo-ros-pkgs

# ── Step 4: TurtleBot3 ───────────────────────────────
echo ""
echo "[SETUP] Step 3: Installing TurtleBot3..."
sudo apt-get install -y \
    ros-humble-turtlebot3 \
    ros-humble-turtlebot3-gazebo \
    ros-humble-turtlebot3-simulations

if ! grep -q "TURTLEBOT3_MODEL" ~/.bashrc; then
    echo "export TURTLEBOT3_MODEL=burger" >> ~/.bashrc
fi
export TURTLEBOT3_MODEL=burger

# ── Step 5: rosbridge ────────────────────────────────
echo ""
echo "[SETUP] Step 4: Installing rosbridge (needed for attacker VM)..."
sudo apt-get install -y ros-humble-rosbridge-suite

# ── Step 6: Build workspace ──────────────────────────
echo ""
echo "[SETUP] Step 5: Building ROS2 workspace..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$SCRIPT_DIR/ros2_workspace"

cd "$WS_DIR"
source /opt/ros/humble/setup.bash
colcon build --symlink-install
echo "  ✓ Workspace built"

if ! grep -q "ros2_workspace/install/setup.bash" ~/.bashrc; then
    echo "source $WS_DIR/install/setup.bash" >> ~/.bashrc
fi
source "$WS_DIR/install/setup.bash"

echo ""
echo "=================================================="
echo "  SETUP COMPLETE"
echo ""
echo "  YOUR HOST IP (share with Attacker VM):"
hostname -I | awk '{print "  " $1}'
echo ""
echo "  TO START THE SIMULATION:"
echo ""
echo "  Terminal 1 - Launch Gazebo:"
echo "    export TURTLEBOT3_MODEL=burger"
echo "    ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py"
echo ""
echo "  Terminal 2 - Launch ROS2 nodes:"
echo "    source $WS_DIR/install/setup.bash"
echo "    ros2 launch robot_controller robot_launch.py"
echo ""
echo "  Terminal 3 - Start rosbridge (for attacker VM):"
echo "    ros2 launch rosbridge_server rosbridge_websocket_launch.xml"
echo ""
echo "  See docs/HOW_TO_RUN.md for full instructions"
echo "=================================================="
