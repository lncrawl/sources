#!/usr/bin/env python3
"""Turn a health report into a GitHub step summary."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from check_health import describe


def main() -> int:
    report = Path(sys.argv[1] if len(sys.argv) > 1 else "health.json")
    if not report.is_file():
        print("No health report was produced.")
        return 0

    rows = json.loads(report.read_text(encoding="utf-8"))
    bad = [r for r in rows if not r["ok"]]

    print(f"### {len(rows) - len(bad)} of {len(rows)} hosts answered\n")
    if not bad:
        return 0

    print("| Host | Result |")
    print("|---|---|")
    for r in sorted(bad, key=lambda r: r["host"]):
        print(f"| {r['host']} | {describe(r)} |")

    print(
        "\nA failure here is a candidate for `disabled/`, not a verdict. Runners use "
        "datacentre addresses, so a site that blocks them looks identical to one that died."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
