# Contributing

## One host per pull request

Each spec covers exactly one host, so each PR should too. A mirror is its own file that
extends the original, and it is still its own PR. This keeps a revert to one file.

## Before you open the PR

```bash
sourcelib check                                          # schema and layout, offline
sourcelib try specs/<host>.yaml <a novel url on that host>
```

Paste the `try` output into the PR. It is what a reviewer reads first.

**Read the chapter titles before believing the count.** A spec that reports 400 chapters has
often picked up a navigation menu or a "latest chapters" sidebar alongside the real list. A
spec that reports 12 on a long novel has usually found one page of a paginated table of
contents. Both look like success.

**Read one chapter body.** Empty chapters, or chapters full of advertising and translator
notes, are the usual failure and they pass every automated check.

## Naming

The filename is the normalised host: lowercase, no scheme, no `www.`, no port, no trailing
slash. `base_url` inside the file must agree with it, and CI checks that.

Do not add a separate file for `http://`, for `www.`, or for a mirror that serves identical
content under another name. Scheme and `www.` are folded automatically. A genuine mirror on a
different domain does get its own file, extending the original.

## When a site changes its markup

Add the new selector to `fallback`, do not replace the old one:

```yaml
title:
  css: h1.new-title
  fallback:
    - { css: h1.old-title }
```

Both then work, so a cached or partially-rolled-out page keeps reading correctly, and a wrong
guess degrades instead of breaking.

## When a site dies

Move the spec to `disabled/` and add a reason:

```yaml
disabled: "Domain expired"
```

Do not delete it. If the site comes back, or comes back rebuilt, the parser and the history
are still there. A site that has been redesigned is a parser fix, not a disabled source.

## When data cannot describe it

Some sites need real code: encrypted chapter bodies, a token handshake, a signature scheme.
Add a hook in `hooks/`, one function per file, named after the file. Reference it from the
spec by path. Before writing one, check whether a hook already exists that does the job, since
hooks are meant to be shared rather than copied per source.

Hooks are Python and go through review like any code. Everything else in a spec is data and is
reviewed as data.

**Write hooks from scratch.** This repository is Apache-2.0 and the crawler is
GPL-3.0-or-later, so a hook may not be copied or adapted from the crawler's existing sources.
Implement the site's behaviour, which is not anyone's copyright: the algorithm it uses, the
byte layout it expects, the header it checks. Reading the old code to understand a site is
fine; pasting it is not.

## Style

- Comments only where the reason is not visible in the file. A comment earns its place by
  recording why a selector is odd, or what the obvious alternative breaks.
- Prefer the simplest thing that works. If a `pipe` is not needed, leave it out; the defaults
  handle the common site.
