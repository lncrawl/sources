# Adding a source

A source is one YAML file describing where things are on one website. No Python, unless the site
leaves no choice, and then only a named hook.

```bash
uv sync
```

## 1. Check nobody has it

```bash
ls specs/ | grep <host>
ls disabled/ | grep <host>
```

A file in `disabled/` is a host that was deliberately turned off, and it says why. If the site is
back, the fix is to `git mv` it into `specs/` and delete the `disabled:` line, not to write a new
one.

## 2. Read the page before writing a selector

```bash
uv run poe explain https://example.com/novel/some-title
```

`explain` prints a few kilobytes describing a page that is usually several hundred: what repeats and
how many rows, which script carries the data, what metadata exists, and where the last page's number would
come from. It never offers a class that looks build-generated, because a bundler hash breaks on the
next deploy.

Two things to look for. If the digest says the chapter list may be built by scripts, the list is
probably behind a second request rather than in the page. And if it names a data script, the site is
a JSON shell and `json:` will be shorter and steadier than any selector.

## 3. Try an existing base first

Most sites are not unique. If the digest looks like one of the shapes in
[patterns.md](patterns.md), a spec is three lines:

```yaml
spec: 1
extends: base/wordpress-manga.yaml
base_url: https://example.com/
```

Run it before writing anything else. Half of new sources need nothing more, and the ones that do
usually need one field overridden rather than a whole document.

## 4. Write it

The filename is the host and nothing else: `specs/example.com.yaml`, lowercase, no scheme, no
`www.`, no port. `base_url` inside must agree, and CI checks that it does.

```yaml
spec: 1
base_url: https://example.com/
language: en

novel:
  title: { css: h1.entry-title }
  cover: { css: .cover img, attr: [data-src, src] }
  authors: { css: .author a, all: true }
  tags: { css: .genres a, all: true }
  synopsis: { css: .summary }

toc:
  request:
    page: novel
  items:
    css: ul.chapter-list li a
    fields:
      title: {}
      url: { attr: href }

chapter:
  body: { css: "#chapter-content" }
```

Only `novel.title`, `toc.items` and `chapter.body` are required. Leave a field out and the
interpreter reads the page's own metadata: OpenGraph, then JSON-LD, then the document title. A
cover, author list, tag list or synopsis that produces nothing is a warning, not a failure, because
real pages omit them.

Write `pipe:` only when the site is unusual. Every field kind already has a default: a synopsis and
a chapter body get their inline wrappers flattened and are split into paragraphs, tags get trimmed
and deduplicated. A declared pipe **replaces** the default rather than extending it, so what runs is
always visible in the file.

## 5. Run it against the live site

```bash
uv run poe try specs/example.com.yaml https://example.com/novel/some-title
```

Read the output rather than the exit code. `try` prints what every field produced and samples three
chapters, the first, the middle and the last. The two failures it cannot catch for you are a selector
that matched the wrong thing and a body that came back full of advertising. A chapter count that
looks right is not the same as a chapter list that is right.

Two flags matter while you are still iterating:

```bash
uv run poe try specs/example.com.yaml <url> --toc-pages 4   # stop after two pages of the list
uv run poe try specs/example.com.yaml <url> --sample 25      # read more bodies before believing it
```

`--toc-pages` is where the time goes. Reading the chapter list is most of a trial, and a spec that
pages with `while` or `next` reads it a window at a time, so a novel with a hundred pages of list is
a long wait before the first chapter appears. The reported chapter count is then short and says so.

`--sample` is worth raising for a final pass. Samples are spread evenly and always include the first
and last, and a theme's oddities come in runs: the last bug found this way appeared in exactly one of
three sampled chapters.

If the spec searches, run that too, because **nothing else here reaches a search stage**: a trial
takes a novel URL, a fixture records a novel crawl, and `check` only validates structure. One base's
search had never answered a single query and every gate was green.

```bash
uv run poe try-search specs/example.com.yaml "a title the host carries"
```

Read the result titles rather than the count.

When it passes, record it so CI can notice the site changing under the spec:

```bash
uv run poe record specs/example.com.yaml https://example.com/novel/some-title
```

## 6. Check what CI checks

```bash
uv run poe all
```

That is the same task list the pull request runs, so there is no gate here you cannot see first.

## 7. Open the pull request

One host per pull request, and paste the `try` output. A reviewer cannot tell a working spec from a
plausible one without it.

## When the site will not cooperate

Some sites cannot be described as data: a chapter body behind encryption, a list paged in a way
arithmetic-free templates cannot address, a refusal that has to be recognised. Those get a hook, one
Python function in `hooks/`, and that is the only escape hatch. Read
[the RFC's hook section](https://github.com/lncrawl/sourcelib/blob/main/docs/0001-source-definition.md#7-hooks)
before writing one, and check whether `hooks/shared/` already has it: a hook shared by five hosts is
better than five copies, and that duplication is exactly what the old Python sources accumulated.
