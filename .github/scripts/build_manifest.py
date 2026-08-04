#!/usr/bin/env python3
"""Build the sync manifest that installed apps poll.

One sha per distributable file, so a client can tell what changed without fetching
anything. Bases and hooks are listed in their own right because a spec's behaviour
changes when its base or hook does, while its own file stays byte-identical.

Never committed. This is a published artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[2]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_host(url: str) -> str:
    host = urlsplit(url if "//" in url else f"//{url}").netloc.lower()
    host = host.rsplit("@", 1)[-1].split(":", 1)[0]
    return host[4:] if host.startswith("www.") else host


def collect_specs(folder: str) -> dict:
    out = {}
    for path in sorted((ROOT / folder).glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        entry = {
            "file": f"{folder}/{path.name}",
            "sha": sha(path),
            "spec": doc.get("spec"),
        }
        if doc.get("extends"):
            entry["extends"] = doc["extends"]
        hooks = doc.get("hooks") or {}
        if hooks:
            entry["hooks"] = sorted(set(hooks.values()))
        if doc.get("disabled"):
            entry["reason"] = doc["disabled"]
        out[normalize_host(doc.get("base_url", path.stem))] = entry
    return out


def collect_files(folder: str, pattern: str) -> dict:
    return {
        path.stem: {"file": f"{folder}/{path.name}", "sha": sha(path)}
        for path in sorted((ROOT / folder).glob(pattern))
    }


def collect_hooks() -> dict:
    # Keyed by path, not stem: shared/x.py and sites/x.py are different files. Recursive
    # and unfiltered, so hooks/lib/ is listed too — a client that fetched only the files
    # specs name would install a hook whose imports it never downloaded.
    return {
        str(path.relative_to(ROOT)): {"sha": sha(path)}
        for path in sorted((ROOT / "hooks").rglob("*.py"))
        if "__pycache__" not in path.parts
    }


def build() -> dict:
    manifest = {
        "specs": collect_specs("specs"),
        "disabled": collect_specs("disabled"),
        "bases": collect_files("base", "*.yaml"),
        "hooks": collect_hooks(),
    }
    # The revision serves the app's ETag, so it has to move whenever any entry does
    # and stay put otherwise. Hashing the manifest body gives both for free.
    body = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return {"rev": hashlib.sha256(body).hexdigest()[:16], **manifest}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "manifest.json")
    ap.add_argument("--indent", type=int, default=None)
    args = ap.parse_args()

    manifest = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=args.indent) + "\n", encoding="utf-8")

    counts = {k: len(v) for k, v in manifest.items() if isinstance(v, dict)}
    print(f"{args.output.name} rev={manifest['rev']} {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
