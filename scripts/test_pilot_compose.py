#!/usr/bin/env python3
"""Configuration and redaction contracts for the pilot Compose entry point."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from pilot_compose import check_compose_config, compose, main
from test_pilot_deploy_config import valid_config


def compose_config():
    return {**valid_config(), "PILOT_POSTGRES_USER": "pilot", "PILOT_POSTGRES_PASSWORD": "private-password",
            "PILOT_POSTGRES_DB": "pilot", "INSIGHT_AGENT_DATABASE_URL": "postgresql://pilot:private-password@postgres:5432/pilot",
            "INSIGHT_AGENT_MODE": "remote", "INSIGHT_AGENT_PROVIDER": "openai", "INSIGHT_AGENT_MODEL": "pilot-model",
            "INSIGHT_AGENT_BASE_URL": "https://provider.example.test/v1", "INSIGHT_AGENT_API_KEY": "private-api-key"}


class PilotComposeTests(unittest.TestCase):
    def test_compose_config_requires_matching_internal_database(self):
        values = compose_config()
        self.assertEqual(check_compose_config(values), [])
        for key, value in (("PILOT_POSTGRES_PASSWORD", "different-password"),
                           ("INSIGHT_AGENT_DATABASE_URL", "postgresql://pilot:private-password@other:5432/pilot")):
            with self.subTest(key=key):
                self.assertIn("compose_database_mismatch", check_compose_config({**values, key: value}))

    def test_percent_encoded_database_password_matches_literal(self):
        values = compose_config()
        values.update(PILOT_POSTGRES_PASSWORD="literal$pass@word", INSIGHT_AGENT_DATABASE_URL="postgresql://pilot:literal%24pass%40word@postgres:5432/pilot")
        self.assertEqual(check_compose_config(values), [])

    def test_provider_missing_mock_or_bad_url_is_rejected(self):
        for changes, code in (({"INSIGHT_AGENT_API_KEY": ""}, "compose_remote_provider_required"),
                              ({"INSIGHT_AGENT_PROVIDER": "mock"}, "compose_remote_provider_required"),
                              ({"INSIGHT_AGENT_MODE": "mock"}, "compose_remote_provider_required"),
                              ({"INSIGHT_AGENT_BASE_URL": "https://user:secret@provider.test"}, "compose_provider_url_invalid")):
            with self.subTest(changes=changes):
                failures = check_compose_config({**compose_config(), **changes})
                self.assertIn(code, failures)
                self.assertNotIn("private-api-key", json.dumps(failures))

    def test_host_ports_must_be_valid_and_distinct(self):
        for port in ("0", "65536", "bad", "１２３４"):
            with self.subTest(port=port):
                self.assertIn("compose_host_port_invalid:PILOT_BACKEND_PORT",
                              check_compose_config({**compose_config(), "PILOT_BACKEND_PORT": port}))
        self.assertIn("compose_host_ports_conflict", check_compose_config({**compose_config(), "PILOT_BACKEND_PORT": "3001"}))

    def test_compose_uses_file_values_as_literals_and_does_not_echo(self):
        values = compose_config()
        values["INSIGHT_AGENT_API_KEY"] = "literal$OTHER"
        with patch.dict("os.environ", {"INSIGHT_AGENT_API_KEY": "wrong", "PILOT_BACKEND_PORT": "9999", "COMPOSE_FILE": "wrong"}):
            with patch("pilot_compose.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "resolved-secret", "")) as call:
                self.assertEqual(compose(values, "pilot", "config", "--quiet"), "resolved-secret")
        args, kwargs = call.call_args
        self.assertNotIn("literal$OTHER", " ".join(args[0]))
        self.assertEqual(kwargs["env"]["INSIGHT_AGENT_API_KEY"], "literal$OTHER")
        self.assertNotIn("PILOT_BACKEND_PORT", kwargs["env"])
        self.assertNotIn("COMPOSE_FILE", kwargs["env"])

    def cli(self, action, values, *, error=False):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "pilot.env"
            file.write_text("\n".join(f"{key}='{value}'" for key, value in values.items()))
            with patch("sys.argv", ["pilot_compose.py", action, "--env-file", str(file)]):
                with patch("pilot_compose.compose", side_effect=RuntimeError("private-api-key") if error else None) as command:
                    with patch("builtins.print") as output:
                        status = main()
        return status, json.loads(output.call_args.args[0]), command

    def test_check_does_not_start_services_and_redacts_failures(self):
        status, result, command = self.cli("check", compose_config())
        self.assertEqual((status, result["result"], command.call_count), (0, "PASS", 1))
        self.assertEqual(command.call_args.args[-2:], ("config", "--quiet"))
        status, result, _ = self.cli("up", compose_config(), error=True)
        self.assertEqual(status, 1)
        self.assertNotIn("private-api-key", json.dumps(result))

    def test_down_keeps_volumes_and_missing_account_does_not_start(self):
        _, _, command = self.cli("down", compose_config())
        self.assertEqual(command.call_args.args[-1], "down")
        self.assertNotIn("-v", command.call_args.args)
        status, _, command = self.cli("up", {**compose_config(), "INSIGHT_AGENT_API_KEY": ""})
        self.assertEqual(status, 1)
        command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
