import base64
import json
import time
import urllib.request
import os


import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String

from agric_orion.detect_obstruction import detect


class VisualEvidenceNode(Node):
    def __init__(self):
        super().__init__('visual_evidence_node')
        self.declare_parameter('backend', 'local')       # 'local' or 'url'
        self.declare_parameter('endpoint_url', '')
        self.declare_parameter('timeout_s', 2.0)
        self.sub = self.create_subscription(
            Image, '/camera', self.on_image, qos_profile_sensor_data)
        self.pub = self.create_publisher(String, 'visual_evidence', 10)
        self.last = 0.0
        backend = self.get_parameter('backend').value
        self.get_logger().info(f'visual_evidence_node up, cv2 {cv2.__version__}, backend={backend}')
        if not cv2.__version__.startswith('5.'):
            self.get_logger().error(
                f'Open Cv {cv2._version__} is NOT 5.x , start this node witht the venv '
                f'Python: python -m agric_orion.visual_evidence_node'
            )

    def detect_remote(self, bgr):
        ok, png = cv2.imencode('.png', bgr)
        payload = json.dumps(
            {'image_b64': base64.b64encode(png.tobytes()).decode()}).encode()
        req = urllib.request.Request(
            self.get_parameter('endpoint_url').value, data=payload,
            headers={'Content-Type': 'application/json',
                     'x-api-key': os.environ.get('AGRI_KEY', '')}, method='POST')
        t0 = time.time()
        with urllib.request.urlopen(
                req, timeout=self.get_parameter('timeout_s').value) as resp:
            result = json.loads(resp.read())
        result['round_trip_ms'] = round((time.time() - t0) * 1000, 1)
        return result

    def on_image(self, m):
        now = self.get_clock().now().nanoseconds / 1e9
        if now - self.last < 0.25:                    # about 4 Hz
            return
        self.last = now
        if m.encoding != 'rgb8':
            return
        arr = np.frombuffer(m.data, np.uint8).reshape(m.height, m.step)
        arr = arr[:, :m.width * 3].reshape(m.height, m.width, 3)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

        backend = self.get_parameter('backend').value
        try:
            result = self.detect_remote(bgr) if backend == 'url' else detect(bgr)
        except (OSError, ValueError) as e:
            self.get_logger().warn(
                f'[VISUAL EVIDENCE] detector failed ({e}); publishing nothing',
                throttle_duration_sec=5.0)
            return

        result['timestamp'] = now
        result['backend'] = backend
        out = String()
        out.data = json.dumps(result)
        self.pub.publish(out)


def main():
    rclpy.init()
    rclpy.spin(VisualEvidenceNode())


if __name__ == '__main__':
    main()