from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient


class SecurityHardeningMixin:
    def test_main_app_attaches_security_headers(self) -> None:
        main_module = __import__("app.main", fromlist=["app"])

        response = TestClient(main_module.app).get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")

    def test_security_headers_are_added_to_http_responses(self) -> None:
        main_module = __import__("app.main", fromlist=["add_security_headers"])

        app = FastAPI()
        main_module.add_security_headers(app)

        @app.get("/probe")
        def probe() -> dict[str, str]:
            return {"ok": "yes"}

        response = TestClient(app).get("/probe")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertEqual(response.headers["referrer-policy"], "no-referrer")
        self.assertEqual(
            response.headers["permissions-policy"],
            "camera=(), microphone=(), geolocation=()",
        )
        self.assertEqual(response.headers["cross-origin-opener-policy"], "same-origin")

    def test_security_headers_preserve_existing_response_headers(self) -> None:
        main_module = __import__("app.main", fromlist=["add_security_headers"])

        app = FastAPI()
        main_module.add_security_headers(app)

        @app.get("/download")
        def download() -> dict[str, str]:
            return {"ok": "yes"}

        response = TestClient(app).get(
            "/download",
            headers={"accept": "application/json"},
        )

        self.assertEqual(response.headers["content-type"], "application/json")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
