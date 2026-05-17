#!/bin/bash
#
# FILE: setup_attacker_vm.sh
# TYPE: ATTACKER VM Script (runs on ATTACKER VM - Ubuntu in VMware)
# PURPOSE: Automated setup script for the Attacker VM.
#          Installs all tools needed to perform the attack simulations:
#          roslibpy, nmap, Wireshark, and configures the VM network.
#
# HOW TO RUN (on fresh Ubuntu VM):
#   chmod +x setup_attacker_vm.sh
#   ./setup_attacker_vm.sh

set -e

echo "=================================================="
echo "  ATTACKER VM SETUP - Cybersecurity Project"
echo "=================================================="

echo ""
echo "[SETUP] Updating package lists..."
sudo apt-get update -y

echo ""
echo "[SETUP] Installing Python 3 and pip..."
sudo apt-get install -y python3 python3-pip python3-venv

echo ""
echo "[SETUP] Installing network tools..."
sudo apt-get install -y \
    nmap \
    wireshark \
    tcpdump \
    netcat-openbsd \
    net-tools \
    iputils-ping \
    curl \
    wget

echo ""
echo "[SETUP] Configuring Wireshark for non-root capture..."
sudo dpkg-reconfigure wireshark-common  # Choose 'Yes' when prompted
sudo usermod -aG wireshark $USER

echo ""
echo "[SETUP] Installing Python attack dependencies..."
pip3 install roslibpy websocket-client

echo ""
echo "[SETUP] Verifying installations..."
echo -n "  Python3: "; python3 --version
echo -n "  pip3:    "; pip3 --version
echo -n "  nmap:    "; nmap --version | head -1
echo -n "  roslibpy: "; python3 -c "import roslibpy; print('OK')" 2>/dev/null || echo "FAILED"

echo ""
echo "[SETUP] Network Configuration Check..."
echo "  Your VM IP addresses:"
hostname -I

echo ""
echo "=================================================="
echo "  SETUP COMPLETE"
echo ""
echo "  NEXT STEPS:"
echo "  1. Note your Host machine IP from 'hostname -I' on the HOST"
echo "  2. Ensure VMware network is set to 'Bridged' or 'Host-Only'"
echo "  3. Start rosbridge on HOST:"
echo "     ros2 launch rosbridge_server rosbridge_websocket_launch.xml"
echo "  4. Run attack scripts:"
echo "     python3 network_scanner.py --host <HOST_IP>"
echo "     python3 attack_eavesdropping.py --host <HOST_IP>"
echo "     python3 attack_message_injection.py --host <HOST_IP>"
echo "     python3 attack_dos.py --host <HOST_IP>"
echo "=================================================="
