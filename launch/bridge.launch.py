# from launch import LaunchDescription
# from launch_ros.actions import Node


# def generate_launch_description():
#     bridge = Node(
#         package='ros_gz_bridge',
#         executable='parameter_bridge',
#         arguments=[
#             '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
#             '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
#             '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
#         ],
#         output='screen'
#     )

#     return LaunchDescription([bridge])

import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_share= get_package_share_directory("agric_orion")
    bridge_config = os.path.join(pkg_share, "config" , "bridge.yaml")

    bridge= Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'config_file': bridge_config}],
        output='screen'
    )

    return LaunchDescription(
        [
            bridge,
    ])