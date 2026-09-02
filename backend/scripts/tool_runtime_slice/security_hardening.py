from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient


class SecurityHardeningMixin:
    def test_security_refresh_request_rejects_blank_refresh_token(self) -> None:
        auth_routes_module = __import__(
            "app.api.routes.auth",
            fromlist=["RefreshRequest"],
        )

        with self.assertRaisesRegex(ValueError, "refresh token is required"):
            auth_routes_module.RefreshRequest(refresh_token=" " * 16)

    def test_security_refresh_tokens_treat_blank_token_as_invalid(self) -> None:
        auth_session_module = __import__(
            "app.services.auth_session_service",
            fromlist=["refresh_auth_tokens"],
        )

        self.assertIsNone(auth_session_module.refresh_auth_tokens(refresh_token=" " * 16))

    def test_security_access_token_rejects_signed_non_hs256_algorithm(self) -> None:
        security_module = __import__(
            "app.security",
            fromlist=["_b64url_encode", "_sign_hs256", "parse_access_token"],
        )
        config_module = __import__("app.config", fromlist=["get_settings"])
        settings = config_module.get_settings()

        header = {"alg": "none", "typ": "JWT"}
        payload = {
            "sub": "user-security-token",
            "email": "user@example.com",
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        }
        header_part = security_module._b64url_encode(  # type: ignore[attr-defined]
            json.dumps(header, separators=(",", ":")).encode("utf-8")
        )
        payload_part = security_module._b64url_encode(  # type: ignore[attr-defined]
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        signed_input = f"{header_part}.{payload_part}".encode("ascii")
        sign_part = security_module._b64url_encode(  # type: ignore[attr-defined]
            security_module._sign_hs256(  # type: ignore[attr-defined]
                signed_input,
                settings.auth_jwt_secret,
            )
        )
        token = f"{header_part}.{payload_part}.{sign_part}"

        with self.assertRaisesRegex(ValueError, "unsupported token algorithm"):
            security_module.parse_access_token(token)

    def test_security_access_token_requires_jwt_type_header(self) -> None:
        security_module = __import__(
            "app.security",
            fromlist=["_b64url_encode", "_sign_hs256", "parse_access_token"],
        )
        config_module = __import__("app.config", fromlist=["get_settings"])
        settings = config_module.get_settings()

        header = {"alg": "HS256", "typ": "not-jwt"}
        payload = {
            "sub": "user-security-token",
            "email": "user@example.com",
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        }
        header_part = security_module._b64url_encode(  # type: ignore[attr-defined]
            json.dumps(header, separators=(",", ":")).encode("utf-8")
        )
        payload_part = security_module._b64url_encode(  # type: ignore[attr-defined]
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
        signed_input = f"{header_part}.{payload_part}".encode("ascii")
        sign_part = security_module._b64url_encode(  # type: ignore[attr-defined]
            security_module._sign_hs256(  # type: ignore[attr-defined]
                signed_input,
                settings.auth_jwt_secret,
            )
        )
        token = f"{header_part}.{payload_part}.{sign_part}"

        with self.assertRaisesRegex(ValueError, "invalid token type"):
            security_module.parse_access_token(token)

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
