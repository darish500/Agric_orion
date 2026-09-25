import json
import math

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from std_msgs.msg import String

import tf2_ros
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException


# Known fixed objects in agric_field.sdf, in MAP frame coordinates:
# (x, y, footprint_radius). footprint_radius is half the object's
# horizontal size (box half-width, or cylinder radius) -- taken
# directly from each model's <geometry> in the world file, not
# guessed.
KNOWN_OBJECT = {
    'obstacle_1':          (2.0, 0.0, 0.5),
    'obstacle_2':          (2.0, -1.3, 0.5),
    'crop_row_1_plant_1':  (4.0, 1.0, 0.1),
    'crop_row_1_plant2':   (4.0, 2.0, 0.1),
    'crop_row_2_plant_1':  (4.0, -1.0, 0.1),
    'dynamic_test_obstacle': (-3.0, 1.5, 0.25),
}

# The LiDAR is mounted 0.15m forward of base_link's origin (see
# lidar_joint's <origin xyz="0.15 0 0.1"/> in agric_orion.xacro).
# nearest_obstacle_m is measured from the sensor, not from the point
# world_state reports as robot position -- so this offset must be
# applied before projecting where the obstacle actually is, or every
# estimate is silently short by this exact amount.
LIDAR_FORWARD_OFFSET_M = 0.15

# Extra slack beyond an object's own footprint radius, to absorb
# residual approximation error (the forward sector is +/-10 degrees,
# not a single exact ray; the LiDAR beam that actually returns the
# minimum range may not be exactly centered on the object). This is
# deliberately small -- it is slack on top of a real, measured
# footprint, not a substitute for one.
MATCH_MARGIN_M = 0.15


def identify_obstacle(robot_x, robot_y, yaw, nearest_obstacle_m):
    """
    robot_x, robot_y must already be in map-frame (true world)
    coordinates when this is called -- not raw odom.
    """
    if robot_x is None or robot_y is None or yaw is None or nearest_obstacle_m is None:
        return 'unknown'

    # Project from the LiDAR's true position, not base_link's.
    lidar_x = robot_x + LIDAR_FORWARD_OFFSET_M * math.cos(yaw)
    lidar_y = robot_y + LIDAR_FORWARD_OFFSET_M * math.sin(yaw)

    est_x = lidar_x + nearest_obstacle_m * math.cos(yaw)
    est_y = lidar_y + nearest_obstacle_m * math.sin(yaw)

    best_name = 'unknown'
    best_margin = None  # how far inside the acceptance radius the best match is

    for name, (obj_x, obj_y, footprint_radius) in KNOWN_OBJECT.items():
        dist = math.hypot(est_x - obj_x, est_y - obj_y)
        acceptance_radius = footprint_radius + MATCH_MARGIN_M

        if dist < acceptance_radius:
            margin = acceptance_radius - dist
            if best_margin is None or margin > best_margin:
                best_margin = margin
                best_name = name

    return best_name


class MissionContextNode(Node):
    def __init__(self):
        super().__init__('mission_context_node')

        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.world_state_sub = self.create_subscription(
            String, 'world_state', self.world_state_callback, 10
        )

        self.context_pub = self.create_publisher(
            String, 'mission_context', 10
        )

        self.get_logger().info('mission_context_node started')

    def get_map_to_odom_offset(self):
        try:
            transform = self.tf_buffer.lookup_transform(
                'map', 'odom', Time())
        except (LookupException, ConnectivityException, ExtrapolationException) as e:
            self.get_logger().warn(f'map->odom transform not available yet: {e}')
            return None

        offset_x = transform.transform.translation.x
        offset_y = transform.transform.translation.y
        return (offset_x, offset_y)

    def world_state_callback(self, msg: String):
        try:
            world_state = json.loads(msg.data)
        except (json.JSONDecodeError, TypeError) as e:
            self.get_logger().error(f'failed to parse world_state JSON: {e}')
            return

        if not isinstance(world_state, dict):
            self.get_logger().error('world_state payload must be a JSON object')
            return

        position = world_state.get('position', {})
        odom_x = position.get('x')
        odom_y = position.get('y')
        yaw = world_state.get('yaw')
        nearest_obstacle_m = world_state.get('nearest_obstacle_m')
        path_blocked = world_state.get('path_blocked', False)

        if odom_x is None or odom_y is None or yaw is None:
            return

        offset = self.get_map_to_odom_offset()
        if offset is None:
            return

        offset_x, offset_y = offset
        map_x = odom_x + offset_x
        map_y = odom_y + offset_y

        if nearest_obstacle_m is not None:
            obstacle_identity = identify_obstacle(map_x, map_y, yaw, nearest_obstacle_m)
        else:
            obstacle_identity = None

        mission_context = {
            'robot': {
                'x': map_x,
                'y': map_y,
                'yaw': yaw,
            },
            'environment': {
                'path_blocked': path_blocked,
                'nearest_obstacle_m': nearest_obstacle_m,
                'obstacle_identity': obstacle_identity,
            },
        }

        msg_out = String()
        msg_out.data = json.dumps(mission_context)
        self.context_pub.publish(msg_out)


def main(args=None):
    rclpy.init(args=args)
    node = MissionContextNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()