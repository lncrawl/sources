# lncrawl sources

Source definitions for [Lightnovel Crawler](https://github.com/lncrawl/lightnovel-crawler).

A source tells the crawler how to read one website: where the title is, how to find the
chapter list, which element holds the chapter text. Here a source is **data, not code**. One
YAML file per host, validated against a published schema, interpreted at runtime by
`sourcelib` (on PyPI as `lncrawl-sourcelib`).

That means a broken site can be fixed by editing a few selectors, in an editor with
autocomplete, without writing Python and without waiting for an app release.

## Layout

| Path                   | What lives there                                                                             |
| ---------------------- | -------------------------------------------------------------------------------------------- |
| `specs/<host>.yaml`    | One live source per host. The filename is the host.                                          |
| `disabled/<host>.yaml` | Hosts that are down, blocking, or were never implemented. Each carries a `disabled:` reason. |
| `base/<name>.yaml`     | Shared definitions other specs extend. No `base_url`, so never registered as a source.       |
| `hooks/<name>.py`      | The escape hatch. One function per file, for the rare site that cannot be described as data. |
| `fixtures/<host>/`     | Recorded pages, so a spec can be tested offline.                                             |
| `schema/`              | The JSON Schema, generated from the model. Editors read this.                                |
| `rfc/`                 | The normative format definition.                                                             |

Finding a source is always the same rule: `specs/` plus the host, lowercased, without
`www.` or a scheme.

## Add or fix a source

```bash
pip install lncrawl-sourcelib

sourcelib explain https://example.com/novel/some-book   # what the page looks like
$EDITOR specs/example.com.yaml
sourcelib try specs/example.com.yaml https://example.com/novel/some-book
```

`explain` prints a short structural summary of a page, including candidate selectors and how
many elements each one matches, which is usually enough to write the spec. `try` runs it and
reports what each field produced, or which field matched nothing and where.

Open a pull request with one host per PR. See [CONTRIBUTING.md](CONTRIBUTING.md).

## The format

[RFC-0001](rfc/0001-source-definition.md) is the normative definition: every field, the
evaluation rules, the transform steps, and the hook contract. It is what `sourcelib`, this
repo's CI, the web editor and the JSON Schema are all written against, so it is the thing to
read when the answer matters.

A minimal source is two meaningful lines, because it inherits everything else:

```yaml
spec: 1
extends: base/wordpress.yaml
base_url: https://example.com/
```

## Licence

Apache-2.0, matching the `scraper` package. See [NOTICE](NOTICE) for why the definitions here
are independent of the crawler's own GPL-3.0-or-later code.
