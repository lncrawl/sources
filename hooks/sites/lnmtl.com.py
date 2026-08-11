"""The chapter list for LNMTL, which the novel page ships as data and renders with Vue.

The chapter table in the served markup is the template rather than the result: its rows read
`<a href="{{ chapter.site_url }}">`, the literal placeholder, so nothing declarative can select a
chapter out of it.

What the page does carry is the bootstrap the component starts from — `lnmtl.volumes = [...]`, one
entry per volume — and the component then asks `/chapter?volumeId=<id>&page=<n>` for the rows. That
is two levels of walk, a page count per volume nested inside a list of volumes, and `paginate`
describes one. Hence a hook.

Both facts were read off the page and its own `volume-chapters` bundle, which spells the request as
`$http.get(route, {page, volumeId})`.
"""

from __future__ import annotations

import json
import re
from typing import Any

VOLUMES = re.compile(r"lnmtl\.volumes\s*=\s*")

#: Where the component sends its request. The page assigns the same value to a `route` variable, but
#: as a bare string rather than as a property of the bootstrap object, so it is not worth reading.
CHAPTERS = "/chapter"


def toc_items(value: Any, document: Any, ctx: Any) -> list:
    origin = str(getattr(document, "url", "") or "").split("/novel/")[0]
    rows = []
    for volume in _volumes(getattr(document, "text", "") or ""):
        rows.extend(_volume_rows(volume, origin, ctx))
    return rows


def _volume_rows(volume: dict, origin: str, ctx: Any) -> list:
    number = volume.get("number")
    rows: list = []
    page, last = 1, 1
    while page <= last:
        answer = json.loads(
            ctx.session.fetch("GET", f"{origin}{CHAPTERS}?volumeId={volume['id']}&page={page}").text
        )
        last = int(answer.get("last_page") or 1)
        for chapter in answer.get("data") or []:
            if chapter.get("site_url"):
                rows.append(
                    {
                        "title": chapter.get("title") or "",
                        "url": chapter["site_url"],
                        "volume": number,
                    }
                )
        page += 1
    return rows


def _volumes(markup: str) -> list:
    found = VOLUMES.search(markup)
    if not found:
        raise ValueError("the novel page carries no volume list")
    volumes, _ = json.JSONDecoder().raw_decode(markup[found.end() :])
    return [volume for volume in volumes if volume.get("id")]
