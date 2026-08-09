"""The chapter list for MVLEmpyr, whose two domains serve one library.

The chapters live in a separate WordPress install and are grouped by a tag whose id the site
derives rather than publishes. Its own `novel-t-v5.js` raises 7 to the novel code modulo
1999999997 and asks `wp/v2/posts?tags=<that>`; the code is the only part on the page. Reading the
id back is not an option, because the tags endpoint answers `[]` to a lookup by slug, by search
and by id alike, and the site's own alternative is downloading its whole four-thousand-novel
catalogue to map the slug. Modular exponentiation is arithmetic, and a spec has none, which is
what keeps this a hook.

The rest would be declarable if the identity were: ordinary numbered paging over a JSON array,
with the total in a header. It is done here because the tag has to be computed before the first
request can be made at all.
"""

from __future__ import annotations

import json
from typing import Any

CHAPTER_API = "https://chap.heliosarchive.online/wp-json/wp/v2/posts"

#: What the site asks for, and it is honoured: 500 arrive when 500 exist. Above WordPress's own
#: default cap of 100, so the install has raised it and a smaller number would only cost requests.
PAGE_SIZE = 500

TAG_BASE = 7
TAG_MODULUS = 1999999997


def toc_items(value: Any, document: Any, ctx: Any) -> list[dict[str, str]]:
    code = _code(document)
    tag = pow(TAG_BASE, int(code), TAG_MODULUS)
    origin = str(getattr(ctx.spec, "base_url", "") or "").rstrip("/")

    posts = _walk(ctx.session, tag)
    # The feed answers newest first, and a chapter's place is in `acf` rather than in the order.
    posts.sort(key=lambda post: _number(post))

    rows: list[dict[str, str]] = []
    for post in posts:
        acf = post.get("acf") or {}
        number = acf.get("chapter_number")
        if number is None:
            continue
        rows.append(
            {
                "title": str(acf.get("ch_name") or f"Chapter {number}"),
                "url": f"{origin}/chapter/{code}-{number}",
            }
        )
    return rows


def _code(document: Any) -> str:
    node = document.node.select_one("#novel-code") if getattr(document, "node", None) else None
    code = node.get_text(strip=True) if node else ""
    if not code.isdigit():
        raise ValueError(f"no novel code on {getattr(document, 'url', '')}")
    return code


def _walk(session: Any, tag: int) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    page = 1
    while True:
        # `_fields` is WordPress's own trim. Everything else in a post is the rendered chapter,
        # which the list does not use and which the crawl fetches from the reader anyway: it is
        # 40% of the response for nothing.
        response = session.fetch(
            "GET", f"{CHAPTER_API}?tags={tag}&per_page={PAGE_SIZE}&page={page}&_fields=acf"
        )
        batch = json.loads(response.text)
        if not isinstance(batch, list) or not batch:
            return posts
        posts.extend(batch)
        total = _int(_header(response, "x-wp-total"))
        # The header is the authority where it arrives; a short batch is the fallback for an
        # install that hides it, and asking one page past the end answers 400 rather than [].
        if (total and len(posts) >= total) or len(batch) < PAGE_SIZE:
            return posts
        page += 1


def _header(response: Any, name: str) -> str:
    headers = getattr(response, "headers", None) or {}
    for key, value in headers.items():
        if str(key).lower() == name:
            return str(value)
    return ""


def _number(post: dict[str, Any]) -> int:
    return _int((post.get("acf") or {}).get("chapter_number"))


def _int(value: Any) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0
