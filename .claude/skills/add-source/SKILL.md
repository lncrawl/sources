---
name: add-source
description: Write or fix one host's source definition — reading a page with explain, picking an existing base, the fields that are actually required, verifying against the live site, and recording a fixture. Use when adding a host, repairing a broken spec, or working in specs/ or disabled/.
---

# Writing one host's spec

Read [docs/adding-a-source.md](../../../docs/adding-a-source.md) for the walkthrough and
[docs/patterns.md](../../../docs/patterns.md) for the shape catalogue. This file is what those do not
say: how to work efficiently and where the time goes.

## Order of operations

1. **Check `disabled/` and `specs/` first.** A file in `disabled/` says why it was turned off. If the
   site is back, `git mv` it and delete the `disabled:` line. Writing a fresh spec throws away the
   reason someone recorded.
2. **`poe explain <novel-url>`.** Never open the raw HTML first: it is hundreds of kilobytes and the
   digest is a few. What it tells you that matters most is whether the chapter list is in the page at
   all, and whether the site is a JSON shell.
3. **Try an existing base before writing anything.** Three lines, then run it. Around half of new
   hosts need nothing more, and most of the rest need one field overridden.
4. **`poe try`, and read the field lines.**
5. **`poe record`** once it passes, then **`poe all`**.

## The digest tells you the shape

| The digest says                          | Reach for                     |
| ---------------------------------------- | ----------------------------- |
| repeated `li.wp-manga-chapter`           | `base/wordpress.yaml`         |
| the same, body is images                 | `base/wordpress-manga.yaml`   |
| `/category/<slug>/` in the novel URL     | `base/wpcategory.yaml`        |
| `/search/label/<name>` in the novel URL  | `base/blogger.yaml`           |
| a data script, no repeated structure     | `json:`, not selectors        |
| "the chapter list may be built by scripts" | `toc.request.from`          |

## Write less than you think

Only `novel.title`, `toc.items` and `chapter.body` are required. Leave a field out and the interpreter
reads the page's own metadata: OpenGraph, then JSON-LD, then the document title. A missing cover,
author, tag list or synopsis is a warning, not a failure.

Declare `pipe:` only when the site is unusual. Every field kind has a default, and **a declared pipe
replaces the default rather than extending it**, so a needless one silently drops the deduplication or
paragraph handling you were relying on.

To add one step to a base's body pipe, reference the base's own by name rather than respelling it:
`pipe: [{strip_css: [...]}, clean_body]`. Do not redeclare `pipes.clean_body` in the child to do it,
because a mapping merges by key and the name would then refer to itself.

## Reading the result honestly

The exit code is the least useful part of the output.

- `ok` with a wrong-looking sample is the failure that matters. A title of `Home`, a synopsis that is
  the site's marketing blurb, a body of advertising: all `ok`.
- A chapter **count** is not a chapter **list**. Read the titles, and check the first and last are the
  first and last.
- If the count is short by a suspiciously round number, suspect pagination. `first` defaults to 1, so
  a site numbering from zero loses a page and still passes until the spec says `first: 0`. A feed
  addressed by item index sets `step` to the page size, and that size must be one the host serves in
  full.

`poe resolve specs/<host>.yaml` is the answer to "but the base sets that".

Two flags while iterating. `--toc-pages 4` stops the chapter-list walk early, which is where a trial
spends its time, and the report says the count was truncated. `--sample 25` reads more bodies before
you believe it: samples are spread evenly across the list, and a theme's oddities come in runs, so the
last bug found this way showed up in exactly one of three sampled chapters.

## When it will not cooperate

A site that needs an `if`, arithmetic, decryption, or a protocol the format does not model gets a
hook. Read the `write-hook` skill first, and check `hooks/shared/` before writing one: a hook shared
by five hosts beats five copies, and copy-per-source is exactly what the Python corpus accumulated.

Before concluding a host is dead: a parked domain, a Cloudflare challenge and an ISP block page all
answer `200`. Check the byte count and the redirect target, and check from a second network.

The signatures worth knowing, all measured on this corpus: a ~4.6 KB page titled `Redirecting...`
whose script names `router.parklogic.com` is a parked domain, and its size varies with the domain's
length because the name is interpolated. A ~475 byte body doing `window.location.replace` with a
`js=eyJ...` JWT is a live site behind a bot check. A 114 byte body redirecting to `/lander` is
parked. Nearly half the template-covered hosts turned out to be one of these.
