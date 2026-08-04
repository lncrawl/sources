#!/usr/bin/env python3
"""Write the published site's landing page.

Without one, the site root is a 404 while every file under it serves correctly. A client
fetching `manifest.json` never notices, but anyone who types the URL sees a broken site and has
no way to tell that from a failed deploy.

Generated rather than committed: the counts come from the manifest that was just built, so the
page cannot claim a corpus size the release does not actually carry.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

REPO = "https://github.com/lncrawl/sources"
RFC = f"{REPO}/blob/main/docs/0001-source-definition.md"

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>lncrawl source definitions</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{
    font: 16px/1.6 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
    max-width: 44rem; margin: 0 auto; padding: 2.5rem 1.25rem;
  }}
  h1 {{ font-size: 1.5rem; margin: 0 0 .25rem; }}
  .sub {{ opacity: .7; margin: 0 0 2rem; }}
  table {{ border-collapse: collapse; width: 100%; margin: 0 0 2rem; }}
  th, td {{ text-align: left; padding: .4rem .6rem; border-bottom: 1px solid rgba(128,128,128,.3); }}
  th {{ font-weight: 600; }}
  td.n {{ text-align: right; font-variant-numeric: tabular-nums; }}
  code {{
    font: .9em ui-monospace, SFMono-Regular, Menlo, monospace;
    background: rgba(128,128,128,.15); padding: .1rem .3rem; border-radius: 3px;
  }}
  pre {{ background: rgba(128,128,128,.12); padding: .8rem 1rem; border-radius: 6px; overflow-x: auto; }}
  footer {{ margin-top: 2.5rem; opacity: .7; font-size: .9rem; }}
</style>
</head>
<body>
<h1>lncrawl source definitions</h1>
<p class="sub">{release}Machine-readable index for <a href="{repo}">lncrawl/sources</a>.</p>

<table>
  <tr><th>What</th><th>Count</th></tr>
  <tr><td>Live sources</td><td class="n">{specs}</td></tr>
  <tr><td>Disabled</td><td class="n">{disabled}</td></tr>
  <tr><td>Shared bases</td><td class="n">{bases}</td></tr>
  <tr><td>Hook files</td><td class="n">{hooks}</td></tr>
</table>

<p>An installed app polls <a href="manifest.json"><code>manifest.json</code></a> and refetches
only the files whose digest moved. Every path in it resolves under this same origin, so
<code>specs/example.com.yaml</code> is served at <code>./specs/example.com.yaml</code>.</p>

<pre>curl {site}/manifest.json</pre>

<p>A source describes how to read one website as data: where the title is, how to find the
chapter list, which element holds the chapter text. <a href="{rfc}">RFC-0001</a> is the
normative definition of that format.</p>

<footer>
<code>rev {rev}</code> &middot; <a href="{repo}">repository</a> &middot;
<a href="{rfc}">format</a> &middot; not committed; built when a release is published
</footer>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--release", default="", help="the tag being published")
    ap.add_argument("--site", default="https://lncrawl.github.io/sources")
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    release = ""
    if args.release:
        release = f"Release <code>{html.escape(args.release)}</code>. "

    args.output.write_text(
        PAGE.format(
            release=release,
            repo=REPO,
            rfc=RFC,
            site=html.escape(args.site.rstrip("/")),
            rev=html.escape(str(manifest.get("rev", "unknown"))),
            specs=len(manifest.get("specs") or {}),
            disabled=len(manifest.get("disabled") or {}),
            bases=len(manifest.get("bases") or {}),
            hooks=len(manifest.get("hooks") or {}),
        ),
        encoding="utf-8",
    )
    print(f"{args.output} written for rev {manifest.get('rev')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
