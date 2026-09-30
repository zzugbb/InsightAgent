import asyncio
import json

from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from starlette.responses import StreamingResponse

from app.request_observability import add_request_observability


class RequestObservabilityMixin:
    def test_request_observability_logs_route_template_without_sensitive_values(self) -> None:
        app = FastAPI()

        @app.get("/items/{item_id}")
        def get_item(item_id: str, response: Response) -> dict[str, str]:
            response.headers["X-Request-ID"] = "downstream-id"
            return {"item_id": item_id}

        add_request_observability(app)
        with self.assertLogs("insightagent.http", level="INFO") as logs:
            response = TestClient(app).get(
                "/items/private-item?token=hidden-token",
                headers={"X-Request-ID": "untrusted-id"},
            )

        request_id = response.headers["X-Request-ID"]
        self.assertRegex(request_id, r"^[0-9a-f]{32}$")
        self.assertNotEqual(request_id, "untrusted-id")
        self.assertEqual(
            sum(key.lower() == b"x-request-id" for key, _ in response.headers.raw),
            1,
        )
        payload = json.loads(logs.output[0].split(":", 2)[2])
        self.assertEqual(payload["request_id"], request_id)
        self.assertEqual(payload["route"], "/items/{item_id}")
        self.assertEqual(payload["method"], "GET")
        self.assertEqual(payload["status_code"], 200)
        self.assertGreaterEqual(payload["duration_ms"], 0)
        self.assertNotIn("private-item", logs.output[0])
        self.assertNotIn("hidden-token", logs.output[0])

    def test_request_observability_records_unmatched_and_failure_without_raw_path(self) -> None:
        app = FastAPI()

        @app.get("/fail")
        def fail() -> None:
            raise RuntimeError("private failure text")

        add_request_observability(app)
        client = TestClient(app, raise_server_exceptions=False)
        with self.assertLogs("insightagent.http", level="INFO") as logs:
            missing = client.get("/missing/private-token")
            failed = client.get("/fail")

        self.assertEqual(missing.status_code, 404)
        self.assertEqual(failed.status_code, 500)
        self.assertRegex(failed.headers["X-Request-ID"], r"^[0-9a-f]{32}$")
        payloads = [json.loads(line.split(":", 2)[2]) for line in logs.output]
        self.assertEqual([(item["route"], item["status_code"]) for item in payloads], [
            ("<unmatched>", 404),
            ("/fail", 500),
        ])
        self.assertNotIn("private-token", "\n".join(logs.output))
        self.assertNotIn("private failure text", "\n".join(logs.output))

    def test_main_app_exposes_request_id_to_allowed_browser_origin(self) -> None:
        from app.main import app

        with self.assertLogs("insightagent.http", level="INFO"):
            response = TestClient(app).get(
                "/openapi.json",
                headers={"Origin": "http://127.0.0.1:3001"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertRegex(response.headers["X-Request-ID"], r"^[0-9a-f]{32}$")
        self.assertIn("X-Request-ID", response.headers["access-control-expose-headers"])

    def test_request_observability_measures_stream_until_completion(self) -> None:
        app = FastAPI()

        @app.get("/stream")
        def stream() -> StreamingResponse:
            async def chunks():
                yield b"first"
                await asyncio.sleep(0.02)
                yield b"last"

            return StreamingResponse(chunks())

        add_request_observability(app)
        with self.assertLogs("insightagent.http", level="INFO") as logs:
            response = TestClient(app).get("/stream")
        self.assertEqual(response.content, b"firstlast")
        payload = json.loads(logs.output[0].split(":", 2)[2])
        self.assertGreaterEqual(payload["duration_ms"], 15)
