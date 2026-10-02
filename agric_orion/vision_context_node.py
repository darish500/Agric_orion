import json 
import rclpy 
from rclpy.node import Node 
from std_msgs.msg import String
from sensor_msgs.msg import Image 

from agric_orion.vision_agent import MockVisionAgent,SCENARIO_RESPONSES

class VisionContextNode(Node):
    """
    Publishes vision-derived mission context on /vision_context,
    kept entirely separate from /mission_context (Milestone 5.2/5.3's
    LiDAR-grounded output) -- these are two independent interpretation
    layers, not one combined signal.

    Currently backed by MockVisionAgent, since no real vision model is
    reachable yet (see docs/stage5_vision_experiment.md for the Gemini
    access block). The real swap-in point is exactly one line, in
    __init__ below.

    Because the mock cannot analyze real image content, which
    scenario it simulates is controlled by the 'mock_scenario' ROS
    parameter, settable live with:
        ros2 param set /vision_context_node mock_scenario obstacle_ahead
    Valid values are the keys in vision_agent.SCENARIO_RESPONSES.
    """


    def __init__(self):
        super().__init__('vision_context_node')


        self.vision_agent = MockVisionAgent()

        self.declare_parameter('mock_scenario' , 'open_field')

        self.latest_image = None 

        self.camera_sub = self.create_subscription(
            Image, 'camera' , self.camera_callback , 10
        )

        self.context_pub = self.create_publisher(
            String , 'vision_context' , 10
        )

        self.timer = self.create_timer (1.0 , self.publish_vision_context)

        self.get_logger().info(
            'vision_context_node started (mock backend).'
            "set scenario with: ros2 param set /vision_context_node"
            'mock_scenario <scenario_name>'
        )

    def camera_callback(self, msg: Image):
        self.latest_image = msg

    def publish_vision_context(self):
        if self.latest_image is None:
            return

        scenario = self.get_parameter('mock_scenario').get_parameter_value().string_value

        if scenario not in SCENARIO_RESPONSES:
            self.get_logger().warn(
                f"mcok_scenario '{scenario}' is not a recognized scenario"
                f"(valid: {list(SCENARIO_RESPONSES.keys())}): "
                f"falling back to default."
            )

        result = self.vision_agent.describe_scene(
            image=self.latest_image, scenario_hint=scenario
        )

        msg_out = String()
        msg_out.data = json.dumps(result)
        self.context_pub.publish(msg_out)



def main (args = None ):
    rclpy.init(args=args)
    node = VisionContextNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
   