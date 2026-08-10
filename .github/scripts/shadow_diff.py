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


#: What the app says when the tier it was forced onto serves the domain not at all, as opposed to
#: serving it badly. Matched as text because the two tiers run as subprocesses on purpose.
NO_CRAWLER = "No crawler found for the domain"

#: Hosts where the two tiers genuinely disagree and the spec is the one to believe, each with the
#: measurement that settled it. Kept beside the script rather than in a spec comment because it is
#: a fact about the pair of tiers, and it disappears with the legacy crawler.
EXPECTED = ROOT / ".github" / "shadow-expected.json"


def expected() -> dict:
    try:
        return json.loads(EXPECTED.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


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
            # The whole of stderr, not its tail. The app prints a framed traceback, so the
            # sentence that says what happened is near the top and the last 200 characters are
            # the box drawing around it — which is how a host with no legacy crawler at all read
            # as a broken one.
            return {"error": f"no output (exit {result.returncode}): {result.stderr}"}
        return json.loads(body)
    except subprocess.TimeoutExpired:
        return {"error": f"timed out after {timeout}s"}
    except Exception as error:
        return {"error": f"{type(error).__name__}: {error}"[:200]}
    finally:
        pathlib.Path(target).unlink(missing_ok=True)


def _plain(value: str) -> str:
    """A title with the typography the two tiers disagree about removed.

    Whitespace first: they normalise it differently often enough to matter, one writing
    "Children 2 — Having" where the other writes "Children 2— Having". Then trailing
    sentence punctuation, because one cleaner strips it and the other keeps what the site
    wrote — "Capítulo 1. Prólogo." against "Capítulo 1. Prólogo" is the same chapter and
    would otherwise hold a nightly red over a full stop.

    Only the trailing kind. A period inside a title is part of its numbering.
    """
    return "".join(value.split()).rstrip(".,;:·。、")


def _same(left, right) -> bool:
    """Whether two tiers found the same thing, ignoring how their cleaners wrote it.

    What is being asked is whether both tiers found the same chapter, not whether they
    agree on typography.
    """
    if isinstance(left, str) and isinstance(right, str):
        return _plain(left) == _plain(right)
    if isinstance(left, list) and isinstance(right, list):
        return sorted(_plain(str(x)) for x in left) == sorted(_plain(str(x)) for x in right)
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

    # A tier that could not run is not a mismatch, but which tier failed decides everything. A
    # spec that could not read its host is a defect here and fails the run. A legacy crawler
    # that could not, on a host whose spec read it fine, is the clearest retirement signal the
    # project has: six of the seven such rows on 2026-08-09 were crawlers raising on a live site
    # the spec had just read. Both failing means the host is down, which `health.yml` reports.
    if spec.get("error"):
        row["verdict"] = "both-failed" if legacy.get("error") else "spec-failed"
        return row
    if legacy.get("error"):
        # A host this repository added itself has no legacy crawler to fall back to, so forcing
        # the first tier does not fail, it finds nothing at all. That is not a broken crawler and
        # must not be counted as retirement evidence, which is the whole value of the verdict.
        if NO_CRAWLER in str(legacy["error"]):
            row["verdict"] = "no-legacy-crawler"
            return row
        row["verdict"] = "legacy-broken"
        return row

    if spec.get("tier") != "spec":
        # The spec did not serve its own host, so this run compared the legacy crawler with
        # itself and every field it reports is meaningless. The usual cause is an interpreter
        # older than the spec: the app logs "spec could not be read" and falls through to the
        # first tier, which is indistinguishable from having no spec at all. One stale
        # environment once turned a third of the corpus into a legacy-versus-legacy diff whose
        # only symptom was a host that disagreed with itself between runs.
        row["verdict"] = "spec-not-served"
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
    elif differences and host in expected():
        # A difference someone has looked at and judged the spec to be the better of the two.
        # Reported every night and never failed on, because the alternative is a check that
        # stays red until the legacy crawler is deleted, and a check nobody can make green is
        # one everybody stops reading.
        row["verdict"] = "expected"
        row["expected"] = expected()[host]
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
    # Everything that says something is wrong *here* fails. `spec-not-served` counts because it
    # means the run proved nothing, and a check that silently proves nothing is worse than one
    # that is red. `legacy-broken` and `legacy-stale` do not: both are the first tier failing on
    # a host this repository reads correctly, which is the outcome the whole migration wants.
    failing = ("differs", "spec-not-served", "spec-failed")
    return 1 if any(tally.get(name) for name in failing) else 0


if __name__ == "__main__":
    raise SystemExit(main())
