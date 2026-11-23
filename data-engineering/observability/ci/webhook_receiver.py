"""Tiny alert webhook receiver for CI: appends each POSTed JSON body to a file.

Usage: python webhook_receiver.py PORT OUTPUT_JSONL
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT, OUT = int(sys.argv[1]), sys.argv[2]


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        with open(OUT, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(json.loads(body)) + "\n")
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
