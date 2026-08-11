"""The chapter list for ranobes, which the site renders from a payload rather than into markup.

The `/chapters/<id>/` pages carry their rows in a `window.__DATA__ = {…};` assignment and build the
visible list from it in the browser. `items.script` is the declarative answer to a payload in a
script, but it requires that element's text to *be* JSON, and this one is a statement with JSON
inside it, so nothing in the format reaches the rows.

The same payload also carries `pages_count`, so the walk is written here rather than as a
`paginate`: a `toc.items` hook replaces the whole list stage, and there is no way to keep the
declarative pager and hook only the parsing.

Rows come back as plain dictionaries. A request hook could have merged the pages into one JSON
document instead and left `items` declared, but that means returning an implementation's document
object, where this returns data any implementation of the RFC can accept.
"""

from __future__ import annotations

import json
import re
from typing import Any

PAYLOAD = re.compile(r"window\.__DATA__\s*=\s*(\{)", re.IGNORECASE)


def toc_items(value: Any, document: Any, ctx: Any) -> list:
    first = _payload(getattr(document, "text", "") or "")
    rows = list(first.get("chapters") or [])
    pages = int(first.get("pages_count") or 1)

    base = str(getattr(document, "url", "") or "").rstrip("/")
    for page in range(2, pages + 1):
        answer = ctx.session.fetch("GET", f"{base}/page/{page}/")
        rows.extend(_payload(answer.text).get("chapters") or [])

    # The site lists newest first, on every page and across them, so the whole run reverses.
    return [
        {"title": row.get("title") or "", "url": row.get("link") or ""}
        for row in reversed(rows)
        if row.get("link")
    ]


def _payload(markup: str) -> dict:
    """The assignment's object, decoded.

    Read with a raw decoder rather than a pattern for the closing brace: the object contains
    chapter titles, and a title with a brace in it would end the match early.
    """
    found = PAYLOAD.search(markup)
    if not found:
        raise ValueError("the page carries no chapter payload")
    value, _ = json.JSONDecoder().raw_decode(markup[found.start(1) :])
    return value
