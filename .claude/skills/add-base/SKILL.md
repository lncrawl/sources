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
| `madara_search_max_results`   | `search.paginate.limit`                               |
| `landing_link_selector`       | a selector override                                   |

This is better than a boolean because the difference becomes visible in the child. But note the trap:
**mappings merge, so an override that means "not this" needs an explicit `null`** to delete the
inherited key. A child supplying `count` where the base set `next` leaves both and validation refuses
it, naming the child rather than the base.

Two attributes are deliberately not ported. `auto_create_volumes` is read by nothing except a dead
scaffolder, and declaring `toc.volumes` already carries the meaning. A source-level `version = 1` was
overwritten by the loader, so it never did anything.

## Prefer the free document, and prefer the site's own link

Two orderings that have each cost a hundred chapters:

- In `toc.request.from`, put `page: novel` **first** when the list is sometimes inline. It costs no
  request, and modern installations of several themes render the list into the novel page while the
  ajax endpoints they used to need now answer `404`.
- Prefer `paginate.next` over `paginate.count` unless you have checked the site's numbering. `{page}`
  counts from 2 for the pages after the first, so a zero-based or offset-paged site is off by one and
  **loses a whole page while reporting success**. Open the site's second page and see what it calls
  itself. A next link is followed verbatim and cannot be off by one.

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
