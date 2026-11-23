import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sources_json_path():
    return FIXTURES / "sources_synthetic.json"


@pytest.fixture
def sources_data(sources_json_path):
    return json.loads(sources_json_path.read_text())


class _Receiver:
    """A real local HTTP server that records POSTed alert payloads."""

    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.requests = []
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                receiver.requests.append(
                    {"path": self.path, "headers": dict(self.headers), "json": json.loads(body or b"null")}
                )
                code = receiver.statuses.pop(0) if receiver.statuses else 200
                self.send_response(code)
                self.end_headers()
                self.wfile.write(b"ok")

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/hook"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def webhook_receiver():
    def make(statuses=()):
        return _Receiver(statuses)

    return make
