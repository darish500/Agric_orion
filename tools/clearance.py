import json
import math
import sys

import rclpy
from std_msgs.msg import String

SPAWN_X = -3.0
bx, by = float(sys.argv[1]), float(sys.argv[2])

rclpy.init()
node = rclpy.create_node('clearance')
got = {}
node.create_subscription(String, 'world_state',
                         lambda m: got.setdefault('ws', json.loads(m.data)), 10)
while 'ws' not in got:
    rclpy.spin_once(node, timeout_sec=0.5)
ws = got['ws']
rx, ry = ws['position']['x'] + SPAWN_X, ws['position']['y']
d = math.hypot(bx - rx, by - ry)
print(f'robot ({rx:.2f}, {ry:.2f}); box centre ({bx:.2f}, {by:.2f}); '
      f'centre distance {d:.2f} m; clearance (robot front to box face) ~ {d - 0.3:.2f} m')
rclpy.shutdown()