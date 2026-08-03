#!/usr/bin/env python3
"""Probe every live host and report the ones that stopped answering.

Reachability only. A host that answers is not necessarily still parseable, and a host
that fails here is not necessarily dead: it may be blocking datacentre addresses, which
is why the output is a report for a human rather than an automatic move to disabled/.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

import yaml

ROOT = Path(__file__).resolve().parents[2]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def probe(item: tuple[str, str], timeout: float) -> dict:
    host, url = item
    request = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {"host": host, "url": url, "status": response.status, "ok": True}
    except urllib.error.HTTPError as e:
        # A 403 or 503 is usually a bot wall rather than a dead site, so it is reported
        # but not called a failure.
        return {"host": host, "url": url, "status": e.code, "ok": e.code in (403, 503)}
    except Exception as e:
        return {"host": host, "url": url, "status": None, "ok": False, "error": str(e)}


def describe(result: dict) -> str:
    if result.get("error"):
        return result["error"]
    return f"HTTP {result['status']}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args()

    targets = []
    for path in sorted((ROOT / "specs").glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if doc.get("base_url"):
            targets.append((path.stem, doc["base_url"]))

    if not targets:
        print("no live specs to probe")
        return 0

    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(lambda t: probe(t, args.timeout), targets))

    failed = [r for r in results if not r["ok"]]
    for r in sorted(failed, key=lambda r: r["host"]):
        print("  {}: {}".format(r["host"], describe(r)))
    print(f"\n{len(results) - len(failed)} of {len(results)} answered")

    if args.output:
        args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
