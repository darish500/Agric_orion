import base64
import hmac
import json
import os
import time

import cv2
import numpy as np

try:
    from detect_obstruction import detect              # Lambda bundle: file sits beside this one
except ImportError:
    from agric_orion.detect_obstruction import detect  # local repo


def _response(code, body):
    return {'statusCode': code,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(body)}


def _authorized(event):
    expected = os.environ.get('API_KEY')
    if not expected:
        return True                      # no key configured (local runs)
    headers = {str(k).lower(): v for k, v in (event.get('headers') or {}).items()}
    return hmac.compare_digest(str(headers.get('x-api-key', '')), expected)


def handler(event, context=None):
    t0 = time.time()
    if not _authorized(event):
        return _response(403, {'error': 'forbidden'})
    try:
        body = event.get('body', event)       # Function URL wraps in 'body'; direct invoke doesn't
        if isinstance(body, str):
            body = json.loads(body)
        img_bytes = base64.b64decode(body['image_b64'])
        bgr = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if bgr is None or bgr.shape[:2] != (480, 640):
            return _response(400, {'error': 'expected a 640x480 PNG or JPEG image'})
    except (KeyError, ValueError, TypeError, AttributeError) as e:
        return _response(400, {'error': f'bad request: {e}'})

    result = detect(bgr)
    where = 'aws-lambda' if os.environ.get('AWS_LAMBDA_FUNCTION_NAME') else 'local-standin'
    result['source'] = f'opencv-{cv2.__version__}-{where}'
    result['processing_ms'] = round((time.time() - t0) * 1000, 1)
    return _response(200, result)