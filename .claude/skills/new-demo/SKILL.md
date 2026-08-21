---
name: new-demo
description: >-
  Scaffold a new demo module with the docstring shape, a LESSON block and its
  registry entry, so a new file starts compliant instead of being corrected
  afterwards. Use when adding a demo to src/playground/ or src/examlab/.
argument-hint: "<package>.<module> — e.g. examlab.tool_search or reliability.backoff"
context: fork
allowed-tools: Read, Write, Edit
---

# Scaffold the demo $1

Create the module and register it. Do not implement the demo's substance — the
argument it makes is the author's job, and a scaffold that guesses at it produces
a file whose docstring describes something the code does not do.

Steps, in order:

1. Read `CLAUDE.md` at the repo root for the docstring shape and the line cap,
   and the nested `CLAUDE.md` in the target package for its local rules. Do not
   restate them into the new file; follow them.
2. Read one existing sibling in the same package as the model to copy. For
   `src/examlab/` read `tool_errors.py`; for `src/playground/` read
   `reliability/error_taxonomy.py`. Both are close to the median in length.
3. Write the module with a full `WHAT / WHY / DOMAIN / TRADEOFF / ALTERNATIVE`
   docstring and a `LESSON` dict carrying `domain`, `setup`, `run`, `cost`,
   `expect` and `learn`. Every value must be a **literal** — `playground/lessons.py`
   parses these with `ast` and skips anything computed, so an f-string here
   silently removes the demo from `docs/lessons.md`.
4. `DOMAIN` uses the official CCA-F numbering and names the task statement.
   Check `docs/domain-map.md` — do not infer the number from a filename.
5. Add the registry entry to `DEMOS` in `src/playground/run.py`, in reading
   order, not alphabetically. Below the `BOUNDARY` key if it is an `examlab`
   module. An unregistered module is invisible to `--list` and absent from
   `docs/lessons.md`.
6. Leave `TRADEOFF` explicitly marked as unwritten if the demo has not been run,
   rather than asserting a cost nobody has measured. That marker is easier to
   find later than a plausible sentence.

Then print what still has to be done by hand: the demo body, one run, a
`docs/status.md` row, and `uv run python -m playground.lessons` to regenerate.

## Why this skill has the frontmatter it has

- **`allowed-tools: Read, Write, Edit`** — no `Bash`. A scaffolder has no
  business running anything, and this is the "limit to file operations to prevent
  destructive actions" case: it can create a file and amend a registry, and it
  cannot delete, move or execute.
- **`context: fork`** — step 2 reads a whole sibling module for its shape, which
  is several hundred lines the main conversation does not need afterwards.
- **`argument-hint`** — the dotted name is the one thing this cannot infer, and
  it determines the file path, the registry key and the package's local rules.
