import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
from launch.actions import TimerAction

def generate_launch_description():
    pkg_share = get_package_share_directory('agric_orion')
    map_yaml = os.path.join(pkg_share, 'maps', 'map.yaml')
    planner_yaml = os.path.join(pkg_share, 'config', 'nav2_planner.yaml')
    controller_yaml = os.path.join(pkg_share, 'config', 'nav2_controller.yaml')
    bt_nav_yaml = os.path.join(pkg_share, 'config', 'nav2_bt_navigator.yaml')


    planner_server = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[planner_yaml]
    )

    controller_server = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[controller_yaml]
    )

    behavior_server = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=[bt_nav_yaml]
    )

    bt_navigator = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=[bt_nav_yaml]
    )

    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{
            'autostart': True,
            'node_names': ['planner_server', 'controller_server',
                            'behavior_server', 'bt_navigator']
        }]
    )



    return LaunchDescription([
     planner_server, controller_server,
        behavior_server, bt_navigator, lifecycle_manager
    ])