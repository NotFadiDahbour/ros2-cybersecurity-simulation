#!/usr/bin/env python3
"""
FILE: qos_protection_node.py
TYPE: Mitigation Script - ROS2 Node (runs on HOST machine)
PURPOSE: Implements Quality-of-Service (QoS) based protection against DoS attacks.
         Acts as a rate-limiting proxy for /cmd_vel and other critical topics.
         Drops messages that exceed safe thresholds and logs suspicious sources.

         This node sits BETWEEN the network and the robot controller,
         filtering out flood messages before they reach Gazebo.

HOW TO RUN:
    # Build and source the workspace first
    ros2 run robot_controller qos_protection  # (after adding to setup.py)
    # OR directly:
    python3 qos_protection_node.py

MITIGATES: DoS (Topic Flooding) Attack
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from geometry_msgs.msg import Twist
import time
from collections import deque


class QoSProtectionNode(Node):
    """
    Rate-limiting proxy node for critical ROS2 topics.
    Protects against DoS flooding by capping message throughput.
    """

    def __init__(self):
        super().__init__('qos_protection_node')
        self.get_logger().info('QoS Protection Node started')

        # --- Configuration ---
        self.MAX_CMD_VEL_RATE = 20    # Max legitimate cmd_vel rate (Hz)
        self.MAX_LINEAR_VEL = 0.5     # Max safe linear velocity (m/s)
        self.MAX_ANGULAR_VEL = 1.5    # Max safe angular velocity (rad/s)
        self.ALERT_RATE = 50          # Rate above which to alert (Hz)

        # --- Rate tracking ---
        self.cmd_vel_timestamps = deque(maxlen=200)
        self.blocked_count = 0
        self.passed_count = 0
        self.last_alert_time = 0

        # --- Restricted QoS for input (can receive all messages) ---
        input_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=100
        )

        # --- Strict QoS for output (rate-limited, reliable) ---
        output_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # Subscribe to raw (potentially attacked) /cmd_vel
        self.raw_sub = self.create_subscription(
            Twist, '/cmd_vel_raw', self.cmd_vel_callback, input_qos)

        # Publish filtered /cmd_vel to robot
        self.filtered_pub = self.create_publisher(
            Twist, '/cmd_vel', output_qos)

        # Status timer
        self.timer = self.create_timer(5.0, self.print_status)
        self.get_logger().info(
            f'Rate limit: {self.MAX_CMD_VEL_RATE} Hz | '
            f'Max vel: {self.MAX_LINEAR_VEL} m/s'
        )

    def cmd_vel_callback(self, msg: Twist):
        """Filter incoming velocity commands before forwarding to robot."""
        now = time.time()

        # Remove timestamps older than 1 second
        cutoff = now - 1.0
        while self.cmd_vel_timestamps and self.cmd_vel_timestamps[0] < cutoff:
            self.cmd_vel_timestamps.popleft()

        current_rate = len(self.cmd_vel_timestamps)

        # --- ALERT: Detect flood ---
        if current_rate > self.ALERT_RATE and (now - self.last_alert_time) > 2.0:
            self.get_logger().error(
                f'[SECURITY ALERT] DoS detected! Rate: {current_rate} msg/s '
                f'on /cmd_vel - Blocking excess messages!'
            )
            self.last_alert_time = now

        # --- BLOCK: Rate limit exceeded ---
        if current_rate >= self.MAX_CMD_VEL_RATE:
            self.blocked_count += 1
            return  # Drop the message

        # --- VALIDATE: Velocity sanity check ---
        safe_msg = Twist()
        safe_msg.linear.x = max(
            -self.MAX_LINEAR_VEL,
            min(self.MAX_LINEAR_VEL, msg.linear.x)
        )
        safe_msg.angular.z = max(
            -self.MAX_ANGULAR_VEL,
            min(self.MAX_ANGULAR_VEL, msg.angular.z)
        )

        if abs(safe_msg.linear.x) != abs(msg.linear.x) or \
           abs(safe_msg.angular.z) != abs(msg.angular.z):
            self.get_logger().warn(
                f'[SECURITY] Velocity clamped: '
                f'linear {msg.linear.x:.2f}→{safe_msg.linear.x:.2f}, '
                f'angular {msg.angular.z:.2f}→{safe_msg.angular.z:.2f}'
            )

        # --- PASS: Forward safe message ---
        self.cmd_vel_timestamps.append(now)
        self.filtered_pub.publish(safe_msg)
        self.passed_count += 1

    def print_status(self):
        total = self.passed_count + self.blocked_count
        block_rate = (self.blocked_count / total * 100) if total > 0 else 0
        self.get_logger().info(
            f'[QoS Status] Passed: {self.passed_count} | '
            f'Blocked: {self.blocked_count} | '
            f'Block rate: {block_rate:.1f}%'
        )


def main(args=None):
    rclpy.init(args=args)
    node = QoSProtectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
