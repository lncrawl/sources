# Contributing

## One host per pull request

Each spec covers exactly one host, so each PR should too. A mirror is its own file that
extends the original, and it is still its own PR. This keeps a revert to one file.

## Getting the tools

**If you already have Lightnovel Crawler**, you can use it. Every command below also exists as
`lncrawl dev …`, so there is no second tool to learn:

```bash
lncrawl dev check
lncrawl dev try specs/<host>.yaml <a novel url on that host>
```

**If you only want to write specs**, install the interpreter on its own. It is a small package
and pulls in no application, no web server and no database:

```bash
pip install lncrawl-sourcelib
```

The rest of this guide uses the short `sourcelib` form. Prefix it with `lncrawl dev` if that is
the one you have.

## Writing one

Start from the page rather than from its markup. `explain` prints a few kilobytes describing a
page that is usually several hundred: what repeats and how many rows, which script carries the
data, what metadata exists, and where a page count would come from.

```bash
sourcelib explain <a novel url on that host>
$EDITOR specs/<host>.yaml
```

## Before you open the PR

```bash
sourcelib check                                          # resolve and validate, offline
sourcelib try specs/<host>.yaml <a novel url on that host>
```

Paste the `try` output into the PR. It is what a reviewer reads first. Every line names the
field it came from and the line it lives on, so a failure says where to look.

Once it passes, record the pages so CI can notice a future change breaking it:

```bash
sourcelib record specs/<host>.yaml <the same url>
```

A recording is checked in and replayed offline on every pull request. It cannot be made from a
spec that does not already pass, since that would bake the failure into the suite.

**Read the chapter titles before believing the count.** A spec that reports 400 chapters has
often picked up a navigation menu or a "latest chapters" sidebar alongside the real list. A
spec that reports 12 on a long novel has usually found one page of a paginated table of
contents. Both look like success.

**Read one chapter body.** Empty chapters, or chapters full of advertising and translator
notes, are the usual failure and they pass every automated check.

## Getting the chapter list right

This is where most broken sources go wrong, and the count always looks plausible.

**Too many chapters** means the selector also matched navigation links, a site menu, or a "latest
chapters" panel that shares the real list's class. Rather than hunting for a perfect selector, filter
the rows: a chapter with no `url` is dropped, so narrowing the `url` field narrows the list.

```yaml
items:
  css: 'a[href*="/chapter/"]'
  fields:
    url:
      attr: href
      pipe: [{ regex: { pattern: '.*/chapter/\d+' } }]
```

Anything that fails the pattern yields no url and disappears. `reject` does the inverse when it is
easier to say what you do not want.

**Too few chapters** usually means the list is paginated and you only read page one.

**Wrong order** is common, and guessing is worse than measuring. If each row carries a chapter
number, order by it with `sort_by` and the result is right whichever way the site rendered it.
`reverse` is for sites that are simply newest-first with nothing to sort on.

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
guess degrades instead of breaking. Selectors in `fallback` are inherited by prepending, so a
child adds its own without losing what the base knew.

When a spec extends something, read what it actually resolves to before hunting a bug:

```bash
sourcelib resolve specs/<host>.yaml
```

## When a site dies

Move the spec to `disabled/` and add a reason:

```yaml
disabled: "Domain expired"
```

Do not delete it. If the site comes back, or comes back rebuilt, the parser and the history
are still there. A site that has been redesigned is a parser fix, not a disabled source.

## Before you write a hook

Most things that look like they need code do not. Check these first:

| You want to | Use |
|---|---|
| Read data out of a `<script>` | `css` to select the script, `json` to read into it |
| Find an element with no class, by its text | `:-soup-contains("...")` |
| Get markup that arrived inside a JSON field | the `parse_html` step |
| Drop rows you do not want | narrow a required field, or `reject` |
| Learn a page count from a pager | `all: true`, a `regex`, then `max` |
| Read a page count from a response header | `header` |
| Post a form full of hidden inputs or a token | `form` to harvest it, `payload` for your own values |
| Reuse a token across every request | a `vars` entry with its own request, cached for the session |
| Handle a chapter split across pages | `paginate` on the chapter request |

If none of them fit, say so in the pull request. A gap that five or more sites share belongs in the
format rather than in five hooks.

## When data really cannot describe it

Some sites need real code: encrypted chapter bodies, a signature scheme, a state blob that is
JavaScript rather than JSON.

| Where | For |
|---|---|
| `hooks/sites/<host>.py` | Hooks for one host. Put all of that host's hooks in this one file. |
| `hooks/shared/<name>.py` | A hook serving several hosts, including a whole template family. |
| `hooks/lib/<name>.py` | Helpers. Imported by hooks, never referenced by a spec. |

Name each function after the hook point it serves, since the spec binds by that name:

```yaml
hooks: hooks/sites/example.com.py       # binds every hook point the file defines
```

A hook may import from `lib/` and `shared/`, which is where shared setup belongs. It must not import
from another host's file in `sites/`.

Check whether a suitable hook already exists before writing one. And prefer the table above this
section: most things that look like they need code do not.

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
