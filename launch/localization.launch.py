from launch_ros.actions import Node

static_map_to_odom = Node(
    package='tf2_ros',
    executable='static_transform_publisher',
    arguments=[
        '-3.0', '0.0', '0.0',   # x y z translation
        '0', '0', '0',           # roll pitch yaw
        'map', 'odom'             # parent frame, child frame
    ]
)