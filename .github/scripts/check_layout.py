#!/usr/bin/env python3
"""Check the repository's own layout rules.

Spec *content* is validated by sourcelib against the published schema. This script
checks the things that are policy about this repo rather than about the format:
where a file lives, whether its name matches what it claims, and whether every
cross-file reference resolves.
"""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPECS, DISABLED, BASE, HOOKS = "specs", "disabled", "base", "hooks"
HOOK_DIRS = ("shared", "sites")

errors: list[str] = []
hooks_seen: set[Path] = set()


def fail(path: Path, message: str) -> None:
    errors.append(f"{path.relative_to(ROOT)}: {message}")


def normalize_host(url: str) -> str:
    host = urlsplit(url if "//" in url else f"//{url}").netloc.lower()
    host = host.rsplit("@", 1)[-1].split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    try:
        return host.encode("idna").decode("ascii")
    except UnicodeError:
        return host


def load(path: Path) -> dict | None:
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        fail(path, f"not valid YAML: {e}")
        return None
    if not isinstance(doc, dict):
        fail(path, "top level must be a mapping")
        return None
    return doc


def check_references(path: Path, doc: dict) -> None:
    extends = doc.get("extends")
    if extends is not None:
        if not isinstance(extends, str):
            fail(path, "extends must be a path string")
        else:
            target = ROOT / extends
            if not target.is_file():
                fail(path, f"extends points at a missing file: {extends}")
            elif extends.split("/", 1)[0] not in (SPECS, BASE):
                # Extending a disabled spec would leave dependents orphaned the moment
                # the parent is turned off, with nothing to signal it.
                fail(path, f"extends may only point into {SPECS}/ or {BASE}/: {extends}")

    hooks = doc.get("hooks") or {}
    if not isinstance(hooks, dict):
        fail(path, "hooks must be a mapping of hook point to path")
        return
    for point, ref in hooks.items():
        if not isinstance(ref, str):
            fail(path, f"hook {point} must be a path string")
            continue
        target = ROOT / ref
        if not target.is_file():
            fail(path, f"hook {point} points at a missing file: {ref}")
        elif ref.split("/")[:2] not in [[HOOKS, d] for d in HOOK_DIRS]:
            fail(path, f"hook {point} must live under {HOOKS}/shared/ or {HOOKS}/sites/: {ref}")
        else:
            hooks_seen.add(target.resolve())


def check_concrete(folder: str) -> set[str]:
    hosts: dict[str, Path] = {}
    for path in sorted((ROOT / folder).glob("*.yaml")):
        doc = load(path)
        if doc is None:
            continue

        if not isinstance(doc.get("spec"), int):
            fail(path, "spec must be present and an integer")

        base_url = doc.get("base_url")
        if not isinstance(base_url, str) or not base_url.strip():
            fail(path, f"{folder}/ requires a base_url")
        else:
            host = normalize_host(base_url)
            if host != path.stem:
                fail(path, f"filename must equal the normalized host, which is {host!r}")
            if host in hosts:
                fail(path, f"host already claimed by {hosts[host].name}")
            hosts[host] = path

        reason = doc.get("disabled")
        if folder == DISABLED and not (isinstance(reason, str) and reason.strip()):
            fail(path, "disabled/ requires a non-empty disabled reason")
        if folder == SPECS and reason is not None:
            fail(path, "a disabled reason means the file belongs in disabled/")

        check_references(path, doc)
    return set(hosts)


def check_base() -> None:
    for path in sorted((ROOT / BASE).glob("*.yaml")):
        doc = load(path)
        if doc is None:
            continue
        if not isinstance(doc.get("spec"), int):
            fail(path, "spec must be present and an integer")
        if doc.get("base_url") is not None:
            fail(path, f"{BASE}/ specs are abstract and must not declare a base_url")
        check_references(path, doc)


def check_orphan_hooks() -> None:
    """Flag hook files nothing reaches.

    lib/ is exempt by design: those modules exist to be imported. shared/ and sites/ hold
    hook functions, so one nobody references is either dead or a spec forgot it.
    """
    referenced_text = "\n".join(p.read_text(encoding="utf-8") for p in hooks_seen if p.is_file())
    for folder in HOOK_DIRS:
        for path in sorted((ROOT / HOOKS / folder).glob("*.py")):
            if path.resolve() in hooks_seen:
                continue
            # A shared hook may be reached by import rather than by a spec reference.
            if (
                f"import {path.stem}" in referenced_text
                or f"{folder}.{path.stem}" in referenced_text
            ):
                continue
            fail(path, "hook is neither referenced by a spec nor imported by one that is")


def main() -> int:
    live = check_concrete(SPECS)
    dead = check_concrete(DISABLED)
    check_base()
    check_orphan_hooks()

    for host in sorted(live & dead):
        errors.append(f"{host}: present in both {SPECS}/ and {DISABLED}/")

    if errors:
        print(f"{len(errors)} problem(s):\n")
        for line in errors:
            print(f"  {line}")
        return 1

    print(f"ok: {len(live)} live, {len(dead)} disabled, {len(hooks_seen)} hooks referenced")
    return 0


if __name__ == "__main__":
    sys.exit(main())
