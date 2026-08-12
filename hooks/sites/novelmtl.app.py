"""The reader page's text for NovelMTL, which the app ships as a JavaScript assignment.

Everything this site renders comes from `window.__INITIAL_STATE__ = {…};`. That is a statement with
JSON inside it rather than a JSON document, so `css: script` with a `json:` path cannot read it —
that pair requires the element's text to *be* JSON. The failure is quiet in a way worth naming: the
novel's title, author and description appear to work, because when a declared extractor yields blank
the interpreter falls back to the page's own metadata (RFC-0001 section 3.8) and those happen to be
in the OpenGraph tags. A chapter body has no such fallback, so it is the field that shows the truth.

Only the body is hooked. The rest of the source is declarative, and the metadata chain covers the
fields the state blob would otherwise supply.
"""

from __future__ import annotations

import json
import re
from typing import Any

STATE = re.compile(r"window\.__INITIAL_STATE__\s*=\s*(\{)")


def chapter_body(value: Any, document: Any, ctx: Any) -> Any:
    state = _state(getattr(document, "text", "") or "")
    page = ((state.get("novels") or {}).get("page")) or {}
    text = str(page.get("content") or "")
    if not text.strip():
        raise ValueError("the reader page carries no text for this page")
    return "".join(f"<p>{line}</p>" for line in text.splitlines() if line.strip())


def _state(markup: str) -> dict:
    """The assignment's object, decoded.

    Read with a raw decoder rather than a pattern for the closing brace, because the object holds
    the whole chapter and a brace in the prose would end the match early.
    """
    found = STATE.search(markup)
    if not found:
        raise ValueError("the page carries no __INITIAL_STATE__")
    value, _ = json.JSONDecoder().raw_decode(markup[found.start(1) :])
    return value
