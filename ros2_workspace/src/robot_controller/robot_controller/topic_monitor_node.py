#!/usr/bin/env python3
"""
FILE: topic_monitor_node.py
TYPE: ROS2 Node (runs on HOST machine)
PURPOSE: Monitors all active ROS2 topics and logs message rates, content, and anomalies.
         Used to observe normal system behavior and detect suspicious activity
         (e.g., flooding during a DoS attack or unexpected command sources).
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from rclpy.qos import QoSProfile, ReliabilityPolicy
import time
from collections import defaultdict


class TopicMonitor(Node):
    def __init__(self):
        super().__init__('topic_monitor')
        self.get_logger().info('Topic Monitor Node started - watching for anomalies')

        # Message rate tracking
        self.msg_counts = defaultdict(int)
        self.msg_timestamps = defaultdict(list)
        self.RATE_ALERT_THRESHOLD = 50  # messages/sec - flag as potential DoS

        qos = QoSProfile(depth=10)
        qos.reliability = ReliabilityPolicy.BEST_EFFORT

        # Monitor /cmd_vel - look for injected commands
        self.cmd_vel_sub = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_vel_callback, 10)

        # Monitor /scan - check for eavesdropping patterns
        self.scan_sub = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, qos)

        # Monitor /odom
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self.odom_callback, 10)

        # Periodic statistics report
        self.stats_timer = self.create_timer(5.0, self.print_stats)

    def record_message(self, topic: str):
        """Track message timestamps and detect abnormal rates."""
        now = time.time()
        self.msg_counts[topic] += 1
        self.msg_timestamps[topic].append(now)

        # Keep only last 1 second of timestamps
        cutoff = now - 1.0
        self.msg_timestamps[topic] = [
            t for t in self.msg_timestamps[topic] if t > cutoff
        ]

        rate = len(self.msg_timestamps[topic])
        if rate > self.RATE_ALERT_THRESHOLD:
            self.get_logger().error(
                f'[ALERT] HIGH MESSAGE RATE on {topic}: {rate} msg/s '
                f'- Possible DoS attack!'
            )

    def cmd_vel_callback(self, msg: Twist):
        self.record_message('/cmd_vel')
        # Log any large velocity commands that seem anomalous
        if abs(msg.linear.x) > 1.5 or abs(msg.angular.z) > 3.0:
            self.get_logger().warn(
                f'[SUSPICIOUS] Extreme velocity on /cmd_vel: '
                f'linear={msg.linear.x:.2f}, angular={msg.angular.z:.2f}'
            )

    def scan_callback(self, msg: LaserScan):
        self.record_message('/scan')

    def odom_callback(self, msg: Odometry):
        self.record_message('/odom')

    def print_stats(self):
        """Print a summary of message counts every 5 seconds."""
        self.get_logger().info('--- Topic Monitor Statistics ---')
        for topic, count in self.msg_counts.items():
            rate = len(self.msg_timestamps[topic])
            self.get_logger().info(
                f'  {topic}: total={count}, current_rate={rate} msg/s')
        self.get_logger().info('--------------------------------')


def main(args=None):
    rclpy.init(args=args)
    node = TopicMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
