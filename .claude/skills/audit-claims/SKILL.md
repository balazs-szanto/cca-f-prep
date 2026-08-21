---
name: audit-claims
description: >-
  Sweep one file or directory for claims about Claude's behaviour and report
  every one that carries no evidential label. Use when reviewing a demo before
  it ships, or when a docstring asserts something the run may not support.
argument-hint: "<path> — a file or directory under src/ or docs/"
context: fork
allowed-tools: Read, Grep, Glob
---

# Audit the evidential labels in $1

This repo's central convention is that **every claim about Claude's behaviour
carries its evidential state in place**: `DOCUMENTED` (official docs, with URL
and fetch date), `MEASURED` (run here, with the output), `INFERRED` (a guess), or
`SCRIPTED` (consumed a fabricated response — `src/examlab/` only). A claim with
no label is the defect this skill looks for.

Read `$1`. If it is a directory, read every `.py` and `.md` file in it.

For each file, report:

1. **Unlabelled behavioural claims.** A sentence asserting what Claude, the CLI,
   the SDK or the API *does*, with no label in the same paragraph. Quote the line
   and say which label you think it should carry, and why. Be strict about the
   direction: if you cannot tell whether it was measured, that is itself the
   finding.
2. **Labels that outrun their evidence.** `MEASURED` with no output quoted
   anywhere near it. `DOCUMENTED` with no URL or no fetch date. `SCRIPTED` used
   in a file outside `src/examlab/`, which is a category error.
3. **Numbers with no provenance.** Any figure — token counts, ratios, timings —
   that is not traceable to a run recorded in `docs/status.md` or to a cited
   page. Absolute currency figures are forbidden outright; report any you find.
4. **Claims the repo elsewhere contradicts.** If a statement disagrees with
   `docs/status.md`, `docs/tool-surface.md` or `docs/traps.md`, say so and name
   both sides. Do not decide which is right — a conflict this repo has not
   resolved must be left standing and reported as unresolved.

Then give a one-line verdict: how many unlabelled claims, and whether you would
let the file ship.

Do not edit anything. Do not run any demo. Do not make a model call beyond your
own reasoning — this is a reading exercise, and `allowed-tools` above enforces
that rather than trusting this paragraph to.

## Why this skill has the frontmatter it has

- **`context: fork`** — the audit reads whole files and quotes lines back, which
  is exactly the verbose exploratory output that should not accumulate in the
  main conversation. The finding is a short list; the reading that produced it is
  not, and the main session only needs the first.
- **`allowed-tools: Read, Grep, Glob`** — an auditor that can write is an
  auditor that can quietly fix what it found, and a convention audit whose
  findings disappear into edits teaches nobody. The restriction is the point.
- **`argument-hint`** — invoked bare, the useful question is "audit what?", and
  the hint asks it before the skill starts guessing.
