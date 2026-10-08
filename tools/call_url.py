import base64, json, os, statistics, time, urllib.error, urllib.request

URL = os.environ['AGRI_URL']
KEY = os.environ.get('AGRI_KEY', '')
DATA = os.path.expanduser('~/workspace/stage6_data')


def call(path, key=KEY):
    payload = json.dumps(
        {'image_b64': base64.b64encode(open(path, 'rb').read()).decode()}).encode()
    req = urllib.request.Request(
        URL, data=payload, method='POST',
        headers={'Content-Type': 'application/json', 'x-api-key': key})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body, code = json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        body, code = e.read().decode()[:120], e.code
    return code, body, (time.time() - t0) * 1000


for name in ('baseline', 'h010'):
    code, body, ms = call(f'{DATA}/{name}.png')
    shown = body if code != 200 else {k: body.get(k) for k in
            ('visual_obstruction', 'est_range_m', 'source', 'processing_ms')}
    print(name, code, f'{ms:.0f} ms', shown)

code, body, ms = call(f'{DATA}/h010.png', key='wrong-key')
print('wrong key ->', code, '(expect 403)')

times = sorted(call(f'{DATA}/h010.png')[2] for _ in range(20))
print(f'20 calls: median {statistics.median(times):.0f} ms, worst {times[-1]:.0f} ms')