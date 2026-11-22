"""Tiny local web UI. Standard library only; binds to localhost so nothing leaves the machine."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .model import Model

PAGE = (Path(__file__).with_name("static") / "index.html").read_bytes()
MAX_BYTES = 20_000


def make_handler(model: Model):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path in ("/", "/index.html"):
                self._send(200, PAGE, "text/html; charset=utf-8")
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self) -> None:
            if self.path != "/api/check":
                return self._send(404, b"not found", "text/plain")
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BYTES:
                return self._send(413, b'{"error":"message too long"}', "application/json")
            try:
                text = json.loads(self.rfile.read(length) or b"{}").get("text", "")
            except (json.JSONDecodeError, AttributeError):
                return self._send(400, b'{"error":"invalid json"}', "application/json")
            body = json.dumps(model.score(str(text)).to_dict()).encode()
            self._send(200, body, "application/json")

        def log_message(self, *_args) -> None:  # never log message contents
            pass

    return Handler


def serve(port: int = 8765, host: str = "127.0.0.1") -> None:
    server = ThreadingHTTPServer((host, port), make_handler(Model.load()))
    print(f"RedFlag running at http://{host}:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
