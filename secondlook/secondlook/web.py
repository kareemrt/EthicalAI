"""A one-page local web app. Standard library only; binds to localhost.

Messages are analysed in memory and never stored, logged, or sent anywhere.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .engine import check

PAGE = (Path(__file__).parent / "static" / "index.html").read_bytes()
MAX_BYTES = 50_000


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if self.path != "/api/check":
            return self._send(404, b"not found", "text/plain")
        size = int(self.headers.get("Content-Length") or 0)
        if size > MAX_BYTES:
            return self._send(413, b'{"error":"message too long"}', "application/json")
        try:
            text = json.loads(self.rfile.read(size) or b"{}").get("message", "")
        except (ValueError, AttributeError):
            return self._send(400, b'{"error":"bad request"}', "application/json")
        body = json.dumps(check(str(text)).to_dict()).encode()
        self._send(200, body, "application/json")

    def log_message(self, *args):  # never log request contents
        pass


def serve(port: int = 8765) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Second Look running at http://127.0.0.1:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
