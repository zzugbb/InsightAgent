#!/usr/bin/env python3
"""Check the committed OpenAPI surface against the current FastAPI app."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
BASELINE_PATH = BACKEND_DIR / "api_surface_baseline.json"
CHANGELOG_PATH = ROOT_DIR / "docs" / "api-changelog.md"
HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head", "options", "trace"})


def fingerprint(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_manifest(openapi: dict[str, Any]) -> dict[str, Any]:
    operations: dict[str, str] = {}
    for path, path_item in openapi.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS:
                continue
            operations[f"{method.upper()} {path}"] = fingerprint(
                {"operation": operation, "path_parameters": path_item.get("parameters", [])}
            )

    components: dict[str, str] = {}
    for group, entries in openapi.get("components", {}).items():
        for name, schema in entries.items():
            components[f"{group}.{name}"] = fingerprint(schema)

    return {
        "schema_version": 1,
        "api_version": str(openapi.get("info", {}).get("version", "")),
        "openapi_version": str(openapi.get("openapi", "")),
        "operations": dict(sorted(operations.items())),
        "components": dict(sorted(components.items())),
    }


def differences(baseline: dict[str, Any], current: dict[str, Any]) -> list[str]:
    changes: list[str] = []
    for field in ("schema_version", "api_version", "openapi_version"):
        if baseline.get(field) != current.get(field):
            changes.append(f"changed {field}")
    for section in ("operations", "components"):
        old = baseline.get(section, {})
        new = current.get(section, {})
        for key in sorted(old.keys() | new.keys()):
            if key not in old:
                changes.append(f"added {section}: {key}")
            elif key not in new:
                changes.append(f"removed {section}: {key}")
            elif old[key] != new[key]:
                changes.append(f"changed {section}: {key}")
    return changes


def current_manifest() -> dict[str, Any]:
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    from app.main import app

    return build_manifest(app.openapi())


def write_baseline(manifest: dict[str, Any], note: str) -> None:
    note = note.strip()
    if len(note) < 8 or "\n" in note or "\r" in note:
        raise ValueError("--note must be a single descriptive line of at least 8 characters")
    BASELINE_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    if not CHANGELOG_PATH.exists():
        CHANGELOG_PATH.write_text("# API 变更记录\n\n记录对外 HTTP/OpenAPI 契约的基线及后续变更；指纹差异需要人工判断兼容性。\n")
    with CHANGELOG_PATH.open("a") as changelog:
        changelog.write(f"\n- {datetime.now().astimezone().date()} · API {manifest['api_version']}：{note}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Update baseline and append a changelog entry")
    parser.add_argument("--note", help="Required one-line explanation for --write")
    args = parser.parse_args()
    if args.write != bool(args.note):
        parser.error("--write and --note must be used together")

    manifest = current_manifest()
    if args.write:
        try:
            write_baseline(manifest, args.note)
        except ValueError as exc:
            parser.error(str(exc))
        print(f"API baseline updated: {len(manifest['operations'])} operations, {len(manifest['components'])} components")
        return 0

    if not BASELINE_PATH.is_file():
        print(f"API baseline missing: {BASELINE_PATH}", file=sys.stderr)
        return 1
    baseline = json.loads(BASELINE_PATH.read_text())
    changes = differences(baseline, manifest)
    if changes:
        print("API surface changed; review compatibility and record the decision:", file=sys.stderr)
        for change in changes[:20]:
            print(f"  {change}", file=sys.stderr)
        if len(changes) > 20:
            print(f"  ... and {len(changes) - 20} more", file=sys.stderr)
        return 1
    print(f"API surface ok: {len(manifest['operations'])} operations, {len(manifest['components'])} components")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
