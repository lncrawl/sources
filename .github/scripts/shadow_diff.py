"""Compare the two tiers on the hosts this repository has committed to.

While a host is served by a spec here and still has a legacy Python crawler in the app, both can be
run against the same novel and compared. That keeps a converted source verified continuously rather
than only on the day it was written, and it is the only check that notices a fix landing on the
legacy side and never reaching here.

The comparison lives here rather than in the interpreter because `sourcelib` must never import
`lncrawl` — that rule is what keeps retiring the first tier a deletion rather than a rewrite. It
drives the crawler as a subprocess rather than importing it, which also keeps this Apache-licensed
repository from linking a GPL one.

Which novel to read is not discovered. Every URL comes from a recorded fixture, so the set is the
one already committed to, and a run does not depend on a listing page still repeating the same
shape. Hosts with no fixture are simply not compared, and the summary says how many.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]

#: Fields worth failing over. `synopsis_digest` is deliberately absent: the two tiers normalise
#: whitespace differently often enough that it would drown the fields that matter.
COMPARED = ("title", "chapter_count", "first_chapter", "last_chapter")

#: Reported but never failed on. A tier finding a cover or an author the other misses is worth
#: seeing and is not a regression in either direction.
NOTED = ("cover_url", "authors", "tags", "volumes", "language")


def fixture_urls() -> dict:
    out = {}
    for path in sorted((ROOT / "fixtures").glob("*/recording.json.gz")):
        try:
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                out[path.parent.name] = json.load(handle)["url"]
        except Exception as error:  # pragma: no cover - a corrupt recording is not this check's job
            print(f"  {path.parent.name}: unreadable recording ({type(error).__name__})")
    return out


def dump(url: str, specs: str | None, timeout: int) -> dict:
    """Read *url* with whichever tier the app resolves, with `specs` deciding which that is."""
    environment = dict(os.environ, LNCRAWL_SPECS_PATH=specs or "")
    with tempfile.NamedTemporaryFile("r", suffix=".json", delete=False) as handle:
        target = handle.name
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "lncrawl",
                "dev",
                "shadow-dump",
                url,
                "--chapters",
                "3",
                "-o",
                target,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=environment,
        )
        body = pathlib.Path(target).read_text(encoding="utf-8").strip()
        if not body:
            return {"error": f"no output (exit {result.returncode}): {result.stderr[-200:]}"}
        return json.loads(body)
    except subprocess.TimeoutExpired:
        return {"error": f"timed out after {timeout}s"}
    except Exception as error:
        return {"error": f"{type(error).__name__}: {error}"[:200]}
    finally:
        pathlib.Path(target).unlink(missing_ok=True)


def _same(left, right) -> bool:
    """Whether two tiers found the same thing, ignoring how their cleaners spaced it.

    The two normalise whitespace differently often enough to matter: one writes
    "Children 2 — Having" where the other writes "Children 2— Having", and comparing
    those literally would leave the nightly permanently red over a space. What is being
    asked is whether both tiers found the same chapter, not whether they agree on
    typography, so whitespace is removed on both sides before comparing.
    """
    if isinstance(left, str) and isinstance(right, str):
        return "".join(left.split()) == "".join(right.split())
    if isinstance(left, list) and isinstance(right, list):
        return sorted("".join(str(x).split()) for x in left) == sorted(
            "".join(str(x).split()) for x in right
        )
    return left == right


def compare(host: str, url: str, spec: dict, legacy: dict) -> dict:
    row = {
        "host": host,
        "url": url,
        "spec_tier": spec.get("tier"),
        "legacy_tier": legacy.get("tier"),
    }

    if spec.get("error"):
        row["spec_error"] = spec["error"]
    if legacy.get("error"):
        row["legacy_error"] = legacy["error"]

    # A tier that could not run is not a mismatch. It is either a dead host, which `health.yml`
    # reports, or a broken tier, which is what the error field is for.
    if spec.get("error") or legacy.get("error"):
        row["verdict"] = "incomparable"
        return row

    if legacy.get("tier") != "legacy":
        # Nothing forced the legacy tier, so both dumps are the same tier and the comparison is
        # vacuous. Saying so beats reporting a perfect match.
        row["verdict"] = "no-legacy-crawler"
        return row

    differences = {
        field: {"spec": spec.get(field), "legacy": legacy.get(field)}
        for field in COMPARED
        if _same(spec.get(field), legacy.get(field)) is False
    }
    notes = {
        field: {"spec": spec.get(field), "legacy": legacy.get(field)}
        for field in NOTED
        if _same(spec.get(field), legacy.get(field)) is False
    }
    # A legacy crawler that read nothing is not evidence against the spec, and failing the run on
    # it would leave this nightly red until somebody deletes a crawler that is already being
    # shadowed. It is still worth reporting: it is one of the few signals that a legacy file has
    # rotted, and it says the host is safe to retire from the first tier.
    if differences and not legacy.get("chapter_count") and spec.get("chapter_count"):
        row["verdict"] = "legacy-stale"
    else:
        row["verdict"] = "differs" if differences else "matches"
    if differences:
        row["differences"] = differences
    if notes:
        row["notes"] = notes
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hosts", nargs="*", help="Hosts to compare. Empty means every fixture.")
    parser.add_argument("-o", "--output", default="shadow.json")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    urls = fixture_urls()
    wanted = [h for h in args.hosts if h] or sorted(urls)
    missing = [h for h in wanted if h not in urls]
    wanted = [h for h in wanted if h in urls]

    # A directory shaped like this repository but holding nothing. The app prefers a sibling
    # checkout when the configured path does not look like the definitions repository, so an
    # invalid path would silently leave the spec tier serving and compare a tier with itself.
    empty = pathlib.Path(tempfile.mkdtemp(prefix="no-specs-"))
    (empty / "specs").mkdir()
    (empty / "base").mkdir()

    rows = []
    for host in wanted:
        url = urls[host]
        print(f"-- {host}", flush=True)
        rows.append(
            compare(
                host, url, dump(url, str(ROOT), args.timeout), dump(url, str(empty), args.timeout)
            )
        )
        print(f"   {rows[-1]['verdict']}", flush=True)

    tally = {}
    for row in rows:
        tally[row["verdict"]] = tally.get(row["verdict"], 0) + 1
    report = {"compared": len(rows), "tally": tally, "without_fixture": missing, "rows": rows}
    pathlib.Path(args.output).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    print("\n" + ", ".join(f"{count} {verdict}" for verdict, count in sorted(tally.items())))
    if missing:
        print(f"{len(missing)} host(s) asked for without a fixture: {' '.join(missing[:8])}")
    return 1 if tally.get("differs") else 0


if __name__ == "__main__":
    raise SystemExit(main())
