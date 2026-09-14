import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import FollowPath
from nav_msgs.msg import Path


class TestFollowPath(Node):
    def __init__(self):
        super().__init__('test_follow_path')
        self.plan_sub = self.create_subscription(Path, '/plan', self.plan_callback, 10)
        self.action_client = ActionClient(self, FollowPath, 'follow_path')
        self.sent = False

    def plan_callback(self, msg: Path):
        if self.sent:
            return
        self.sent = True
        self.get_logger().info(f'Got path with {len(msg.poses)} poses, sending to controller...')

        goal = FollowPath.Goal()
        goal.path = msg
        goal.controller_id = 'FollowPath'

        self.action_client.wait_for_server()
        self.action_client.send_goal_async(goal)


def main():
    rclpy.init()
    node = TestFollowPath()
    rclpy.spin(node)


if __name__ == '__main__':
    main()