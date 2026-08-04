# Documentation

Guides for writing and fixing sources. Start at the top.

| File                                     | What it is                                                     |
| ---------------------------------------- | -------------------------------------------------------------- |
| [adding-a-source.md](adding-a-source.md) | Writing one from scratch, from a URL to a merged pull request.  |
| [patterns.md](patterns.md)               | The shapes real sites come in, with a spec for each.            |
| [troubleshooting.md](troubleshooting.md) | What a failure means and where to look next.                   |

**The format itself is defined elsewhere.**
[RFC-0001](https://github.com/lncrawl/sourcelib/blob/main/docs/0001-source-definition.md) is
normative: every field, every default, the evaluation order, the transform registry and the hook
contract. It lives with the interpreter because one grammar version covers the model, the step
registry and the hook points together, and all three are implemented there.

These pages are the shorter path. Where one of them and the RFC disagree, the RFC is right and the
page is the bug.
