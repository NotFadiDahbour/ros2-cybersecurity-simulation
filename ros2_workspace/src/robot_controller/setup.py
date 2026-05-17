"""
FILE: setup.py
TYPE: ROS2 Package Configuration (runs on HOST machine)
PURPOSE: Defines the ROS2 Python package for the robot_controller nodes.
         Used by colcon build system to compile and install the package.
"""
 
from setuptools import setup
 
package_name = 'robot_controller'
 
setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', [
            'launch/robot_launch.py',
            'launch/simple_world_launch.py',
        ]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='your_name',
    maintainer_email='your_email@example.com',
    description='ROS2 robot controller for cybersecurity simulation',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'robot_controller = robot_controller.robot_controller_node:main',
            'topic_monitor = robot_controller.topic_monitor_node:main',
        ],
    },
)