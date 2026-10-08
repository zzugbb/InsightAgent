#!/usr/bin/env python3
"""Aggregate low-sensitivity LLM HTTP attempt events from JSON log lines."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable


MODES = {"request", "stream"}
OUTCOMES = {
    "http_response", "success", "compat_retry", "http_error", "network_error",
    "provider_error", "empty_response", "interrupted", "unexpected_error",
}
STATUS_FAMILIES = {"1xx", "2xx", "3xx", "4xx", "5xx"}


def summarize(lines: Iterable[str]) -> dict[str, object]:
    by_mode: Counter[str] = Counter()
    by_outcome: Counter[str] = Counter()
    by_status_family: Counter[str] = Counter()
    malformed_lines = 0
    usage_available = 0
    durations: dict[str, list[float]] = {mode: [] for mode in sorted(MODES)}
    invalid_durations = 0
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            malformed_lines += 1
            continue
        if not isinstance(event, dict) or event.get("event") != "llm_http_attempt":
            continue
        mode = event.get("mode")
        outcome = event.get("outcome")
        family = event.get("status_family")
        if (
            not isinstance(mode, str) or mode not in MODES
            or not isinstance(outcome, str) or outcome not in OUTCOMES
            or (family is not None and (not isinstance(family, str) or family not in STATUS_FAMILIES))
        ):
            malformed_lines += 1
            continue
        duration = event.get("duration_ms")
        if (
            isinstance(duration, (int, float)) and not isinstance(duration, bool)
            and math.isfinite(duration) and duration >= 0
        ):
            durations[mode].append(float(duration))
        else:
            invalid_durations += 1
        by_mode[mode] += 1
        by_outcome[outcome] += 1
        if family is not None:
            by_status_family[family] += 1
        if event.get("usage_available") is True:
            usage_available += 1
    return {
        "event": "llm_http_attempt_summary",
        "total_attempts": sum(by_mode.values()),
        "by_mode": dict(sorted(by_mode.items())),
        "by_outcome": dict(sorted(by_outcome.items())),
        "by_status_family": dict(sorted(by_status_family.items())),
        "usage_available_attempts": usage_available,
        "malformed_lines": malformed_lines,
        "invalid_duration_attempts": invalid_durations,
        "duration_ms_by_mode": {
            mode: {
                "count": len(values),
                "min": round(min(values), 3) if values else None,
                "max": round(max(values), 3) if values else None,
                "mean": round(sum(values) / len(values), 3) if values else None,
            }
            for mode, values in durations.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, help="JSON-line log file; stdin by default")
    args = parser.parse_args()
    if args.path is None:
        summary = summarize(sys.stdin)
    else:
        with args.path.open(encoding="utf-8") as source:
            summary = summarize(source)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
