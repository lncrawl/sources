"""The chapter body for docln, which the site obfuscates before sending it to its own reader.

The served `#chapter-content` holds nothing but the chapter title. The prose sits beside it in a
`#chapter-c-protected` element as a JSON array of base64 chunks, each XORed against a per-chapter
key the same element carries in the clear, and the reader assembles it in the browser.

Nothing in the format can express this. The chunks are ordered by a four-digit prefix inside each
string rather than by their position in the array, the payload is a keyed byte transform, and the
key changes per chapter, so it cannot be a step argument — those take literals. Rendering the page
in a browser would also work and needs no code at all, but it costs a browser per chapter, and a
novel here runs to hundreds.

The scheme below was read from the site's own `scripts/app.js`, which names the three schemes, the
attributes they are configured by, and the order the chunks are joined in.

Notes are inlined rather than dropped. The reader turns a `[noteN]` marker into a tooltip whose
text lives in a `#noteN` element further down the page, so the marker alone is meaningless in a
file — but the text is right there to fold in.
"""

from __future__ import annotations

import base64
import json
import re
from typing import Any

PROTECTED = "#chapter-c-protected"

#: Each chunk opens with its own position, zero-padded, and the array arrives shuffled.
ORDER_DIGITS = 4

NOTE = re.compile(r"\[note(\d+)\]", re.IGNORECASE)


def chapter_body(value: Any, document: Any, ctx: Any) -> Any:
    node = getattr(document, "node", None)
    holder = node.select_one(PROTECTED) if node is not None else None
    if holder is None:
        # Not every chapter is protected, and an unprotected one is already prose.
        return value
    return _inline_notes(_decode(holder), node)


def _decode(holder: Any) -> str:
    scheme = holder.get("data-s") or "none"
    key = (holder.get("data-k") or "").encode("utf-8")
    try:
        chunks: list[str] = json.loads(holder.get("data-c") or "[]")
    except ValueError as error:
        raise ValueError("the protected block is not a chunk list") from error
    if not chunks:
        raise ValueError("the protected block is empty")

    chunks.sort(key=lambda chunk: int(chunk[:ORDER_DIGITS]))
    return "".join(_chunk(chunk[ORDER_DIGITS:], scheme, key) for chunk in chunks)


def _chunk(payload: str, scheme: str, key: bytes) -> str:
    raw = base64.b64decode(payload[::-1] if scheme == "base64_reverse" else payload)
    if scheme == "xor_shuffle":
        if not key:
            raise ValueError("the chapter is xor_shuffle encoded and carries no key")
        raw = bytes(byte ^ key[index % len(key)] for index, byte in enumerate(raw))
    return raw.decode("utf-8")


def _inline_notes(text: str, node: Any) -> str:
    def swap(found: re.Match[str]) -> str:
        content = node.select_one(f"#note{found.group(1)} .note-content")
        return f" ({content.get_text(' ', strip=True)})" if content else ""

    return NOTE.sub(swap, text)
