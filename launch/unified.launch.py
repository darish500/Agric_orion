import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share= get_package_share_directory("agric_orion")

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share,'launch','gazebo.launch.py')
        )
    )

    bridge = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch' ,'bridge.launch.py')
        )
    )

    map_server_launch= IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'map_server.launch.py')
        )
    )

    static_map_to_odom = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_map_to_odom',
        arguments=[
            '-3.0', '0.0', '0.0',
            '0' , '0' ,'0' ,
            'map', 'odom'
        ]
    )


    return LaunchDescription(
        [
            gazebo,
            bridge,
            static_map_to_odom,
            map_server_launch
        ]
    )