import json
import math

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from std_msgs.msg import String

import tf2_ros
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException




KNOWN_OBJECT = {
    'obstacle_1':          (2.0, 0.0, 0.5),
    'obstacle_2':          (2.0, -1.3, 0.5),
    'crop_row_1_plant_1':  (4.0, 1.0, 0.1),
    'crop_row_1_plant2':   (4.0, 2.0, 0.1),
    'crop_row_2_plant_1':  (4.0, -1.0, 0.1),
    'dynamic_test_obstacle': (-3.0, 1.5, 0.25),
}

LIDAR_FORWARD_OFFSET_M = 0.15
MATCH_MARGIN_M = 0.15




def identify_obstacle(robot_x, robot_y, yaw, nearest_obstacle_m):
    if robot_x is None or robot_y is None or yaw is None or nearest_obstacle_m is None:
        return 'unknown'

    lidar_x = robot_x + LIDAR_FORWARD_OFFSET_M * math.cos(yaw)
    lidar_y = robot_y + LIDAR_FORWARD_OFFSET_M * math.sin(yaw)

    est_x = lidar_x + nearest_obstacle_m * math.cos(yaw)
    est_y = lidar_y + nearest_obstacle_m * math.sin(yaw)

    best_name = 'unknown'
    best_margin = None

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

        # --- Temporal state (new, Milestone 5.3) ---
        # Memory of path_blocked across callbacks, so we can detect
        # transitions and track how long a blockage has persisted.
        # previous_path_blocked starts False: on the very first
        # message, if path_blocked happens to already be True, this
        # correctly reports it as a fresh transition (duration ~0),
        # which is the honest answer -- we have no earlier history to
        # know otherwise.
        self.previous_path_blocked = False
        self.blocked_since = None  # a ROS Time, or None if not currently blocked

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



    def update_blocked_duration(self, path_blocked):
        """
        Updates temporal state for path_blocked and returns
        (blocked_changed, blocked_duration_s).

        blocked_changed is True only on the exact cycle the state
        flips (either direction), not on every cycle it happens to be
        True.
        """
        now = self.get_clock().now()

        blocked_changed = (path_blocked != self.previous_path_blocked)



        if path_blocked and self.blocked_since is None:
            # Just became blocked (or first message ever arrived
            # already blocked) -- start the clock.
            self.blocked_since = now

        if not path_blocked:
            # Cleared -- no active streak.
            self.blocked_since = None



        if self.blocked_since is not None:
            blocked_duration_s = (now - self.blocked_since).nanoseconds / 1e9
        else:
            blocked_duration_s = 0.0

        # Update memory for the next callback. Must happen last --
        # everything above depends on the OLD value.
        self.previous_path_blocked = path_blocked

        return blocked_changed, blocked_duration_s



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

        blocked_changed, blocked_duration_s = self.update_blocked_duration(path_blocked)



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
                'path_blocked_changed': blocked_changed,
                'path_blocked_duration_s': round(blocked_duration_s, 1),
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