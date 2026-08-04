# Patterns

The shapes real sites come in. Find yours here before writing a spec from scratch: most sites are
one of a dozen themes, and a matching `extends` is three lines instead of forty.

Every example below is taken from a base in this repository that has been run against a live host.

## Identifying the shape

`uv run poe explain <url>` answers most of it:

| The digest says                             | The site probably is           | Start from                    |
| ------------------------------------------- | ------------------------------ | ----------------------------- |
| a repeated `li.wp-manga-chapter`            | the Madara WordPress theme     | `base/wordpress.yaml`         |
| the same, and the body is images            | Madara, manga variant          | `base/wordpress-manga.yaml`   |
| no repeated structure, and a data script     | a JSON shell                   | `json:` rather than selectors |
| the chapter list may be built by scripts     | the list is a second request   | `toc.request.from`            |
| `/category/<slug>/` in the novel URL         | a novel-is-a-category WordPress | `base/wpcategory.yaml`        |
| `/search/label/<name>` in the novel URL      | a Blogger site                 | `base/blogger.yaml`           |

## The chapter list is not on the novel page

The single most common reason a source needs more than selectors. Give `toc.request` a list of
alternatives and the interpreter takes the first that produces rows, so one base can serve
installations that differ:

```yaml
toc:
  request:
    from:
      - page: novel # free: the document is already in hand
      - post: "{novel_url}/ajax/chapters/"
      - post: "{origin}/wp-admin/admin-ajax.php"
        payload:
          action: manga_get_chapters
          manga: "{vars.manga_id}"
```

Order matters twice over. `page: novel` costs no request, so it belongs first when the list is
sometimes inline. And an alternative that answers `200` with an empty body **loses** to the next one:
reachability alone is not enough, or a dead endpoint would shadow a working page.

## The list is paged

Three ways to say when to stop, and the right one is whichever the site tells you.

The site reports how many pages there are:

```yaml
paginate:
  count: { css: ".pagination a:last-child", pipe: [{ regex: { pattern: "page-(\\d+)" } }] }
  url: "{novel_url}/chapters/page-{page}"
  concurrent: true
```

The count can come from a **response header**, which is how a REST feed usually says it:

```yaml
paginate:
  count: { header: X-WP-TotalPages }
  url: "{origin}/wp-json/wp/v2/posts?categories={vars.category_id}&page={page}"
```

There is a next link, and no count anywhere:

```yaml
paginate:
  next: { css: "a.next-page", attr: href }
```

Or nothing says, and you walk until a page has no rows:

```yaml
paginate:
  while: has_items
  url: "{novel_url}/chapters?page={page}"
```

Prefer `count` over `while` when the site offers it. Stopping at the first empty page turns a
temporary blank into a truncated novel, and nothing in the output says so.

### `{page}` counts from 2, and some sites do not

`count` and `while` assume the stage's own request *was* page 1, so the pages they fetch are
numbered from 2. A site whose paging is zero-based, or is an item offset rather than a page number,
does not line up with that, and nothing in the format can shift it: there is no arithmetic in a
template.

This is worth recognising because it fails **silently and while reporting success**. Measured on one
`novelmtl` host, whose novel page is page `0` and whose pager links start at `page=1`:

| Pagination | Chapters | Verdict |
| ---------- | -------- | ------- |
| `next`     | 1333     | PASSED  |
| `count`    | 1233     | PASSED  |

The count itself was right. `count` read the last-page link and got 13, then fetched pages 2 to 13
and never fetched page 1, losing exactly one page of chapters. A trial cannot catch that: every field
produced something and the chapter list looked plausible.

So when a site's own numbering does not start where `{page}` does, use `next` if the theme offers a
next link, and a `toc.items` hook if it does not. Check the arithmetic before trusting `count`: open
the second page and see what the site calls it.

### Overriding a base's pagination

`paginate` is a mapping, so a child's keys **merge** into the base's rather than replacing them.
Supplying a different termination condition therefore leaves two in the resolved spec, and validation
refuses it:

```
toc.request.paginate
  Value error, only one of while, count, next may be set, got ['count', 'next']
```

The error names the child, not the base it inherited from, which is confusing the first time. Delete
the inherited key explicitly:

```yaml
toc:
  request:
    paginate:
      next: null # the base sets this; this spec pages by count instead
      count: { css: ".pager a:last-child" }
      url: "{novel_url}?page={page}"
```

An explicit `null` deletes an inherited key anywhere, not just here. It is the tool for every case
where a base declares something a child needs gone rather than changed.

## The data is JSON, not HTML

A growing share of sites are API shells. Selectors are the wrong tool; use a dotted path. `$` is the
whole body, which is how a bare top-level array is read:

```yaml
toc:
  request:
    get: "{origin}/api/book/{vars.book_id}/chapters"
  items:
    json: "$"
    fields:
      title: { json: "title.rendered", pipe: [parse_html, text, trim] }
      url: { json: link }
```

Two things that catch people. JSON strings often carry HTML entities, and `parse_html` then `text`
decodes them. And when a JSON field holds a rendered HTML fragment, put `json:` and `css:` on the
same item list: the path picks the fragment and the selector runs inside it.

```yaml
search:
  request:
    post: "{origin}/lnsearchlive"
    payload: { inputContent: "{query}" }
  json: resultview # a fragment inside the response
  css: ".novel-list .novel-item a" # selected within it
```

## The request needs a value from somewhere else

`vars` reads a value once and makes it available to every template. Where it reads from is
declared, because the corpus needs three different origins.

From the novel URL itself, with no document involved:

```yaml
vars:
  slug: { on: url, regex: "/category/([^/?#]+)" }
```

From the novel page:

```yaml
vars:
  manga_id: { on: novel, css: "#manga-chapters-holder[data-id]", attr: data-id }
```

From a request of its own, fetched once and reused. This is how a one-time token works:

```yaml
vars:
  verify_token:
    on: { get: "{origin}/search" }
    css: '#novelSearchForm input[name="__LNRequestVerifyToken"]'
    attr: value
```

## Volumes

Select the headings and the chapters separately. Assignment is positional in document order: a
heading partitions the chapters that follow it, which is the shape real sites use.

```yaml
toc:
  items:
    css: "li.chapter"
    fields:
      title: { css: a }
      url: { css: a, attr: href }
  volumes:
    css: "li.volume-heading"
    fields:
      title: {}
```

With no `volumes`, chapters are grouped by `chapters_per_volume`.

## A manga body

Pages arrive lazily, with the real address in `data-src` and a placeholder in `src`:

```yaml
chapter:
  body:
    css: div.reading-content
    pipe:
      - strip_css: [input] # the theme leaves a hidden input in the reader
      - unlazy_images
      - keep_attrs: [src, alt]
```

`unlazy_images` also trims the address, which matters more than it sounds: several themes emit
`src=" https://…"` with a leading space.

## A body with junk in it

Reach for the narrowest step that removes it. `strip_css` deletes matched elements, `unwrap` removes
a tag and keeps its contents, and `drop_leading` removes a duplicated chapter heading:

```yaml
chapter:
  body:
    css: "#content"
    pipe:
      - strip_css: [".ads", ".share-buttons"]
      - drop_leading: { matches: '(?i)^\s*chapter\s+\d+', within: 5 }
      - unwrap: [div]
      - paragraphs
```

Note what a *filter* does. `regex` and `reject` yield **nothing** when they do not match, so a field
whose pipe ends in one disappears rather than passing through. That is deliberate, and it is how a
loose selector gets narrowed. It is also how a careless pipe silently deletes data, so check the
`try` output rather than the exit code.

## A site that is one of many names

An alias is two meaningful lines, extending the concrete spec rather than a base:

```yaml
spec: 1
extends: specs/bato.to.yaml
base_url: https://mangatoto.net/
```

Extending a live sibling couples them: a bad selector in the parent breaks every mirror at once.
That is usually the right trade, because they are the same application, but it is worth knowing.

## The search endpoint is broken but the rest works

Turn the capability off and keep the configuration, so it can come back without being rewritten:

```yaml
can_search: false
```

You can force a capability off. You cannot claim one that does not resolve, and CI rejects it.
