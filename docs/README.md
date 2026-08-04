# Documentation

| File                                                   | What it is                                            |
| ------------------------------------------------------ | ----------------------------------------------------- |
| [0001-source-definition.md](0001-source-definition.md) | The normative definition of the source format.        |

The format spec is what `sourcelib`, this repository's CI, the web editor and the published JSON Schema are
all written against. Where it and an implementation disagree, one of them is wrong; they are never both
right.

Numbered because a later grammar arrives as a new document rather than as edits to this one. The `spec` field
in every source definition exists so both can be live at the same time.
