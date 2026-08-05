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
- **The pager is odd but numbered.** `first` and `last` are the numbers the site puts on its pages,
  so a list numbered from zero is `first: 0` and not a hook. `paginate.next` follows an href verbatim
  where a site publishes no page numbers at all, and `step` set to the page size addresses a feed by
  the index of its first row — provided the host serves that size in full, since `step` is a fixed
  stride and a short page silently skips the difference.
- **The row to drop is identified by a field the stage does not need.** `require` names extra fields a
  row cannot do without, and a `reject` in that field's pipe is then the condition.
- **The junk is identified only by its wording.** `strip_matching` removes an element by what it says.

A hook is genuinely justified for: paging whose next address is a number only the response knows,
decryption or any transformation with branching, a protocol the request model does not describe, and
any condition that needs a `vars` or `query` value *inside* a step argument, since steps take literals
only. `hooks/shared/blogger_feed.py` is alive on three of those at once. Its feed under-delivers
`max-results` by an amount that varies per blog and per offset, so the walk has to advance by what
arrived; recognising the novel's own info post compares a row against the label name; and matching a
search query compares a label against `{query}`.

Two more limits are worth knowing before you conclude a spec cannot do something. A row that is a JSON
object honours only `json`, `const`, `pipe`, `default` and `all` — a `regex`, `attr` or `fallback` on
such a field is ignored rather than refused. And `const` is not interpolated, so a field cannot yet be
produced from `vars` alone. Both are interpreter defects against RFC-0001 rather than format decisions,
so check whether they are still true before writing Python around them.

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
example. Keep its docstring honest as the grammar grows, and re-measure before you rewrite it: the
claim that `step` had made its paging declarable was true of one blog and false of the other six.
