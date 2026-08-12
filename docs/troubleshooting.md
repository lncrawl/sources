# Troubleshooting

What a failure means, and where to look next. Every message below is one this repository's tooling
actually prints.

## Reading `try` output

The exit code is the verdict, but the verdict is the least useful part. Read the field lines:

- `ok` with a sample that looks wrong is the failure mode that matters. A title of `"Home"` or a
  synopsis that is the site's marketing blurb both count as `ok`.
- `none` on a cover, author, tag list or synopsis is a warning, not an error. Real pages omit those,
  and failing on them would reject working sources.
- A chapter count is not a chapter list. Read the titles.

`uv run poe resolve specs/<host>.yaml` prints the document with every ancestor merged, which is the
answer to "but the base sets that". A deep `extends` chain is otherwise guesswork.

## Messages

**`matched no chapters`** — `toc.items.css` selected nothing on the page that was fetched. Usually
the list is not on the novel page at all; see the `from` alternatives in
[patterns.md](patterns.md). Confirm what was fetched before changing the selector, because a
selector is rarely wrong about a document you have actually looked at.

**`no alternative in from produced a document`** — every alternative failed, and the message names
what each one did. A `404` means that endpoint does not exist on this installation, which is fine if
a later alternative works. All of them failing usually means the address needs a var the page did
not supply.

**`{vars.x} has no value in this context`** — the var produced nothing. Check its `on:`: a var
reading `on: novel` runs against the novel stage's document, which is not the HTML page if that
stage fetches JSON.

**`page: 'novel' has not been fetched yet`** — a stage referenced a document that had not been
produced. Stages run `search`, `novel`, `toc`, `chapter`, so a chapter may reuse the novel document
and not the reverse. A stage cannot reuse its own, which is the natural typo: `novel.request` with
`page: novel` reads as "the novel page" and means "the document this stage is about to produce".

**`expected a node, got str`** — a pipe step that needs an element was handed text. Something earlier
flattened it: `text` and `paragraphs` both end the node part of a pipe, so node steps come first.

**`only one of while, last, next may be set`** — usually a child overriding a base's pagination. The
keys merge rather than replace, so supplying a second condition leaves both in the resolved spec, and
the error names the child rather than the base it came from. Write `next: null` (or whichever the base
set) to delete the inherited one. `uv run poe resolve` shows what actually merged.

**`a css selector needs a parsed document`** — the response was not HTML. If it is JSON, use `json:`.

**`produced nothing, and a novel needs a title`** — the title selector missed and the page's own
metadata had nothing either. Check the page is what you think: a parked domain and a Cloudflare
challenge both answer `200` with a plausible-looking document.

**`is out of date; run sourcelib schema -o …`** — the committed schema does not match the model of
the installed interpreter. Usually the interpreter is a different version than the schema pins; run
`uv run poe pin`.

**`lncrawl-sourcelib X is installed but the schema pins Y`** — your interpreter is not the one CI
uses, so a spec can pass here and fail on the pull request, or the reverse. The message names both
ways to fix it.

## The site fights back

**A page that is suspiciously small.** A few kilobytes where you expected hundreds is usually a
challenge page or an error page, not the site. `explain` prints the byte count first for this reason.

**A redirect to `ww1.`, `ww19.`, `ww547.`** and similar prefixes is domain parking. The host is gone,
not blocked, and the answer is a `disabled/` entry rather than a new selector.

**A dead site is not always dead.** Some networks answer a blocked domain with their own `200` page,
which is indistinguishable from a site that changed. Before moving a spec to `disabled/`, check from
somewhere else. A host wrongly disabled is worse than one left alone: the memory of why travels with
the file and the next person believes it.

**`curl` fails where the tooling works.** The interpreter's HTTP layer impersonates a browser's TLS
fingerprint; `curl` does not. A Cloudflare error from `curl` says nothing about the site.

**"The browser could not clear it" usually means nobody was watching.** The solver runs hidden for
the first part of its budget and only then opens a window — and that window is waiting for a *person*
to answer the challenge. Run unattended it spends the rest of the budget waiting for someone who is
not there and reports failure, which reads exactly like a host that cannot be cleared. Set
`SOURCELIB_BROWSER=headed` and sit with it before believing otherwise. Eleven hosts recorded here as
permanently blocked turned out to serve 26 KB to 267 KB of real markup on the first attended run.

**One attempt is not a measurement.** Retry a challenged host three times before writing anything
down. Two of those eleven cleared only on the third try, and one cleared on the first after failing
outright a minute earlier.

**Probing a challenged host spends something.** Repeated attempts degrade what it will serve you: one
went from the full page, to alternating full and partial, to a fifth of the size with no title, over
perhaps fifteen tries. Work in a small number of deliberate attempts rather than a loop, and if a host
starts answering worse than it did, stop and come back rather than concluding it is broken.

## A pass that is not one

The failures worth fearing are the ones that report success.

**A chapter count that is short by exactly one page.** The site's paging does not start where
`{page}` does, and `first` is how to say so. Every field still produces something. See
[patterns.md](patterns.md#say-what-the-site-numbers-its-pages-from). Open the site's second page and
check what it calls itself.

**A body that is mostly advertising.** `try` reports the length, not the quality. Read one.

**Every novel field `ok`, and the body empty.** The metadata chain fills a field whose extractor
yields nothing, so `title`, `authors` and `synopsis` go green off the page's OpenGraph tags whether or
not the selector behind them ever resolved. `chapter.body` has no such fallback. A run where the novel
reads perfectly and only the body fails is the shape of an extractor that never worked at all — on
`novelmtl.app` a `json:` path pointed into a script the interpreter could not parse, and the three
novel fields hid it. Change one to something deliberately wrong: if it still reports the same value,
the chain is answering, not the spec.

**A title that is the site's name.** When a selector misses, the interpreter falls back to the page's
own metadata, and a parked domain or a challenge page has a perfectly good `<title>`. A novel called
`Home` or the site's brand means the selector missed and the fallback covered for it.

**A row field named `id`.** `try` passes and the crawler raises `Chapter() got multiple values for
keyword argument 'id'`, which names neither the spec nor the field. A row's extra fields are handed
to the app's chapter model as keyword arguments, so a field sharing a name with one of its own —
`id`, `body`, `images`, `success`, `crawler_version` — collides. An API returning bare ids is the
common case; call the field `chapter_id` or `part_id`.

**Rows at the end of the list that are adverts.** A site selling early access often posts one row per
membership tier, worded and linked exactly like a chapter: `Chapter 2210 - 2230 Gold (40 chapters)`.
The page behind it carries a title marked as a teaser and no prose, so keeping them ends a book with
a run of empty chapters. Nothing on the chapter page distinguishes it until it is fetched, and only
the row's own wording does, so `reject` in the title's pipe with `require: [title]` on the list is the
fix. `try` samples the last chapter for this reason: it is where such rows live.

## Offline checks disagree with the live site

Fixtures test the spec, never the site. A green `poe fixtures` means the spec still reads the pages
recorded that day, and it will stay green long after the site has been redesigned. The nightly health
sweep is the counterweight. If `try` fails and `fixtures` passes, the site changed; re-record after
fixing the spec.
