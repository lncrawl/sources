"""Ask every searchable host to find the novel this repository already recorded from it.

Nothing else tests a `search` stage. `try` skips it, a recording does not capture it, and CI never
runs it, so a search that finds nothing looks exactly like a search nobody has used. Sites do not
report the failure either: send a renamed form field or select a class the theme dropped and the
answer is `200` with the empty results page.

That is not hypothetical. On 2026-08-09 seven hosts were returning nothing — a search field renamed
from `searchkey` to `keyword` on one deployment of a family whose siblings still want the old name,
a heading that lost the class the selector matched on, an endpoint moved under `/novel-list/`, a
theme replaced wholesale — and every one of them passed every other gate.

**The query comes from the host's own fixture.** A recording stores the title of the novel it was
made from, so each host is asked for a book it demonstrably carries, and the check needs no list of
search terms to maintain and no guess about what language the site is in. A host with no fixture is
not checked, which is one more reason to record one.
"""

from __future__ import annotations

import argparse
import gzip
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
CLI = ROOT / ".venv" / "bin" / "sourcelib"

#: Errors that are the host refusing us rather than the spec being wrong. Reported, never failed on:
#: a challenge is `health.yml`'s subject, and a spec cannot fix one.
REFUSALS = ("challenge", "Super Bot Fight", "no detection layer", "Exhausted", "timed out")


def recorded_title(host: str) -> str:
    path = ROOT / "fixtures" / host / "recording.json.gz"
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return str((json.load(handle).get("expected") or {}).get("title") or "")
    except Exception:
        return ""


def queries(title: str) -> list[str]:
    """The title, then a shorter piece of it.

    A host that matches on a whole phrase answers the first; one that matches word by word, or
    that has since renamed the novel slightly, answers a later one. Reporting the best of the
    three keeps a fuzzy search engine from reading as a broken stage.
    """
    words = [word for word in re.split(r"\W+", title) if len(word) > 3]
    out = [title.strip()]
    if len(words) >= 2:
        out.append(" ".join(words[:2]))
    if words:
        out.append(max(words, key=len))
    return [q for q in dict.fromkeys(out) if q]


def searchable(host: str) -> bool:
    """Whether this spec resolves to a search stage it claims to support."""
    result = subprocess.run(
        [str(CLI), "resolve", str(ROOT / "specs" / f"{host}.yaml")],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    text = result.stdout
    if "can_search: false" in text:
        return False
    return bool(re.search(r"^search:", text, re.M))


def ask(host: str, query: str, timeout: int) -> tuple[int, str]:
    try:
        result = subprocess.run(
            [str(CLI), "try-search", str(ROOT / "specs" / f"{host}.yaml"), query, "--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(ROOT),
        )
        report = json.loads(result.stdout)
    except Exception as error:
        return -1, f"{type(error).__name__}: {error}"[:160]
    finding = (report.get("findings") or [{}])[0]
    return int(finding.get("count") or 0), str(report.get("error") or finding.get("detail") or "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hosts", nargs="*", help="Hosts to check. Empty means every fixture.")
    parser.add_argument("-o", "--output", default="search-health.json")
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()

    wanted = args.hosts or sorted(
        path.parent.name for path in (ROOT / "fixtures").glob("*/recording.json.gz")
    )

    rows = []
    for host in wanted:
        if not (ROOT / "specs" / f"{host}.yaml").exists():
            continue
        title = recorded_title(host)
        if not title:
            rows.append({"host": host, "verdict": "no-title"})
            continue
        if not searchable(host):
            rows.append({"host": host, "verdict": "no-search-stage"})
            continue

        best, detail, used = 0, "", ""
        for query in queries(title):
            count, note = ask(host, query, args.timeout)
            detail = detail or note
            if count > best:
                best, used, detail = count, query, note
            if best:
                break
        verdict = "ok" if best else ("refused" if any(w in detail for w in REFUSALS) else "empty")
        rows.append(
            {
                "host": host,
                "verdict": verdict,
                "results": best,
                "query": used,
                "title": title,
                "detail": detail[:200],
            }
        )
        print(f"{host:34} {verdict:16} {best:>4}  {used or detail[:60]}", flush=True)

    tally: dict = {}
    for row in rows:
        tally[row["verdict"]] = tally.get(row["verdict"], 0) + 1
    pathlib.Path(args.output).write_text(
        json.dumps({"tally": tally, "rows": rows}, indent=2, ensure_ascii=False) + "\n"
    )
    print("\n" + ", ".join(f"{count} {name}" for name, count in sorted(tally.items())))
    # Only `empty` fails: the stage ran, the host answered, and nothing came back.
    return 1 if tally.get("empty") else 0


if __name__ == "__main__":
    raise SystemExit(main())
