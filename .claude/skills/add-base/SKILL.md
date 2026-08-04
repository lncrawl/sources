---
name: add-base
description: Convert a shared crawler template into a base spec that many hosts extend — reading the Python for intent rather than porting it, the flags that are not fields, and verifying against a live host before anything depends on it. Use when writing or changing anything in base/.
---

# Writing a base

A base is the only shared bottleneck in this repository. A mistake in `base/wordpress.yaml` reaches
59 hosts, so bases are written one at a time and each is verified against a live site before the next
one starts.

## Read the template for intent, never for text

The crawler's `lncrawl/templates/<name>.py` is the reference. It is **not** a thing to port:

- Its licence forbids it. This repository is Apache-2.0 and the crawler is GPL-3.0-or-later, so
  nothing here may be copied or adapted from it. A site's scheme is not anyone's copyright, so
  implementing the observable behaviour is fine; transcribing the code is not.
- It is frequently stale. The `novelmtl` draft described a pager that no longer exists on any host in
  that family. What the template tells you is *which page holds what* and *which quirks were worth
  handling*. Confirm every selector against a live page.

Read its docstring and comments before its methods. That is where the reason for an odd choice lives,
and the reason usually still applies even when the selector does not.

## Behavioural flags are not fields

Templates expose booleans that children flip. A base spec is data with a fixed schema, so it cannot
invent fields like these, and they port as **overrides of the thing the flag controlled**:

| Flag                          | Ports as                                              |
| ----------------------------- | ----------------------------------------------------- |
| `madara_body_from_paragraphs` | child overrides `chapter.body.pipe` to use `paragraphs` |
| `chapter_list_on_novel_page`  | child overrides `toc.request.from`                    |
| `madara_search_quote_mode`    | a different `search` URL template                     |
| `madara_search_max_results`   | `search.paginate.last` as a literal page number       |
| `landing_link_selector`       | a selector override                                   |

This is better than a boolean because the difference becomes visible in the child. But note the trap:
**mappings merge, so an override that means "not this" needs an explicit `null`** to delete the
inherited key. A child supplying `last` where the base set `next` leaves both and validation refuses
it, naming the child rather than the base.

Two attributes are deliberately not ported. `auto_create_volumes` is read by nothing except a dead
scaffolder, and declaring `toc.volumes` already carries the meaning. A source-level `version = 1` was
overwritten by the loader, so it never did anything.

## Prefer the free document, and prefer the site's own link

Two orderings that have each cost a hundred chapters:

- In `toc.request.from`, put `page: novel` **first** when the list is sometimes inline. It costs no
  request, and modern installations of several themes render the list into the novel page while the
  ajax endpoints they used to need now answer `404`.
- **Open the site's second page and see what it calls itself**, then say so with `first`.
  It is the number the site gives the page the stage already fetched, and it defaults to 1; a
  zero-based site sets `first: 0`. Getting it wrong **loses a page while reporting success**, which no
  trial can catch.

  Then prefer `last` over both alternatives wherever the site publishes a page total. It is safer
  than `while`, because a transient blank page cannot truncate the novel, and faster than either,
  because a known last page is fetched at the full width the rate limit allows while `while` walks in
  speculative windows and `next` cannot parallelise at all. Two specs moved this way: novelfire from
  `while` to `last` went 120 seconds to 52 for the same 3139 chapters, and novelmtl from `next` to
  `last` with `first: 0` reads the same 1333 while no longer depending on the theme happening to
  render a next link.

## Verify, then let hosts depend on it

Pick a host, write a three-line spec extending the base, and `poe try` it. Then `poe record`.

A base that has not been run is not finished. If no host in the family is reachable, say so in a
comment at the top of the base and **do not add a spec that extends it**, because an unverified base
with dependents looks finished and is not. `base/novelpub.yaml` is the worked example of this state.

## What to put in the base and what to leave out

In the base: everything the family shares, including the quirks. Out of the base: anything one host
does differently, which belongs in that host's spec as an override.

If the base needs a hook, it goes in `hooks/shared/` and the base binds it, so every child gets it
without repeating the binding. Read the `write-hook` skill.
