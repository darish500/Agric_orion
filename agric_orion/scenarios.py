import json, os, subprocess, time
import cv2
from detect_obstruction import detect

OUT_DIR = os.path.expanduser('~/workspace/stage6_data')
HERE = os.path.dirname(os.path.abspath(__file__))
BOX = 'sc'
COLORS = {'red': '0.8 0.1 0.1', 'green': '0.1 0.7 0.1', 'gray': '0.5 0.5 0.5'}

# name, x, y, (size_x, size_y, height), colour, ground_truth_in_corridor
SCENARIOS = [
    ('s_clear',      None, None, None,            None,    False),
    ('s_side',       -1.5, 0.6,  (0.2, 0.4, 0.10), 'red',   False),
    ('s_gray',       -1.5, 0.0,  (0.2, 0.4, 0.10), 'gray',  True),
    ('s_green',      -1.5, 0.0,  (0.2, 0.4, 0.10), 'green', True),
    ('s_near_edge',  -0.5, 0.0,  (0.2, 0.4, 0.10), 'red',   True),
    ('s_beyond',      0.0, 0.0,  (0.2, 0.4, 0.10), 'red',   False),
    ('s_small',      -1.3, 0.0,  (0.1, 0.1, 0.10), 'red',   True),
    ('s_small_far',  -0.5, 0.0,  (0.1, 0.1, 0.10), 'red',   True),
    ('s_clear_end',  None, None, None,            None,    False),
]

def gz(service, reqtype, req):
    r = subprocess.run(['gz', 'service', '-s', f'/world/agri_field/{service}',
                        '--reqtype', reqtype, '--reptype', 'gz.msgs.Boolean',
                        '--timeout', '2000', '--req', req],
                       capture_output=True, text=True)
    return 'true' in r.stdout

def spawn(x, y, size, color):
    sx, sy, h = size
    c = COLORS[color]
    sdf = (f"<sdf version='1.9'><model name='{BOX}'><static>true</static>"
           f"<pose>{x} {y} {h/2} 0 0 0</pose><link name='l'>"
           f"<collision name='c'><geometry><box><size>{sx} {sy} {h}</size></box></geometry></collision>"
           f"<visual name='v'><geometry><box><size>{sx} {sy} {h}</size></box></geometry>"
           f"<material><ambient>{c} 1</ambient><diffuse>{c} 1</diffuse></material>"
           f"</visual></link></model></sdf>")
    return gz('create', 'gz.msgs.EntityFactory', f'sdf: "{sdf}"')

def remove(name=BOX):
    return gz('remove', 'gz.msgs.Entity', f'name: "{name}" type: MODEL')

def capture(name):
    for ext in ('json', 'png'):
        try: os.remove(f'{OUT_DIR}/{name}.{ext}')
        except FileNotFoundError: pass
    subprocess.run(['/usr/bin/python3', os.path.join(HERE, 'capture_trial.py'), name])
    p = f'{OUT_DIR}/{name}.json'
    return json.load(open(p))['forward_min_m'] if os.path.exists(p) else None

def main():
    for n in (BOX, 'tb', 'test_box'): remove(n)
    rows = []
    for name, x, y, size, color, truth in SCENARIOS:
        if size is not None and not spawn(x, y, size, color):
            print(name, 'SPAWN FAILED'); remove(); continue
        time.sleep(1.5)
        lidar = capture(name)
        if size is not None: remove()
        time.sleep(1.5)
        img = cv2.imread(f'{OUT_DIR}/{name}.png')
        r = detect(img) if img is not None else {}
        true_rng = None if size is None else round(x - size[0] / 2 + 2.8, 2)
        det = r.get('visual_obstruction')
        verdict = ('NO IMAGE' if det is None else
                   'ok' if det == truth else
                   'MISS' if truth else 'FALSE ALARM')
        rows.append((name, truth, det, true_rng, r.get('est_range_m'), lidar, verdict))
    print('\nscenario      truth  detected  true_rng  est_rng  lidar_min  verdict')
    for row in rows:
        print('{:13s} {!s:6s} {!s:9s} {!s:9s} {!s:8s} {!s:10s} {}'.format(*row))

if __name__ == '__main__':
    main()