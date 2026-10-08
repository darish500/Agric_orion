import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'cloud'))
from handler import handler


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(n).decode()
        r = handler({'body': body})
        out = r['body'].encode()
        self.send_response(r['statusCode'])
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    print('local stand-in for a Function URL on http://127.0.0.1:8080  (Ctrl+C to stop)')
    HTTPServer(('127.0.0.1', 8080), Handler).serve_forever()