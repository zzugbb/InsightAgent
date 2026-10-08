#!/usr/bin/env python3
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
from export_acceptance_evidence import fingerprint, sanitize_obj  # noqa: E402


class ExportEvidenceStaticTests(unittest.TestCase):
    def test_sanitize_redacts_and_fingerprints(self):
        payload = {
            "content": "secret answer body",
            "api_key": "sk-should-not-appear",
            "usage_json": '{"total_tokens": 1}',
        }
        out = sanitize_obj(payload)
        self.assertEqual(out["api_key"], "[redacted]")
        self.assertEqual(out["content"]["fingerprint"], fingerprint("secret answer body"))
        self.assertNotIn("sk-should-not-appear", json.dumps(out))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ExportEvidenceStaticTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        print("export_acceptance_evidence static tests passed")
    raise SystemExit(0 if result.wasSuccessful() else 1)
