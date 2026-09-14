import os 
from launch_ros.actions import Node
from launch import LaunchDescription
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_share = get_package_share_directory('agric_orion')

    planner_yaml= os.path.join(pkg_share , 'config' , 'nav2_planner.yaml')

    planner_server= Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters= [planner_yaml]
    )

    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_planner',
        output= 'screen',
        parameters=[
            {
                'autostart': True,
                'node_names': ['planner_server'] 
            }
        ]
    )


    return LaunchDescription(
        [
            planner_server,
            lifecycle_manager
        ]
    )