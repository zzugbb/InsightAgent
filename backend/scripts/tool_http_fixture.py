"""Local HTTP read fixture; no paid provider, request logging, or persistent resources."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Barrier, Event, Lock, Thread
from urllib.parse import urlsplit


class ReadService:
    def __init__(self, *, overlap=False, blocked=False, retry=False, response_payload=None):
        self.calls, self.active, self.max_active = [], 0, 0
        self.lock, self.started, self.finished, self.release = Lock(), Event(), Event(), Event()
        self.barrier = Barrier(2) if overlap else None
        self.retry, self.exited = retry, 0
        self.response_payload = response_payload
        if not blocked:
            self.release.set()

    def __enter__(self):
        fixture = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                path = urlsplit(self.path).path
                with fixture.lock:
                    fixture.calls.append({"path": path, "user": self.headers.get("X-User"),
                                          "authorization": self.headers.get("Authorization")})
                    attempt = sum(call["path"] == path for call in fixture.calls)
                    fixture.active += 1
                    fixture.max_active = max(fixture.max_active, fixture.active)
                    if fixture.active == 2:
                        fixture.started.set()
                try:
                    if fixture.barrier is not None:
                        fixture.barrier.wait(timeout=3)
                    fixture.release.wait(5)
                    status = 503 if fixture.retry and path == "/read_a" and attempt == 1 else 200
                    payload = json.dumps(fixture.response_payload if fixture.response_payload is not None else {
                        "result": 5 if path == "/read_a" else 7, "api_key": "response-fixture-secret"}).encode()
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                finally:
                    with fixture.lock:
                        fixture.active -= 1
                        fixture.exited += 1
                        if fixture.exited >= 2:
                            fixture.finished.set()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        return self

    def __exit__(self, *args):
        self.release.set()
        if self.barrier is not None:
            self.barrier.abort()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def tool_specs(self, *, opted=True, method="GET"):
        return {name: {"template": "calc_eval", "label": f"Fixture {name}",
                       "execution": {"kind": "http_json", "url": f"{self.url}/{name}", "method": method,
                                     "parallel_read_only": opted, "timeout_ms": 4000,
                                     "headers": {"Authorization": "Bearer request-fixture-secret", "X-User": "$user_id"},
                                     "result_fields": {"result": "result"}},
                       "result_preview_keys": ["result"], "result_output_keys": ["result"]}
                for name in ("read_a", "read_b")}
