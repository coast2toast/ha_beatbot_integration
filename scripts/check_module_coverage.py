"""Require above 95 percent statement coverage for every integration module."""

from __future__ import annotations

import json
import sys
from pathlib import Path

MINIMUM_EXCLUSIVE = 95.0
INTEGRATION_PREFIX = "custom_components/beatbot/"


def main() -> int:
    """Validate per-module coverage from a coverage.py JSON report."""
    report_path = Path(sys.argv[1] if len(sys.argv) > 1 else "coverage.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    failures: list[tuple[str, float]] = []

    for file_path, details in sorted(report["files"].items()):
        if not file_path.startswith(INTEGRATION_PREFIX):
            continue
        summary = details["summary"]
        if summary["num_statements"] == 0:
            continue
        percentage = float(summary["percent_covered"])
        if percentage <= MINIMUM_EXCLUSIVE:
            failures.append((file_path, percentage))

    if failures:
        for file_path, percentage in failures:
            print(f"{file_path}: {percentage:.2f}% (must be above 95%)")
        return 1

    print("Every non-empty Beatbot integration module is above 95% coverage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
