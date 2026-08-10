# AGENTS.md

Guidance for agents working in this repo: the **source definitions** for
[Lightnovel Crawler](https://github.com/lncrawl/lightnovel-crawler). One YAML document per website,
describing where the title is, how to find the chapter list, and which element holds the text.

This repository is **data**. It contains no application, and the only Python in it is hooks and CI
scripts. That is the point: a definition can be validated, diffed and form-edited, and tested without
being executed, so authoring needs no sandbox and no privileged account.

The format is defined elsewhere.
[RFC-0001](https://github.com/lncrawl/sourcelib/blob/main/docs/0001-source-definition.md) is
normative and lives with the interpreter, because one grammar version covers the model, the step
registry and the hook points together and all three are implemented there. Read it when the answer
has to be exact; [docs/](docs/) is the shorter path for getting a source written.

## Skills

Deep, task-scoped knowledge lives in `.claude/skills/`. **Read the matching skill before starting
work in its area.**

| Skill         | Use when                                                                |
| ------------- | ----------------------------------------------------------------------- |
| `add-source`  | Writing or fixing one host's spec                                       |
| `add-base`    | Converting a shared template family into a base that many specs extend  |
| `write-hook`  | A site that cannot be described as data                                 |

## Commands

Toolchain: [uv](https://docs.astral.sh/uv/). [pyproject.toml](pyproject.toml) owns the task list, the
lint rules and the Python floor; `uv run poe` prints every task with what it does.

```bash
uv sync
uv run poe all       # every gate a pull request has to pass
uv run poe explain <url>
uv run poe try specs/<host>.yaml <novel-url>
uv run poe record specs/<host>.yaml <novel-url>
.venv/bin/sourcelib try-search specs/<host>.yaml "<a title the host carries>"
```

**`try-search` is the only thing that tests a `search` stage**, and nothing else does: `try` skips it,
a fixture does not record it, and a search that finds nothing is not an error a site reports. A
renamed form field answers `200` with the empty results page, so the stage returns zero rows and the
spec still passes every gate. Run it when you touch a `search` stage, and run it on the children when
you touch one in a base — the same family can disagree, and freewebnovel's does.

`poe all` is what CI runs, so there is no gate here that cannot be reproduced before pushing.

## The interpreter version is pinned, and the pin is in the schema

`x-generator` inside [schema/source.v1.json](schema/source.v1.json) names the interpreter version CI
installs. That is deliberate: an unpinned install would let an interpreter release fail a pull request
that touched neither the spec nor the interpreter. `uv run poe pin` reports a local mismatch.

A fix you need from the interpreter is still testable before it ships: `poe link ../sourcelib` puts a
sibling checkout in the environment. **Then run the CLI as `.venv/bin/sourcelib`, not through `uv run`
or `poe`**, both of which sync first and reinstall the pinned version over the link without saying so —
the flag you just added comes back as `unrecognized arguments`.

What cannot be short-circuited is the pin itself. Only a release lets CI and everyone else have the
fix, so the sequence stays: release it there, then bump the pin here and re-record any affected
fixture. A recording made under a different interpreter will not replay, and nothing can make one
fixture satisfy both.

## Layout

| Path                    | What it holds                                                       |
| ----------------------- | ------------------------------------------------------------------- |
| `specs/<host>.yaml`     | One concrete source per host. Flat, the filename is the address.     |
| `base/<name>.yaml`      | Abstract specs, extended by others. Never served on their own.       |
| `disabled/<host>.yaml`  | Preserved but not registered, each carrying a `disabled:` reason.    |
| `hooks/`                | The escape hatch. `shared/` serves many hosts, `sites/` serves one.  |
| `fixtures/<host>/`      | Recorded pages, replayed offline in CI.                             |
| `schema/source.v1.json` | Generated from the interpreter's model. The one committed artifact.  |
| `docs/`                 | Author-facing guides.                                               |
| `docs/drafts/`          | Untracked paper conversions. Read them; never trust them.           |

## Invariants that break silently

- **A spec is not done when it validates. It is done when it runs.** Validation checks shape.
  Only `try` against a live host tells you a selector matched the right thing, and only a recorded
  fixture keeps it that way. Never mark a base complete on a document that has never been run.
- **Read the `try` output, not the exit code.** Three failures report success: a chapter list short by
  exactly one page when the site's paging does not start where `{page}` does, a body that is mostly
  advertising, and a title that is the site's own name because the selector missed and the metadata
  fallback covered for it. See [docs/troubleshooting.md](docs/troubleshooting.md).
- **Overriding an inherited mapping key means deleting it, not adding beside it.** Mappings merge, so
  supplying a second pagination condition leaves both and validation refuses it, naming the child
  rather than the base. Write an explicit `null`.
- **The filename is the normalised host and `base_url` must agree.** Lowercase, no scheme, no `www.`,
  no port. CI checks the agreement, and that check is what stops identity drifting.
- **Abstract means no `base_url`, and nothing else.** The folder is a convention CI enforces on top of
  that, never a second definition that could disagree.
- **`extends` may not point into `disabled/`.** Disabling a spec with dependents has to break the
  build loudly rather than silently orphan its mirrors.
- **Nothing generated is committed** except the schema, which editors need in-tree.
- **A dead host is a claim, not an observation.** A parked domain, a challenge page and an ISP block
  page all answer `200` with a plausible document. Check the byte count and the redirect target, and
  check from a second network before moving anything to `disabled/`. A host wrongly disabled is worse
  than one left alone, because the reason travels with the file and the next person believes it.
- **Disabling is a move, not a delete.** `git mv` into `disabled/` and add the reason. The work is
  preserved and reviving it is the reverse.

## Conventions

- **ruff**, configured in [pyproject.toml](pyproject.toml). Markdown is excluded from the formatter,
  because it rewrites column-aligned code blocks inside prose.
- **A comment in a spec earns its place by recording a *why* the YAML cannot show**: the site
  behaviour that forced an odd selector, the endpoint that answers `200` with nothing, the theme's
  stray element. Not a restatement of the selector.
- **One host per pull request**, and paste the `try` output. A reviewer cannot tell a working spec
  from a plausible one without it.
- Prose reads like a person wrote it. Sparing em-dashes; prefer a full stop, a colon or a comma.

## Commits

- **Never commit or push automatically.** When work is done, pause and draft a commit message for the
  user. Only run `git commit` when asked in that moment; prior approval does not carry over.
- **No AI attribution trailers.**
- Imperative subject, no type prefix. The reasoning belongs in the reply or the spec comment, not in
  git history.
