"""Report whether the installed interpreter is the one CI pins.

`schema/source.v1.json` carries the version that produced it in `x-generator`, and validate.yml
installs exactly that. So a contributor running a different version can see a spec pass locally and
fail on the pull request, or the reverse, with nothing in the output saying why.

The schema is the single source of truth for the pin. This only compares against it.
"""

from __future__ import annotations

import json
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

SCHEMA = Path("schema/source.v1.json")
PACKAGE = "lncrawl-sourcelib"


def pinned() -> str:
    generator = json.loads(SCHEMA.read_text(encoding="utf-8")).get("x-generator", "")
    return generator.partition("==")[2].strip()


def main() -> int:
    want = pinned()
    if not want:
        print(f"{SCHEMA} names no version in x-generator", file=sys.stderr)
        return 1

    try:
        have = version(PACKAGE)
    except PackageNotFoundError:
        print(f"{PACKAGE} is not installed. Run `uv sync`", file=sys.stderr)
        return 1

    if want == have:
        print(f"{PACKAGE} {have} matches the schema pin")
        return 0

    print(
        f"{PACKAGE} {have} is installed but the schema pins {want}, so a spec can pass here and "
        f"fail in CI.\nEither `uv pip install '{PACKAGE}=={want}'`, or regenerate the schema with "
        f"`sourcelib schema -o {SCHEMA}` if {have} is the version you mean to adopt.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
