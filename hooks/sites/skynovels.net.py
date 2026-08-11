"""Repairing the chapter text SkyNovels serves, which arrives with its characters taken apart.

The API writes a watermark line into every chapter using mathematical alphanumerics — characters
outside the basic plane, which JSON escapes as a surrogate pair — and then inserts a zero-width
character *between* the two halves of each pair. A reader never sees the zero-width ones and the
browser reassembles nothing, because the site's own script strips them before display.

What reaches a Python string is therefore a run of unpaired surrogates, which is a string that
cannot be encoded: writing the chapter fails with `UnicodeEncodeError: surrogates not allowed`
rather than producing anything wrong, so every chapter on the host was unreadable.

There is no step for this. Removing the separators is a substitution, which the pipe cannot express
— `replace` takes literals and `regex` extracts rather than substitutes — and rejoining the halves
afterwards is an encode round trip.
"""

from __future__ import annotations

import re
from typing import Any

#: The separators measured in the watermark: zero-width space, non-joiner, joiner, word joiner and
#: the byte-order mark. Invisible either way, so removing them changes nothing a reader sees.
ZERO_WIDTH = re.compile("[​‌‍⁠﻿]")


def chapter_body(value: Any, document: Any, ctx: Any) -> Any:
    text = value if isinstance(value, str) else str(value or "")
    if not text:
        return value
    text = ZERO_WIDTH.sub("", text)
    # Once the halves are adjacent again this pairs them back into the characters they were.
    return text.encode("utf-16", "surrogatepass").decode("utf-16")
