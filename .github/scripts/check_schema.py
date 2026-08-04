#!/usr/bin/env python3
"""Validate every spec document against the committed JSON Schema.

Needs no interpreter, only `jsonschema` and `pyyaml`, so it guards the repository before
`lncrawl-sourcelib` is published and keeps working if installing it ever breaks. It catches
unknown keys, wrong types and bad shapes. Cross-field rules, such as only one of `get`,
`post`, `page` and `from` being set, are not expressible in JSON Schema and belong to the
interpreter.

The schema editors read is this same file, so a document that fails here is one an author
would have seen underlined.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List

import jsonschema
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "schema" / "source.v1.json"
FOLDERS = ("specs", "disabled", "base")

# RFC-0001 specifies YAML 1.2. PyYAML implements 1.1, where `on`, `off`, `yes` and `no` are
# booleans, so `on: url` would parse as `True: "url"` and a var would lose its scope.
_BOOL_1_2 = re.compile(r"^(?:true|false|True|False|TRUE|FALSE)$")


class Loader(yaml.SafeLoader):
    """A SafeLoader with YAML 1.2 booleans."""


Loader.yaml_implicit_resolvers = {
    first: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:bool"]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
Loader.add_implicit_resolver("tag:yaml.org,2002:bool", _BOOL_1_2, list("tTfF"))


def documents() -> List[Path]:
    found: List[Path] = []
    for folder in FOLDERS:
        found.extend(sorted((ROOT / folder).glob("*.yaml")))
    return found


def load(path: Path) -> Dict[str, Any]:
    data = yaml.load(path.read_text(encoding="utf-8"), Loader=Loader)
    if not isinstance(data, dict):
        raise ValueError("a spec document must be a mapping")
    return data


def main() -> int:
    if not SCHEMA.exists():
        print(f"error: {SCHEMA.relative_to(ROOT)} is missing", file=sys.stderr)
        return 1

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)

    # The interpreter version that regenerates this file. Its absence would leave CI
    # installing whatever is latest, so an interpreter release could fail a source pull
    # request that touched neither the schema nor the interpreter.
    if not schema.get("x-generator"):
        print(f"error: {SCHEMA.name} declares no x-generator", file=sys.stderr)
        return 1

    files = documents()
    failed = 0
    for path in files:
        name = path.relative_to(ROOT)
        try:
            document = load(path)
        except Exception as error:
            failed += 1
            print(f"{name}: {error}", file=sys.stderr)
            continue

        errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
        if errors:
            failed += 1
            for error in errors:
                where = "/".join(str(part) for part in error.path) or "<root>"
                print(f"{name}: {where}: {error.message}", file=sys.stderr)

    print(f"ok: {len(files) - failed} of {len(files)} documents match the schema")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
