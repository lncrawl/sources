---
name: write-hook
description: Write the Python escape hatch for a site that cannot be described as data — when a hook is justified, the signature and context, where the file goes, and the import rule CI enforces. Use when working in hooks/ or when a spec needs an if, arithmetic, decryption or a protocol the format does not model.
---

# Writing a hook

A hook is the **only** escape hatch. There is no way for a spec to name an arbitrary class or module,
and that is what lets the format be authored without a sandbox. So a hook is Python in a data
repository, and it keeps a review gate the specs do not have.

Section 7 of
[RFC-0001](https://github.com/lncrawl/sourcelib/blob/main/docs/0001-source-definition.md) is the
contract. Read it before writing one.

## First, be sure it is needed

Most reaches for a hook are a spec problem. Check in this order:

- **The list is elsewhere, not unreachable.** `toc.request.from` takes alternatives and picks the
  first that yields rows.
- **The value is in JSON, not in markup.** `json:` reads a dotted path, and `json:` plus `css:` on one
  item list means parse-then-select.
- **The request needs a value from another page.** `vars` reads from the URL, from a stage's document,
  or from a request of its own that is fetched once and reused. That last one covers a session token.
- **The pager is odd but has a link.** `paginate.next` follows an href verbatim.

A hook is genuinely justified for: arithmetic in pagination (an item offset, a zero-based index, a
range), rejecting a row on a field other than the required one, decryption or any transformation with
branching, and a protocol the request model does not describe.

Track the rate. Past roughly 15% of specs carrying a `hooks:` entry, the grammar is wrong and should
be extended rather than worked around one host at a time. Say so rather than writing the fifth copy.

## Where it goes

| Serving              | Path                     |
| -------------------- | ------------------------ |
| More than one host   | `hooks/shared/<name>.py` |
| Exactly one host     | `hooks/sites/<host>.py`  |
| Helpers for hooks    | `hooks/lib/<name>.py`    |

Check `hooks/shared/` before writing anything. A hook shared by five hosts beats five copies, and
copy-per-source is the failure the Python corpus is full of: `drop_leading` was reimplemented by hand
dozens of times because there was nowhere to put it once.

**A hook must not import from `hooks/sites/`.** CI enforces it, and the loader refuses it by reading
the syntax tree *before* the module executes, so a forbidden import cannot already have run. Reaching
into another host's implementation couples two sites that have never seen each other.

## The shape

The function is named for the point it serves, with the dot replaced by an underscore:
`toc.items` binds `toc_items`. The point set is closed and derived, so the name is already decided.
One file may define several.

Transform-shaped points take `(value, document, ctx)` and return the value. `check_response` and
`login` keep the shapes their jobs require.

`ctx` carries the HTTP session, the resolved spec, `vars` as templates see them, and `state`, a
mutable mapping scoped to one crawl. Use `ctx.key(name)` for a state key: a `shared/` hook serves many
specs, so two independent hooks reaching for `state["token"]` would collide.

**The context is a parameter and never ambient.** A hook module is imported once and shared by every
crawl, so only an argument can say which crawl it is serving. Never cache per-crawl data at module
scope.

## Write it against the site, not against the crawler

The same licence rule as everywhere here: nothing may be copied or adapted from the crawler's Python.
Implement the site's observable behaviour, which is a fact and not anyone's copyright.

Type the parameters as `Any`. A hook must work against any implementation of the RFC rather than
against one library's classes, which is why `hooks/**` ignores the unused-argument rule.

## Say why in the file

A hook is the one place in this repository where a paragraph of prose earns its keep. Its docstring
should say what the format could not express and what the alternative was, because the next person's
first question is whether the hook is still necessary. `hooks/shared/blogger_feed.py` is the worked
example: it records that the feed pages by item offset and reports a count of entries, so the next
offset is however many arrived, which no declared pagination can say.
