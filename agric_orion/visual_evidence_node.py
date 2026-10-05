import json
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String
from agric_orion.detect_obstruction import detect

class VisualEvidenceNode(Node):
    def __init__(self):
        super().__init__('visual_evidence_node')
        self.sub = self.create_subscription(
            Image, '/camera', self.on_image, qos_profile_sensor_data)
        self.pub = self.create_publisher(String, 'visual_evidence', 10)
        self.last = 0.0
        self.get_logger().info(f'visual_evidence_node up, cv2 {cv2.__version__}')

    def on_image(self, m):
        now = self.get_clock().now().nanoseconds / 1e9
        if now - self.last < 0.25:          # limit to ~4 Hz
            return
        self.last = now
        if m.encoding != 'rgb8':
            return
        arr = np.frombuffer(m.data, np.uint8).reshape(m.height, m.step)
        arr = arr[:, :m.width * 3].reshape(m.height, m.width, 3)
        result = detect(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
        result['timestamp'] = now
        out = String(); out.data = json.dumps(result)
        self.pub.publish(out)

def main():
    rclpy.init()
    rclpy.spin(VisualEvidenceNode())

if __name__ == '__main__':
    main()