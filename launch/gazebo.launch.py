import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_share= get_package_share_directory('agric_orion')
    xacro_path= os.path.join(pkg_share,'urdf','agric_orion.xacro')
    world_path= os.path.join(pkg_share,'worlds','agric_field.sdf')

    gz_sim = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(
                    get_package_share_directory('ros_gz_sim'),
                    'launch',
                    'gz_sim.launch.py'
                )
            ),
            launch_arguments= {'gz_args' : f'-r {world_path}'}.items()
        )

    robot_description = ParameterValue(
        Command([
            'xacro ',xacro_path
        ]),
        value_type=str
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description}]
    )

    spawn_robot= Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'agric_orion',
            'x', '-3.0'
            '-y', '0.0'
            '-z', '0.3'
        ],
        output='screen'
    )

    

    return LaunchDescription([
        gz_sim,
        robot_state_publisher,
        spawn_robot
    ])