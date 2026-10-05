import json, os, random, subprocess, sys, time
import numpy as np
from PIL import Image
from capture_trial import OUT_DIR

HEIGHTS_M = [0.03, 0.05, 0.08, 0.10, 0.15, 0.18, 0.22, 0.25, 0.30, 0.50]
BOX = 'tb'
HERE = os.path.dirname(os.path.abspath(__file__))

def gz(service, reqtype, req):
    r = subprocess.run(
        ['gz', 'service', '-s', f'/world/agri_field/{service}',
         '--reqtype', reqtype, '--reptype', 'gz.msgs.Boolean',
         '--timeout', '2000', '--req', req],
        capture_output=True, text=True)
    return 'true' in r.stdout

def spawn(h):
    sdf = (f"<sdf version='1.9'><model name='{BOX}'><static>true</static>"
           f"<pose>-1.5 0 {h/2} 0 0 0</pose><link name='l'>"
           f"<collision name='c'><geometry><box><size>0.2 0.4 {h}</size></box></geometry></collision>"
           f"<visual name='v'><geometry><box><size>0.2 0.4 {h}</size></box></geometry>"
           f"<material><ambient>0.8 0.1 0.1 1</ambient><diffuse>0.8 0.1 0.1 1</diffuse></material>"
           f"</visual></link></model></sdf>")
    return gz('create', 'gz.msgs.EntityFactory', f'sdf: "{sdf}"')

def remove(name=BOX):
    return gz('remove', 'gz.msgs.Entity', f'name: "{name}" type: MODEL')

def capture(name):
    for ext in ('json', 'png'):             # delete stale files first
        try: os.remove(f'{OUT_DIR}/{name}.{ext}')
        except FileNotFoundError: pass
    subprocess.run([sys.executable, os.path.join(HERE, 'capture_trial.py'), name])
    p = f'{OUT_DIR}/{name}.json'
    return json.load(open(p))['forward_min_m'] if os.path.exists(p) else None

def changed_pixels(name):
    a = np.asarray(Image.open(f'{OUT_DIR}/{name}.png').convert('RGB'), dtype=np.int16)
    b = np.asarray(Image.open(f'{OUT_DIR}/baseline.png').convert('RGB'), dtype=np.int16)
    return int((np.abs(a - b).sum(axis=2)[245:, :] > 30).sum())

def main():
    remove('tb'); remove('test_box')        # clear leftovers; harmless if absent
    random.seed(1)
    order = HEIGHTS_M[:]; random.shuffle(order)
    trials = ([('baseline', None)]
              + [(f'h{round(h*100):03d}', h) for h in order]
              + [('baseline_end', None)])
    rows = []
    for name, h in trials:
        if h is not None and not spawn(h):
            print(name, 'SPAWN FAILED'); remove(); continue
        time.sleep(1.5)
        fmin = capture(name)
        if h is not None: remove()
        time.sleep(1.5)
        px = None if name == 'baseline' or fmin is None else changed_pixels(name)
        rows.append((name, h, fmin, px))

    base = rows[0][2]
    print('\nheight_cm | lidar_min_m | lidar_sees_box | px_changed_vs_baseline')
    for name, h, fmin, px in sorted(rows, key=lambda r: (r[1] is None, r[1] or 0)):
        sees = None if fmin is None else fmin < base - 0.5
        print(f'{name:12s} {fmin} {sees} {px}')

main()