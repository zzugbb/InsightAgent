from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient


class SecurityHardeningMixin:
    def test_security_production_cors_rejects_wildcard_origin(self) -> None:
        main_module = __import__(
            "app.main",
            fromlist=["_validate_cors_origins_for_environment"],
        )

        with self.assertRaisesRegex(RuntimeError, "wildcard CORS origin"):
            main_module._validate_cors_origins_for_environment(  # type: ignore[attr-defined]
                SimpleNamespace(
                    app_env="production",
                    cors_origins=["https://app.example.com", "*"],
                )
            )

    def test_security_development_cors_allows_wildcard_origin(self) -> None:
        main_module = __import__(
            "app.main",
            fromlist=["_validate_cors_origins_for_environment"],
        )

        self.assertIsNone(
            main_module._validate_cors_origins_for_environment(  # type: ignore[attr-defined]
                SimpleNamespace(app_env="development", cors_origins=["*"])
            )
        )

    def test_security_access_token_signing_rejects_default_secret_in_production(
        self,
    ) -> None:
        security_module = __import__(
            "app.security",
            fromlist=["create_access_token", "get_settings"],
        )
        original_get_settings = security_module.get_settings
        security_module.get_settings = lambda: SimpleNamespace(  # type: ignore[assignment]
            app_env="production",
            auth_jwt_secret="dev-only-change-me",
            auth_access_token_ttl_minutes=5,
        )
        try:
            with self.assertRaisesRegex(RuntimeError, "default JWT secret"):
                security_module.create_access_token(
                    user_id="user-default-secret",
                    email="user@example.com",
                )
        finally:
            security_module.get_settings = original_get_settings  # type: ignore[assignment]

    def test_security_access_token_parse_rejects_default_secret_in_production(
        self,
    ) -> None:
        security_module = __import__(
            "app.security",
            fromlist=["_b64url_encode", "_sign_hs256", "parse_access_token", "get_settings"],
        )
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": "user-default-secret",
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
            security_module._sign_hs256(signed_input, "dev-only-change-me")  # type: ignore[attr-defined]
        )
        token = f"{header_part}.{payload_part}.{sign_part}"
        original_get_settings = security_module.get_settings
        security_module.get_settings = lambda: SimpleNamespace(  # type: ignore[assignment]
            app_env="production",
            auth_jwt_secret="dev-only-change-me",
        )
        try:
            with self.assertRaisesRegex(RuntimeError, "default JWT secret"):
                security_module.parse_access_token(token)
        finally:
            security_module.get_settings = original_get_settings  # type: ignore[assignment]

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
