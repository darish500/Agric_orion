import json, os, sys, time
import numpy as np
import rclpy
from PIL import Image as PILImage
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, LaserScan

OUT_DIR = os.path.expanduser('~/workspace/stage6_data')

def main():
    name = sys.argv[1]                      # e.g. baseline, h010
    rclpy.init()
    node = rclpy.create_node('capture_trial')
    latest = {}
    node.create_subscription(Image, '/camera',
        lambda m: latest.__setitem__('img', m), qos_profile_sensor_data)
    node.create_subscription(LaserScan, '/scan',
        lambda m: latest.__setitem__('scan', m), qos_profile_sensor_data)

    end = time.time() + 2.0                 # collect for 2 s, keep the newest
    while time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.1)
    if 'img' not in latest or 'scan' not in latest:
        print('MISSING DATA:', list(latest.keys())); return

    # camera -> PNG
    m = latest['img']
    assert m.encoding == 'rgb8', m.encoding
    arr = np.frombuffer(m.data, np.uint8).reshape(m.height, m.step)
    arr = arr[:, :m.width * 3].reshape(m.height, m.width, 3)
    os.makedirs(OUT_DIR, exist_ok=True)
    PILImage.fromarray(arr).save(f'{OUT_DIR}/{name}.png')

    # scan -> JSON summary
    s = latest['scan']
    ranges = np.array(s.ranges)
    angles = s.angle_min + np.arange(len(ranges)) * s.angle_increment
    fwd = np.abs(angles) <= np.deg2rad(10)
    fwd_vals = ranges[fwd][np.isfinite(ranges[fwd])]
    summary = {
        'name': name,
        'forward_min_m': float(fwd_vals.min()) if len(fwd_vals) else None,
        'forward_hits': int(len(fwd_vals)),
        'ranges': [float(r) if np.isfinite(r) else None for r in ranges],
    }
    json.dump(summary, open(f'{OUT_DIR}/{name}.json', 'w'))
    print(name, 'image', m.width, 'x', m.height,
          '| forward_min_m =', summary['forward_min_m'],
          '| forward_hits =', summary['forward_hits'])
    rclpy.shutdown()

if __name__ == '__main__':
    main()