import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
import math
import time


class Nav2EvalNode(Node):
    def __init__(self):
        super().__init__('nav2_eval_node')

        self.declare_parameter('target_x', 0.0)
        self.declare_parameter('target_y', 0.0)
        self.declare_parameter('test_name', 'unnamed_test')

        self.target_x = self.get_parameter('target_x').value
        self.target_y = self.get_parameter('target_y').value
        self.test_name = self.get_parameter('test_name').value

        self.action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

        self.odom_sub = self.create_subscription(
            Odometry, 'odom', self.odom_callback, 10)

        self.last_odom_xy = None
        self.path_length = 0.0
        self.tracking = False

        self.last_feedback = None
        self.start_wall_time = None
        self.end_wall_time = None
        self.result_msg = None
        self.goal_succeeded = None

        # Known static map -> odom offset (from static_transform_publisher).
        # Documented simplification -- see docs/known_limitations.md.
        self.map_to_odom_offset = (-3.0, 0.0)

    def odom_callback(self, msg: Odometry):
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y

        if self.tracking:
            if self.last_odom_xy is not None:
                dx = x - self.last_odom_xy[0]
                dy = y - self.last_odom_xy[1]
                self.path_length += math.hypot(dx, dy)
            self.last_odom_xy = (x, y)

    def feedback_callback(self, feedback_msg):
        self.last_feedback = feedback_msg.feedback

    def send_goal(self):
        self.get_logger().info(f'[{self.test_name}] Waiting for action server...')
        self.action_client.wait_for_server()

        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = 'map'
        goal.pose.pose.position.x = self.target_x
        goal.pose.pose.position.y = self.target_y
        goal.pose.pose.orientation.w = 1.0

        self.get_logger().info(
            f'[{self.test_name}] Sending goal: ({self.target_x}, {self.target_y})')

        self.tracking = True
        self.start_wall_time = time.time()

        send_goal_future = self.action_client.send_goal_async(
            goal, feedback_callback=self.feedback_callback)
        send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error(f'[{self.test_name}] Goal rejected')
            self.tracking = False
            rclpy.shutdown()
            return

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result_callback)

    def result_callback(self, future):
        self.end_wall_time = time.time()
        self.tracking = False

        result = future.result()
        self.result_msg = result.result
        status = result.status

        # GoalStatus: 4 = SUCCEEDED, 5 = CANCELED, 6 = ABORTED
        self.goal_succeeded = (status == 4)

        self.print_summary(status)
        rclpy.shutdown()

    def print_summary(self, status):
        wall_time = (self.end_wall_time - self.start_wall_time
                     if self.start_wall_time else 0.0)

        num_recoveries = (self.last_feedback.number_of_recoveries
                           if self.last_feedback else -1)

        final_error = None
        if self.last_odom_xy is not None:
            map_x = self.last_odom_xy[0] + self.map_to_odom_offset[0]
            map_y = self.last_odom_xy[1] + self.map_to_odom_offset[1]
            final_error = math.hypot(
                map_x - self.target_x, map_y - self.target_y)

        status_names = {4: 'SUCCEEDED', 5: 'CANCELED', 6: 'ABORTED'}

        print('')
        print(f'===== Nav2 Evaluation: {self.test_name} =====')
        print(f'Target:            ({self.target_x}, {self.target_y})')
        print(f'Result:            {status_names.get(status, status)}')
        print(f'Travel time (s):   {wall_time:.2f}')
        print(f'Path length (m):   {self.path_length:.2f}')
        print(f'Recoveries used:   {num_recoveries}')
        if final_error is not None:
            print(f'Final position error (m): {final_error:.2f}')
        print('===============================================')
        print('')


def main(args=None):
    rclpy.init(args=args)
    node = Nav2EvalNode()
    node.send_goal()
    rclpy.spin(node)


if __name__ == '__main__':
    main()