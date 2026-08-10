"""The chapter body for wtr-lab, which the site encrypts before sending it to its own reader.

Two things keep this a hook rather than a request and a `json` path.

The body arrives AES-GCM encrypted. The reader chunk decrypts it in the browser with a key it
carries in the clear, and the format has no cipher and should not grow one: this is one site's
scheme, not a shape worth putting in a grammar.

And the reader is a POST whose payload names the novel, the chapter and a translation service, then
answers with a `success` flag and a `code` rather than a status. `CHAPTER_LOCKED` and
`requireTurnstile` both arrive as HTTP 200, so a stage that only read the status would store the
refusal as a chapter.

**The text this returns is the original, not the translation.** `web` is the only service an
unauthenticated request may ask for — `google`, `bing` and `raw` all answer `"Unsupported
translation service"` — and it returns the raw. The site's English chapter titles are stored per
chapter and come from the list instead, which is why the two do not match. The Python crawler this
replaces asks for exactly the same thing, so nothing is lost by converting.

The scheme below was read from the site's own reader chunk, which spells out the prefix, the three
base64 fields, the order they are joined in, and the key.

The spec points `chapter.request` at the one-row slice of the chapter list rather than at the
reader page. Both name the chapter, but the slice is a couple of hundred bytes against the page's
thirty-odd kilobytes, and it also carries the chapter's own id, which the POST wants and the URL
does not have.
"""

from __future__ import annotations

import base64
import json
import re
from typing import Any

READER = "https://wtr-lab.com/api/reader/get"

#: The key the reader chunk hands to `crypto.subtle.importKey`, verbatim and in the clear.
KEY = b"IJAFUUxjM25hyzL2AZrn0wl7cESED6Ru"

#: GCM's tag is the last 16 bytes of the joined ciphertext. The browser's `crypto.subtle` takes the
#: two together; every Python AES-GCM implementation wants them apart.
TAG_BYTES = 16

#: The only service an unauthenticated caller may name. See above.
SERVICE = "web"

RAW_ID = re.compile(r"/api/chapters/(\d+)")


def chapter_body(value: Any, document: Any, ctx: Any) -> str:
    raw_id, row = _from_slice(document)
    payload = {
        "translate": SERVICE,
        "language": "en",
        "raw_id": raw_id,
        "chapter_no": int(row["order"]),
        "retry": False,
        "force_retry": False,
    }
    if row.get("id"):
        payload["chapter_id"] = int(row["id"])

    answer = json.loads(ctx.session.fetch("POST", READER, json=payload).text)
    if not answer.get("success"):
        raise ValueError(_refusal(answer))

    body = (((answer.get("data") or {}).get("data")) or {}).get("body")
    if body is None:
        raise ValueError("the reader answered with no body")
    lines = _decrypt(body) if isinstance(body, str) else body
    return "".join(f"<p>{line}</p>" for line in lines if str(line).strip())


def _from_slice(document: Any) -> tuple:
    """The novel and the chapter, out of the one-row list the stage fetched."""
    url = str(getattr(document, "url", "") or "")
    found = RAW_ID.search(url)
    if not found:
        raise ValueError(f"not a chapter slice: {url}")
    rows = (getattr(document, "parsed", None) or {}).get("chapters") or []
    if not rows:
        raise ValueError(f"the chapter slice is empty: {url}")
    return int(found.group(1)), rows[0]


def _refusal(answer: dict) -> str:
    """Why the reader said no, in the site's own words.

    Worth separating: `CHAPTER_LOCKED` is a paywall and `requireTurnstile` is this address being
    past its allowance, and the two want different responses from whoever reads the log.
    """
    if answer.get("requireTurnstile"):
        seen, limit = answer.get("count"), answer.get("threshold")
        counted = f" ({seen} of {limit})" if seen and limit else ""
        return f"this address is past the chapters it is allowed{counted}"
    return str(answer.get("code") or answer.get("error") or "the reader refused the request")


def _decrypt(blob: str) -> list:
    """Undo what the reader chunk does, in the order it does it.

    The prefix says whether the plaintext is a JSON array of lines or one string. The rest is three
    base64 fields separated by colons: the IV, then the two halves of the ciphertext in the order
    they are *concatenated*, which is the third field before the second.
    """
    as_array = False
    if blob.startswith("arr:"):
        as_array, blob = True, blob[4:]
    elif blob.startswith("str:"):
        blob = blob[4:]

    parts = blob.split(":")
    if len(parts) != 3:
        raise ValueError(f"not the encrypted shape: {len(parts)} field(s)")
    iv, tail, head = (base64.b64decode(part) for part in parts)

    joined = head + tail
    text = _aesgcm(iv, joined[:-TAG_BYTES], joined[-TAG_BYTES:])
    return json.loads(text) if as_array else [text]


def _aesgcm(iv: bytes, ciphertext: bytes, tag: bytes) -> str:
    try:
        from Crypto.Cipher import AES  # type: ignore[import-not-found]
    except ImportError as error:  # pragma: no cover - depends on the host environment
        raise RuntimeError(
            "wtr-lab sends its chapters encrypted and needs pycryptodome to read them"
        ) from error
    return AES.new(KEY, AES.MODE_GCM, nonce=iv).decrypt_and_verify(ciphertext, tag).decode("utf-8")
