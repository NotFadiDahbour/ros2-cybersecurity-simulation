"""
FILE: robot_launch.py
TYPE: ROS2 Launch File (runs on HOST machine)
PURPOSE: Launches the complete robot simulation stack:
         - robot_controller_node: main movement logic
         - topic_monitor_node: anomaly detection and logging
         Run with: ros2 launch robot_controller robot_launch.py
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='robot_controller',
            executable='robot_controller',
            name='robot_controller',
            output='screen',
            parameters=[{
                'use_sim_time': True,
            }]
        ),
        Node(
            package='robot_controller',
            executable='topic_monitor',
            name='topic_monitor',
            output='screen',
            parameters=[{
                'use_sim_time': True,
            }]
        ),
    ])
