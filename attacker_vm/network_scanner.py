#!/usr/bin/env python3
"""
FILE: network_scanner.py
TYPE: ATTACKER VM Script (runs on ATTACKER VM - Ubuntu in VMware)
PURPOSE: Performs initial reconnaissance by scanning the target network for:
         - Open ROS bridge ports (9090)
         - Active DDS/RTPS traffic (UDP port 7400+)
         - ROS2 node and topic enumeration via rosbridge
         This represents the discovery phase before launching an attack.

REQUIREMENTS (on Attacker VM):
    pip3 install roslibpy
    sudo apt-get install nmap  (for network scanning)

HOW TO RUN:
    python3 network_scanner.py --target 192.168.1.0/24
    python3 network_scanner.py --host 192.168.1.100  (enumerate single host)
"""

import argparse
import socket
import sys
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import roslibpy
    HAS_ROSLIBPY = True
except ImportError:
    HAS_ROSLIBPY = False
    print("[WARN] roslibpy not installed - ROS enumeration disabled")


def check_port(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except (socket.error, OSError):
        return False


def scan_ros_ports(host: str):
    ros_ports = {
        9090:  'ROS Bridge WebSocket',
        11311: 'ROS Master (ROS1)',
        7400:  'DDS/RTPS Discovery (UDP)',
        7401:  'DDS/RTPS Data',
    }
    print(f"\n[SCANNER] Scanning ROS-related ports on {host}...")
    open_ports = {}
    for port, service in ros_ports.items():
        if check_port(host, port):
            print(f"  [OPEN]   {port}/tcp - {service}")
            open_ports[port] = service
        else:
            print(f"  [closed] {port}/tcp - {service}")
    return open_ports


def call_service(client, service_name, service_type, timeout=5.0):
    """Call a rosapi service and return the result dict, or None on failure."""
    result = [None]
    done   = [False]

    svc = roslibpy.Service(client, service_name, service_type)
    req = roslibpy.ServiceRequest()

    def on_success(response):
        result[0] = response
        done[0]   = True

    def on_error(err):
        done[0] = True

    svc.call(req, on_success, on_error)

    deadline = time.time() + timeout
    while not done[0] and time.time() < deadline:
        time.sleep(0.1)

    return result[0]


def enumerate_ros_info(host: str, port: int = 9090):
    """
    Open a SINGLE rosbridge connection and enumerate both topics and nodes.
    Avoids the Twisted ReactorNotRestartable crash that occurs when you
    create multiple roslibpy.Ros clients in the same process.
    """
    if not HAS_ROSLIBPY:
        print("[SCANNER] roslibpy not available - skipping enumeration")
        return [], []

    print(f"\n[SCANNER] Connecting to rosbridge at {host}:{port}...")
    client = roslibpy.Ros(host=host, port=port)

    try:
        client.run(timeout=10)
    except Exception as e:
        print(f"[SCANNER] Connection failed: {e}")
        return [], []

    if not client.is_connected:
        print("[SCANNER] Could not connect to rosbridge.")
        return [], []

    print("[SCANNER] Connected.\n")

    # ── Topics ───────────────────────────────────────────────────────────
    topics = []
    print(f"[SCANNER] Enumerating ROS topics via rosbridge at {host}:{port}...")
    result = call_service(client, '/rosapi/topics', 'rosapi/Topics')
    if result:
        for topic, t in zip(result.get('topics', []), result.get('types', [])):
            topics.append({'topic': topic, 'type': t})
            print(f"  [FOUND] {topic}  ({t})")
    else:
        print("  [WARN] Topic enumeration timed out or failed")

    # ── Nodes ────────────────────────────────────────────────────────────
    nodes = []
    print(f"\n[SCANNER] Enumerating ROS nodes via rosbridge at {host}:{port}...")
    result = call_service(client, '/rosapi/nodes', 'rosapi/Nodes')
    if result:
        for node in result.get('nodes', []):
            nodes.append(node)
            print(f"  [NODE] {node}")
    else:
        print("  [WARN] Node enumeration timed out or failed")

    client.terminate()
    return topics, nodes


def main():
    parser = argparse.ArgumentParser(description='ROS2 Network Reconnaissance Scanner')
    parser.add_argument('--host',   type=str, help='Single target host IP to enumerate')
    parser.add_argument('--target', type=str, help='CIDR subnet to scan (e.g., 192.168.1.0/24)')
    parser.add_argument('--port',   type=int, default=9090, help='ROS bridge port (default: 9090)')
    parser.add_argument('--output', type=str, default='recon_results.json', help='Output file for results')
    args = parser.parse_args()

    print("=" * 60)
    print("  ROS2 NETWORK RECONNAISSANCE - SIMULATION ONLY")
    print("  For educational/research use in controlled environments")
    print("=" * 60)

    results = {}

    if args.host:
        target = args.host
        print(f"\n[SCANNER] Target: {target}")

        open_ports = scan_ros_ports(target)
        results['open_ports'] = open_ports

        if 9090 in open_ports:
            # Single connection for both topics and nodes
            topics, nodes = enumerate_ros_info(target, args.port)
            results['topics'] = topics
            results['nodes']  = nodes
        else:
            print("[SCANNER] ROS bridge port not open - cannot enumerate topics/nodes")

    elif args.target:
        print(f"\n[SCANNER] Scanning subnet: {args.target}")
        base = '.'.join(args.target.split('.')[:3])
        print(f"[SCANNER] Checking {base}.1 - {base}.254 for port 9090...")

        found_hosts = []

        def check_host(ip):
            if check_port(ip, 9090, timeout=0.5):
                return ip
            return None

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = {executor.submit(check_host, f"{base}.{i}"): i for i in range(1, 255)}
            for future in as_completed(futures):
                ip = future.result()
                if ip:
                    print(f"  [FOUND] ROS bridge at {ip}:9090")
                    found_hosts.append(ip)

        results['discovered_hosts'] = found_hosts

    else:
        print("[ERROR] Provide --host or --target")
        sys.exit(1)

    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n[SCANNER] Results saved to {args.output}")


if __name__ == '__main__':
    main()
