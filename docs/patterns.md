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
  last: { css: ".pagination a:last-child", pipe: [{ regex: { pattern: "page-(\\d+)" } }] }
  url: "{novel_url}/chapters/page-{page}"
```

Those pages are fetched in parallel without asking. `concurrent` is on by default wherever the
condition allows it, and the host's pace still applies: it is enforced per origin, so parallelism
decides how many requests wait on that budget rather than how large it is. Set `concurrent: false` to
force one at a time.

The last page can come from a **response header**, which is how a REST feed usually says it:

```yaml
paginate:
  last: { header: X-WP-TotalPages }
  url: "{origin}/wp-json/wp/v2/posts?categories={vars.category_id}&page={page}"
```

There is a next link, and nothing saying where the list ends:

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

Prefer `last` over `while` when the site offers it. Stopping at the first empty page turns a
temporary blank into a truncated novel, and nothing in the output says so.

### The site counts items, not pages

A feed addressed by the index of its first row rather than by a page number sets `step` to the page
size. `{page}` then counts rows:

```yaml
paginate:
  first: 1
  step: 100
  while: has_items
  url: "{origin}/feeds/posts/summary?alt=atom&max-results=100&start-index={page}"
```

**Pick a page size the host actually honours.** If it returns fewer rows than asked, the stride and the
rows returned disagree and the walk skips the difference silently. Blogger does not honour
`max-results` at all, and the shortfall varies by blog and by offset: asking 100 returned 25, then 17,
then 36 on one blog, 70, then 67, then 77 on another, and the full 100 on a third. Asking 25 came back
whole everywhere it was measured. Count the rows at several offsets before trusting a stride, and take
the size that arrives complete over the size that would be fewer requests.

### The cheap path first, a browser only if it fails

`render` runs every request for that stage in a browser, which is slow and needs one installed. Where
a host *usually* answers a plain fetch and only sometimes challenges, ask for both and let `from`
choose: alternatives are tried until one yields rows, so a challenge page — which yields none — loses
to the rendered attempt behind it.

```yaml
novel:
  request:
    from:
      - get: "{novel_url}" # tried first, costs nothing
      - get: "{novel_url}" # only reached when the first yields nothing
        render: true
        wait_for: ".wp-manga-chapter"
```

The day the host stops challenging, the browser stops being used, with no edit to the spec. Prefer
this to a bare `render: true` unless the markup is *never* in the served page, as with a list that
scripts build from an API.

### Say what the site numbers its pages from

`first` and `last` are the numbers the **site** puts on its own pages, not a count of them. The stage's
own request already produced `first`, so the walk covers the pages after it. `first` defaults to 1, and
a site numbering from zero says so:

```yaml
paginate:
  first: 0 # the novel page is page 0 here, so the next one is 1
  last: { css: ".pagination a[href]", attr: href, all: true, pipe: [{ regex: { pattern: "page=(\\d+)" } }, max] }
  url: "{origin}/ajax?page={page}"
```

Either may be a literal or read from the page, and where an extractor finds several numbers the largest
wins, because a pager lists the pages it can reach.

**When the pager says how long it is only by how long it is**, `count` reads that. Several themes
render one `<option>` per page and give every one the same `value`, so no number can be selected out
of the markup and the total is the number of options:

```yaml
paginate:
  last: { css: "#indexselect option", all: true, pipe: [count] }
  url: "{novel_url}?page={page}"
```

It is worth reaching for, because the alternative is `while`, and `while` walks speculatively where
`last` fetches at the full width the rate limit allows. The `freewebnovel` family walked that way and
a single `try` on a long novel ran past ten minutes.

A site that addresses a page by the **index of its first item** rather than by a page number sets
`step` to the page size, as above. Two shapes still need a hook: a start-and-end range over a known
total, and a feed that answers with fewer rows than asked, where the next offset is a number only the
response knows.

**Get `first` wrong and it fails while reporting success.** Before it existed, one `novelmtl` host whose
novel page is page `0` gave:

| Pagination | Chapters | Verdict |
| ---------- | -------- | ------- |
| `next`     | 1333     | PASSED  |
| `last`     | 1233     | PASSED  |

The last page was right. It read 13 from the pager, then walked 2 to 13 and never fetched page 1,
losing exactly that page of chapters while every field still produced something. With `first: 0` the
same spec reads all 1333.

So open the site's second page and see what it calls itself. `next` remains the answer only where a site
publishes nothing about where its list ends.

### Overriding a base's pagination

`paginate` is a mapping, so a child's keys **merge** into the base's rather than replacing them.
Supplying a different termination condition therefore leaves two in the resolved spec, and validation
refuses it:

```
toc.request.paginate
  Value error, only one of while, last, next may be set, got ['last', 'next']
```

The error names the child, not the base it inherited from, which is confusing the first time. Delete
the inherited key explicitly:

```yaml
toc:
  request:
    paginate:
      next: null # the base sets this; this spec pages by last instead
      last: { css: ".pager a:last-child" }
      url: "{novel_url}?page={page}"
```

An explicit `null` deletes an inherited key anywhere, not just here. It is the tool for every case
where a base declares something a child needs gone rather than changed.

## The page is an app shell and the list is nowhere in it

`explain` shows an empty document and no selector finds a chapter. Before reaching for `render: true`,
which is slow and has to run for every chapter, look for where the data actually comes from. Four
places, cheapest first.

**The page already carries it.** A Next.js or Nuxt page hydrates from a payload embedded in its own
markup, so the record is usually there before any request is made. Look for `script#__NEXT_DATA__`
and read it with a dotted path — `wuxia.click` keeps its whole novel under
`props.pageProps.dehydratedState.queries.0.state.data`, so its spec needs no second request at all.
`ItemList.script` reads rows out of such an element when the list is in there too.

**The site calls an API you can call.** Watch the network while the page loads rather than reading the
DOM afterwards. A public read endpoint is common, and then the spec is ordinary: a `get` for the
record and another for the body, with `vars` carrying the slug out of the URL. `konkon.ink` answers
`api-k.<host>/api/public/novels/<slug>` with the record, the chapter list and, from a second route,
the text.

**The call happens on a click.** A capture that loads the page and waits sees nothing, because the
list arrives when a tab is opened. `wuxia.city` and `webfic.com` look identical to a dead site under a
load-only capture. Either drive the interaction or accept the host as deferred, but do not record
"no XHR" as "no API".

**It is a form POST behind a token.** WordPress sites often answer on `admin-ajax.php` with a nonce
minted per page. Both halves are declarable — a `var` reads the token out of the inline script, another
reads the post id from the page's shortlink, and the request is a `post` with a `payload`. Only an
answer that is neither markup nor JSON needs a hook; `creativenovels.com` is the corpus's example.

Three things to check before counting such a host converted:

- **Read the payload's own fields.** `konkon.ink` described itself perfectly and its spec worked, and
  then the API reported `is_locked` with empty content on 47 of its 48 chapters. A site that says it is
  paywalled is telling you something a chapter sample of one would miss.
- **Check the totals the API gives you.** A response carrying `chapters_pagination.total` lets you
  prove the rows you read are all of them, which no selector-based list can do.
- **A `json` path has no wildcard.** `tags` and `genres` usually arrive as lists of objects, and a stage
  field cannot map one key across them, so those stay empty even though the payload holds them.

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

### Junk that only its wording identifies

A translator's note, a watermark and a "read this at ..." line sit in ordinary markup, so no selector
finds them. `strip_matching` removes an element by what it says:

```yaml
pipe:
  - strip_matching: { pattern: '^\s*(Translator|Editor):' }
  - strip_matching: { pattern: "Bookmark this website", tags: [p, strong] }
  - clean_body
```

It considers only elements with no children of their own unless `tags` names some. That is not a
detail: every ancestor of a match contains the matching text too, so an unrestricted search would
find the body itself and delete the chapter while every field still reported `ok`.

### Adding a step to a base's pipe

A declared `pipe` **replaces** the default rather than extending it, so a child wanting one more step
would have to respell the whole list, and would then stop tracking the base when it changed.
Reference the base's named pipe instead. Every base with a body pipe declares it as `clean_body`:

```yaml
chapter:
  body:
    pipe:
      - strip_css: [".c-ads", ".custom-code"]
      - clean_body
```

Do not redeclare `pipes: { clean_body: ... }` in the child to do this. A mapping merges by key, so
the child's entry replaces the parent's and the name inside it then refers to itself, which is a
load-time error. Redeclare it only when you mean to replace the base's cleanup outright, as
`base/wordpress-manga.yaml` does for a body that is images.

### When `drop_leading` does nothing

It only removes a block that looks like a heading: a leaf holding a line of text, not an element with
blocks of its own and not almost all of the body. That guard exists because a theme that wraps a whole
chapter in one div opening with its title would otherwise lose the chapter, and report success. If your
heading survives, one of three things is true:

- **It is not in a block of its own.** A heading written as bare text between `<br>` tags is not an
  element, so there is nothing to remove. Nothing in the format reaches it.
- **It is behind something.** Empty ad slots count as blocks, so put `drop_empty_nodes` before it
  rather than widening `within` to however many slots this page happened to have.
- **It is a tag rather than a heading.** `strip_tags: [h1, h2, h3]` is simpler, and prose does not use
  headings. That is what the WordPress and MangaStream bases do.

Note what a *filter* does. `regex` and `reject` yield **nothing** when they do not match, so a field
whose pipe ends in one disappears rather than passing through. That is deliberate, and it is how a
loose selector gets narrowed. It is also how a careless pipe silently deletes data, so check the
`try` output rather than the exit code.

## The list has rows that are not chapters

A row is dropped when a field the stage requires resolves empty, and a loose selector narrowed by a
filter step is the usual way to use that. When the test reads a field the stage has no use for, name
it in `require`:

```yaml
items:
  json: "$"
  require: [parent, posts]
  fields:
    title: { json: name }
    url: { json: link }
    parent: { json: parent, pipe: [{ reject: { pattern: "^[1-9]" } }] }
    posts: { json: count, pipe: [{ reject: { pattern: "^0$" } }] }
```

A `reject` yields nothing when it matches, so the field resolves empty and the row goes. `require`
adds to what the stage already needs and cannot remove it: a chapter still needs a `url`.

A name in `require` that is not a declared field is a load-time error, because it would otherwise read
as a field empty on every row and drop the entire list, which looks exactly like a dead selector.

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
