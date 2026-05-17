#!/bin/bash
#
# FILE: setup_sros2_security.sh
# TYPE: Mitigation Script (runs on HOST machine)
# PURPOSE: Enables SROS2 (Secure ROS2) security features to protect robot
#          communication against the demonstrated attacks.
#          Implements authentication and encryption for DDS communication.
#
# HOW TO RUN (on HOST machine):
#   chmod +x setup_sros2_security.sh
#   ./setup_sros2_security.sh
#
# MITIGATES:
#   - Message injection (command spoofing)
#   - Eavesdropping (data interception)
#   - Unauthorized node connections

set -e

KEYSTORE_DIR="$HOME/ros2_security_keystore"

echo "=================================================="
echo "  SROS2 SECURITY SETUP - Mitigation Implementation"
echo "=================================================="

echo ""
echo "[SROS2] Step 1: Installing SROS2 tools..."
sudo apt-get install -y \
    ros-humble-rmw-fastrtps-cpp \
    ros-humble-rmw-cyclonedds-cpp

echo ""
echo "[SROS2] Step 2: Creating security keystore at $KEYSTORE_DIR..."
mkdir -p "$KEYSTORE_DIR"
ros2 security create_keystore "$KEYSTORE_DIR"
echo "  ✓ Keystore created"

echo ""
echo "[SROS2] Step 3: Generating keys for robot_controller node..."
ros2 security create_enclave "$KEYSTORE_DIR" /robot_controller
echo "  ✓ robot_controller enclave created"

echo ""
echo "[SROS2] Step 4: Generating keys for topic_monitor node..."
ros2 security create_enclave "$KEYSTORE_DIR" /topic_monitor
echo "  ✓ topic_monitor enclave created"

echo ""
echo "[SROS2] Step 5: Exporting security environment variables..."

EXPORT_LINES="
# SROS2 Security Configuration
export ROS_SECURITY_ENABLE=true
export ROS_SECURITY_STRATEGY=Enforce
export ROS_SECURITY_KEYSTORE=$KEYSTORE_DIR
"

# Add to ~/.bashrc if not already present
if ! grep -q "ROS_SECURITY_ENABLE" ~/.bashrc; then
    echo "$EXPORT_LINES" >> ~/.bashrc
    echo "  ✓ Added security variables to ~/.bashrc"
else
    echo "  ✓ Security variables already in ~/.bashrc"
fi

# Also export for current session
export ROS_SECURITY_ENABLE=true
export ROS_SECURITY_STRATEGY=Enforce
export ROS_SECURITY_KEYSTORE="$KEYSTORE_DIR"

echo ""
echo "[SROS2] Step 6: Verifying security configuration..."
echo "  ROS_SECURITY_ENABLE   = $ROS_SECURITY_ENABLE"
echo "  ROS_SECURITY_STRATEGY = $ROS_SECURITY_STRATEGY"
echo "  ROS_SECURITY_KEYSTORE = $ROS_SECURITY_KEYSTORE"

echo ""
echo "[SROS2] Step 7: Displaying keystore contents..."
ls -la "$KEYSTORE_DIR/"

echo ""
echo "=================================================="
echo "  SROS2 SETUP COMPLETE"
echo ""
echo "  SECURITY FEATURES NOW ACTIVE:"
echo "  ✓ Node authentication (DDS Identity/Permissions certificates)"
echo "  ✓ Topic encryption (AES-128/256)"
echo "  ✓ Access control (only authorized nodes can publish/subscribe)"
echo ""
echo "  RE-RUN THE ATTACKS TO VERIFY THEY ARE NOW BLOCKED:"
echo "  - Eavesdropping: DDS traffic is now encrypted"
echo "  - Message injection: Unauthorized publishers rejected"
echo "  - DoS: QoS limits still apply separately (see setup_qos.py)"
echo ""
echo "  LAUNCH NODES WITH SECURITY:"
echo "  ros2 launch robot_controller robot_launch.py"
echo "  (security vars are auto-loaded from environment)"
echo "=================================================="
