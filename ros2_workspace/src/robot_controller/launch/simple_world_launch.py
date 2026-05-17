"""
FILE: simple_world_launch.py
PURPOSE: Launches Gazebo with simple_world.world and spawns TurtleBot3 burger.
RUN WITH: ros2 launch robot_controller simple_world_launch.py
"""

import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    world_file = os.path.expanduser(
        '~/ros2_cybersecurity_project/gazebo_worlds/simple_world.world'
    )

    # Start Gazebo with the custom world
    gazebo = ExecuteProcess(
        cmd=['gazebo', '--verbose', world_file,
             '-s', 'libgazebo_ros_factory.so',
             '-s', 'libgazebo_ros_init.so'],
        output='screen'
    )

    # Spawn TurtleBot3 burger into the running Gazebo
    spawn_robot = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-entity', 'turtlebot3_burger',
            '-database', 'turtlebot3_burger',
            '-x', '0', '-y', '0', '-z', '0.01',
        ],
        output='screen'
    )

    return LaunchDescription([
        gazebo,
        spawn_robot,
    ])
