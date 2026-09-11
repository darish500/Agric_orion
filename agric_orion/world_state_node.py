import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from std_msgs.msg import String
import json
import math


class WorldStateNode(Node):
    def __init__(self):
        super().__init__('world_state_node')

        self.latest_odom = None

        self.odom_sub = self.create_subscription(
            Odometry, 'odom', self.odom_callback, 10)

        self.scan_sub = self.create_subscription(
            LaserScan, 'scan', self.scan_callback, 10)

        self.state_pub = self.create_publisher(
            String, 'world_state', 10)

        self.get_logger().info('world_state_node started')

    def odom_callback(self, msg: Odometry):
        # Just store the most recent odometry message.
        # scan_callback will read from this when it needs position/orientation.
        self.latest_odom = msg

    def scan_callback(self, msg: LaserScan):
        if self.latest_odom is None:
            # No odometry data has arrived yet — skip this scan rather
            # than crash trying to read position that doesn't exist yet.
            return

        # --- Position ---
        x = self.latest_odom.pose.pose.position.x
        y = self.latest_odom.pose.pose.position.y

        # --- Orientation: quaternion -> yaw ---
        # odom gives orientation as a quaternion (x, y, z, w). For a ground
        # vehicle we only care about rotation around the vertical (Z) axis,
        # i.e. yaw. This is the standard formula to extract yaw alone from
        # a quaternion, without needing a full quaternion math library.
        q = self.latest_odom.pose.pose.orientation
        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        )

        # --- Nearest obstacle, forward-facing ---
        # angle_min is -pi (pointing directly behind the robot), and angles
        # increase going around the circle. That means "straight ahead"
        # (angle = 0) sits at the MIDDLE of the ranges array, not the start.
        num_ranges = len(msg.ranges)
        center_index = num_ranges // 2

        # Look at a small forward sector rather than a single index, since
        # a single ray is easy to miss an obstacle by a fraction of a degree.
        # +/-10 samples at ~0.0175 rad/sample (from Milestone 2.2) is
        # roughly a +/-10 degree forward-facing cone.
        sector_half_width = 10
        start = max(0, center_index - sector_half_width)
        end = min(num_ranges, center_index + sector_half_width + 1)

        forward_ranges = msg.ranges[start:end]

        # Filter out inf (nothing detected) before taking the minimum,
        # otherwise min() would just always return inf and hide real data.
        finite_ranges = [r for r in forward_ranges if math.isfinite(r)]

        if finite_ranges:
            nearest_obstacle = min(finite_ranges)
        else:
            # Nothing detected in the forward sector within sensor range.
            nearest_obstacle = None

        # --- Path blocked decision ---
        # Simple placeholder threshold, not real obstacle avoidance logic.
        blocked_threshold_m = 1.0
        if nearest_obstacle is not None:
            path_blocked = nearest_obstacle < blocked_threshold_m
        else:
            path_blocked = False

        # --- Assemble world state ---
        world_state = {
            'timestamp': msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
            'position': {'x': x, 'y': y},
            'yaw': yaw,
            'nearest_obstacle_m': nearest_obstacle,
            'path_blocked': path_blocked,
        }

        msg_out = String()
        msg_out.data = json.dumps(world_state)
        self.state_pub.publish(msg_out)


def main(args=None):
    rclpy.init(args=args)
    node = WorldStateNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()