#!/usr/bin/env python3
"""Focused checks for the pilot deployment preflight."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from check_pilot_deploy_config import check_config, main


def valid_config() -> dict[str, str]:
    return {
        "INSIGHT_AGENT_ENV": "production",
        "PILOT_FRONTEND_URL": "https://pilot.example.test",
        "NEXT_PUBLIC_API_BASE_URL": "https://api.example.test",
        "PILOT_FRONTEND_BUILD_API_BASE_URL": "https://api.example.test",
        "INSIGHT_AGENT_CORS_ORIGINS": '["https://pilot.example.test"]',
        "INSIGHT_AGENT_JWT_SECRET": "j" * 48,
        "INSIGHT_AGENT_SECRET_KEY": "e" * 48,
        "INSIGHT_AGENT_DATABASE_URL": "postgresql://pilot:private-password@postgres:5432/pilot",
        **{field: f"registry.example.test/{field.lower()}@sha256:{'a' * 64}"
           for field in (
               "PILOT_BACKEND_IMAGE", "PILOT_FRONTEND_IMAGE",
               "PILOT_CHROMA_IMAGE", "PILOT_POSTGRES_IMAGE",
           )},
    }


class PilotDeployConfigTests(unittest.TestCase):
    def test_valid_config_passes(self) -> None:
        self.assertEqual(check_config(valid_config()), [])

    def test_development_defaults_and_unpinned_images_fail_without_values(self) -> None:
        values = valid_config()
        values.update({
            "INSIGHT_AGENT_ENV": "development",
            "PILOT_FRONTEND_URL": "http://localhost:3001",
            "NEXT_PUBLIC_API_BASE_URL": "http://127.0.0.1:8000",
            "INSIGHT_AGENT_CORS_ORIGINS": '["*"]',
            "INSIGHT_AGENT_JWT_SECRET": " change-me-in-production ",
            "INSIGHT_AGENT_SECRET_KEY": "",
            "INSIGHT_AGENT_DATABASE_URL": "postgresql://insight:insight@postgres:5432/insightagent",
            "PILOT_CHROMA_IMAGE": "chromadb/chroma:latest",
        })
        failures = check_config(values)
        self.assertIn("production_environment_required", failures)
        self.assertIn("frontend_https_url_required", failures)
        self.assertIn("api_https_url_required", failures)
        self.assertIn("cors_origins_invalid", failures)
        self.assertIn("jwt_secret_invalid", failures)
        self.assertIn("encryption_key_invalid", failures)
        self.assertIn("database_credentials_invalid", failures)
        self.assertIn("image_digest_required:PILOT_CHROMA_IMAGE", failures)
        self.assertNotIn("change-me-in-production", json.dumps(failures))
        self.assertNotIn("private-password", json.dumps(failures))

    def test_reused_secret_fails(self) -> None:
        values = valid_config()
        values["INSIGHT_AGENT_SECRET_KEY"] = values["INSIGHT_AGENT_JWT_SECRET"]
        self.assertIn("separate_secrets_required", check_config(values))

    def test_invalid_urls_and_empty_file_fail_cleanly(self) -> None:
        values = valid_config()
        values["PILOT_FRONTEND_URL"] = "https://user:password@pilot.example.test"
        values["NEXT_PUBLIC_API_BASE_URL"] = "https://api.example.test:bad"
        values["INSIGHT_AGENT_CORS_ORIGINS"] = "not json"
        values["INSIGHT_AGENT_DATABASE_URL"] = "postgresql://bad:%GG@localhost:5432/pilot"
        failures = check_config(values)
        self.assertIn("frontend_https_url_required", failures)
        self.assertIn("api_https_url_required", failures)
        self.assertIn("cors_origins_invalid", failures)
        self.assertIn("database_credentials_invalid", failures)
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / "pilot.env"
            env_path.write_text("INSIGHT_AGENT_ENV=production\n")
            from unittest.mock import patch
            with patch("sys.argv", ["check_pilot_deploy_config.py", "--env-file", str(env_path)]):
                with patch("builtins.print") as output:
                    self.assertEqual(main(), 1)
            payload = json.loads(output.call_args.args[0])
            self.assertEqual(payload["result"], "FAIL")
            self.assertNotIn("pilot.env", json.dumps(payload))

    def test_cli_failure_never_echoes_secret_values(self) -> None:
        values = valid_config()
        values["INSIGHT_AGENT_DATABASE_URL"] = "postgresql://pilot:private-password@localhost:5432/pilot"
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / "pilot.env"
            env_path.write_text("\n".join(f"{key}={value}" for key, value in values.items()))
            from unittest.mock import patch
            with patch("sys.argv", ["check_pilot_deploy_config.py", "--env-file", str(env_path)]):
                with patch("builtins.print") as output:
                    self.assertEqual(main(), 1)
            report = output.call_args.args[0]
            self.assertIn("database_credentials_invalid", report)
            for secret in ("private-password", values["INSIGHT_AGENT_JWT_SECRET"], values["INSIGHT_AGENT_SECRET_KEY"]):
                self.assertNotIn(secret, report)


if __name__ == "__main__":
    unittest.main()
