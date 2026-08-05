"""The chapter list for a Blogger-hosted site, where a novel is a label and a chapter is a post.

Three things keep it a hook rather than a `paginate` block and two item lists.

The feed does not honour `max-results`. Asking a hundred returns 25, then 17, then 36 on one blog,
70, then 67, then 77 on another, and a hundred on a third, so the next offset is however many
actually arrived. `paginate.step` is a fixed stride, and a stride wider than the page silently skips
the difference: a novel loses most of its chapters and the crawl still reports success.

Both row tests compare a row against a value the crawl holds — a title against the label name, a
label against the query — and a step argument takes literals only, with no interpolation.

And the title is the label out of the URL, which needs percent-decoding that no filter or step
performs.

The alternative to the feed was walking the rendered archive behind its "older posts" link, which
ends when a page happens to look empty. That is how a partial chapter list gets mistaken for a whole
one.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote, unquote

#: The feed carrying titles and links. Asking for `default` instead pulls the full body of every
#: post, which is a far larger response for nothing the list uses.
FEED = "feeds/posts/summary"

#: What to ask for, not what arrives. Above whatever each blog will serve in one response the number
#: makes no difference at all — 100, 499 and 500 returned an identical 25 entries on one blog and an
#: identical 97 on another — so this is a ceiling rather than a page size, and the walk below reads
#: the length of every batch instead of trusting it. Kept under 500 because that is where a blog was
#: once seen to answer with an empty `entry` list while still reporting the real total, which is
#: indistinguishable from a label with no posts.
PAGE_SIZE = 100

LABEL_PATH = re.compile(r"/search/label/([^/?#&]+)")

#: A title often announces itself as a chapter after a dash. Matching the novel's name instead is
#: not reliable: the same blog writes "I Became a Rich..." in the label and "I Became the Rich..."
#: in half the titles, so the separator is the stable part.
CHAPTER_SPLIT = re.compile(r"\s+[-–—]\s+")
CHAPTER_LEAD = re.compile(r"^\s*(?:chapter|ch\.?|episode|ep\.?|part|vol)\b", re.I)


def label_of(url: str) -> str:
    found = LABEL_PATH.search(url)
    if not found:
        raise ValueError(f"not a novel url: {url}")
    return found.group(1)


def label_name(label: str) -> str:
    return unquote(label).replace("+", " ").strip()


def toc_items(value: Any, document: Any, ctx: Any) -> list[dict[str, str]]:
    label = label_of(getattr(document, "url", "") or "")
    name = label_name(label)
    # `label` is the path segment as the URL already spelled it, so it is encoded once. Quoting it
    # again turns a space into %2520 and the feed answers with nothing.
    entries = _walk(ctx.session, _origin(ctx), f"{FEED}/-/{label}")

    rows: list[dict[str, str]] = []
    # The feed answers newest first, which is the reverse of reading order.
    for entry in reversed(entries):
        link = _alternate(entry)
        title = str((entry.get("title") or {}).get("$t") or "").strip()
        if not link or not _is_chapter(title, name):
            continue
        rows.append({"url": link, "title": _chapter_title(title)})
    return rows


def _walk(session: Any, origin: str, path: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    start = 1
    while True:
        feed = _feed(session, origin, path, start)
        batch = list(feed.get("entry") or [])
        entries.extend(batch)
        total = _int((feed.get("openSearch$totalResults") or {}).get("$t"))
        if not batch or len(entries) >= total:
            return entries
        # By what arrived rather than by PAGE_SIZE: equal while the cap is honoured, and correct if
        # a blog ever returns short of it.
        start += len(batch)


def _feed(session: Any, origin: str, path: str, start: int) -> Mapping[str, Any]:
    url = f"{origin}/{path}?alt=json&max-results={PAGE_SIZE}&start-index={start}"
    response = session.fetch("GET", url)
    try:
        payload = json.loads(response.text)
    except ValueError as error:
        raise ValueError(f"{url} did not answer with JSON: {error}") from error
    return payload.get("feed") or {}


def _origin(ctx: Any) -> str:
    return str(getattr(ctx.spec, "base_url", "") or "").rstrip("/")


def _alternate(entry: Mapping[str, Any]) -> str:
    for link in entry.get("link") or ():
        if link.get("rel") == "alternate" and link.get("href"):
            return str(link["href"])
    return ""


def _is_chapter(title: str, name: str) -> bool:
    """A post titled exactly the label's name is its info page, not a chapter.

    On at least one of these themes that post renders no body at all, so it would sit at the top
    of the list as a chapter that can never download. The comparison is deliberately exact: a
    prefix test would also swallow real chapters.
    """
    return title.casefold() != name.casefold()


def _chapter_title(title: str) -> str:
    parts = CHAPTER_SPLIT.split(title, maxsplit=1)
    if len(parts) == 2 and CHAPTER_LEAD.match(parts[1]):
        return parts[1].strip()
    return title


def _int(value: Any) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def search_items(value: Any, document: Any, ctx: Any) -> list[dict[str, str]]:
    """Labels that look like novels, filtered to the query.

    Also a hook: the feed answers with every label on the blog at once, so matching the query and
    dropping the housekeeping labels are both row-level rejections. An `ItemList` cannot express
    one, because a row is dropped only when a *required* field resolves empty and neither test
    reads the field that is required.

    The query arrives on the request URL. The spec puts it in a `q=` parameter that Blogger
    ignores, which is the only place a `search.items` hook can read it from: the point's signature
    passes the document and the context, and the query is in neither.
    """
    needle = _query_of(getattr(document, "url", "") or "")
    origin = _origin(ctx)
    feed = _feed(ctx.session, origin, FEED, 1)

    rows: list[dict[str, str]] = []
    for row in feed.get("category") or ():
        label = str(row.get("term") or "").strip()
        if not label or not _is_novel_label(label):
            continue
        if needle and needle not in label.casefold():
            continue
        rows.append({"title": label, "url": f"{origin}/search/label/{quote(label)}"})
    return rows


def _query_of(url: str) -> str:
    found = re.search(r"[?&]q=([^&]*)", url)
    return unquote((found.group(1) if found else "").replace("+", " ")).strip().casefold()


#: A blog carries a few housekeeping labels beside its novels. These are worth naming in the
#: blog's own language: the Turkish blogs put nearly every post under "Bölüm", so leaving it in
#: offers a twelve-thousand-chapter phantom novel ahead of the real ones.
NON_NOVEL_LABELS = frozenset(
    {
        "chapter",
        "chapters",
        "bölüm",
        "bolum",
        "project",
        "projects",
        "announcement",
        "announcements",
        "news",
        "update",
        "updates",
        "release",
        "releases",
    }
)


def _is_novel_label(label: str) -> bool:
    return label.casefold() not in NON_NOVEL_LABELS


def novel_title(value: Any, document: Any, ctx: Any | None = None) -> str:
    """The label, decoded. The archive page's own heading carries the blog name as well."""
    return label_name(label_of(getattr(document, "url", "") or "")) or str(value or "")
