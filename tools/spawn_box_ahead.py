import json
import math
import subprocess
import sys

import rclpy
from std_msgs.msg import String

SPAWN_X = -3.0          # world x of the robot's start; /world_state reports odom coordinates
DIST = float(sys.argv[1]) if len(sys.argv) > 1 else 1.5
NAME = sys.argv[2] if len(sys.argv) > 2 else 'late_box'

rclpy.init()
node = rclpy.create_node('spawn_box_ahead')
got = {}
node.create_subscription(String, 'world_state',
                         lambda m: got.setdefault('ws', json.loads(m.data)), 10)
while 'ws' not in got:
    rclpy.spin_once(node, timeout_sec=0.5)
ws = got['ws']
x = ws['position']['x'] + SPAWN_X
y = ws['position']['y']
yaw = ws['yaw']
bx = x + DIST * math.cos(yaw)
by = y + DIST * math.sin(yaw)
print(f'robot at world ({x:.2f}, {y:.2f}) yaw {yaw:.2f} -> box at ({bx:.2f}, {by:.2f})')

sdf = ("<sdf version='1.9'><model name='%s'><static>true</static>"
       "<pose>%f %f 0.075 0 0 %f</pose><link name='l'>"
       "<collision name='c'><geometry><box><size>0.2 0.4 0.15</size></box></geometry></collision>"
       "<visual name='v'><geometry><box><size>0.2 0.4 0.15</size></box></geometry>"
       "<material><ambient>0.8 0.1 0.1 1</ambient><diffuse>0.8 0.1 0.1 1</diffuse></material>"
       "</visual></link></model></sdf>") % (NAME, bx, by, yaw)
r = subprocess.run(
    ['gz', 'service', '-s', '/world/agri_field/create',
     '--reqtype', 'gz.msgs.EntityFactory', '--reptype', 'gz.msgs.Boolean',
     '--timeout', '2000', '--req', f'sdf: "{sdf}"'],
    capture_output=True, text=True)
print(r.stdout.strip() or r.stderr.strip())
rclpy.shutdown()
