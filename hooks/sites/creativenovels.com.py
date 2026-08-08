"""The chapter list for creativenovels.com, which answers in a delimited string of its own.

Everything about reaching the list is declarable and is declared in the spec: the post id comes off
the page's shortlink, the security token out of the inline `chapter_list_summon` object, and the
request itself is an ordinary form POST to `admin-ajax.php`. Only the answer needs Python.

The response is neither markup nor JSON. It opens with a literal `success.define.`, then repeats
`<url>.data.<title>.data.<date>.data.<status>` separated by `.end_data.`, so there is nothing for
`css`, `json` or `script` to select and no way to split a row out of it. That is the whole reason
this file exists; if the site ever answers in JSON, the spec can read it with `json:` and this
should go.

The leading marker is checked rather than assumed. The same endpoint answers a plain `fail` when the
token has expired, and a hook that skipped the check would return no rows and be indistinguishable
from a novel with an empty list.
"""

from __future__ import annotations

from html import unescape
from typing import Any

#: What a good answer opens with. Everything before the first record.
PREFIX = "success.define."

#: Between two records, and between the fields inside one.
BETWEEN_ROWS = ".end_data."
BETWEEN_FIELDS = ".data."


def toc_items(value: Any, document: Any, ctx: Any) -> list:
    body = (getattr(document, "text", "") or "").strip()
    if not body.startswith(PREFIX):
        # A refused token answers `fail`. Returning nothing here would read as a novel with no
        # chapters, so say what happened instead.
        raise ValueError(f"the chapter list endpoint answered {body[:40]!r}")

    rows = []
    for record in body[len(PREFIX) :].split(BETWEEN_ROWS):
        # A record carries four fields, not two: the date and a release status follow the title.
        # Partitioning on the first separator would put all three in the title.
        fields = record.split(BETWEEN_FIELDS)
        if len(fields) < 2 or not fields[0].strip():
            continue
        rows.append({"url": fields[0].strip(), "title": unescape(fields[1]).strip()})
    return rows
