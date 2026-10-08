import base64
import glob
import json
import os
import sys

import cv2

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'cloud'))
from handler import handler
from agric_orion.detect_obstruction import detect

DATA = os.path.expanduser('~/workspace/stage6_data')
KEYS = ('visual_obstruction', 'corridor_occupancy', 'est_range_m')


def call(raw_bytes):
    event = {'body': json.dumps({'image_b64': base64.b64encode(raw_bytes).decode()}),
             'isBase64Encoded': False}
    r = handler(event)
    return r['statusCode'], json.loads(r['body'])


same = total = 0
print(f'{"image":14s} status  obstruction  range_m  ms     matches_local')
for p in sorted(glob.glob(os.path.join(DATA, '*.png'))):
    raw = open(p, 'rb').read()
    code, out = call(raw)
    ref = detect(cv2.imread(p))
    ok = code == 200 and all(out.get(k) == ref.get(k) for k in KEYS)
    total += 1
    same += ok
    print(f'{os.path.basename(p)[:-4]:14s} {code}     {out.get("visual_obstruction")!s:11s} '
          f'{out.get("est_range_m")!s:8s} {out.get("processing_ms")!s:6s} {ok}')
print(f'\nidentical to local detector: {same}/{total}')

bad1 = handler({'body': ''})['statusCode']
bad2 = handler({'body': json.dumps({'image_b64': base64.b64encode(b"not an image").decode()})})['statusCode']
bad3 = handler({'body': json.dumps({'wrong_key': 1})})['statusCode']
print(f'bad requests (expect 400 400 400): {bad1} {bad2} {bad3}')