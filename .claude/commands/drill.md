---
description: Quiz me on one exam domain using only the files in this repository
---

Drill me on domain: **$1**.

Valid values are `d1`, `d2`, `d4`, `d5`, `d0`, `d3`, or `all`. Only `d1`, `d2`,
`d4` and `d5` have a `docs/dN-*.md` file; `d0` (`src/playground/basics/`, minus
`prompt_shape.py`) and `d3` (`src/playground/basics/prompt_shape.py`) exist as
demos with no domain doc, so for those read the module docstrings and `LESSON`
blocks directly. The numbering itself is unverified — see `docs/domain-map.md`
before treating any of these labels as authoritative.

Rules for this drill:

1. Read the matching `docs/dN-*.md` and the source files it points at. Use only
   what is in this repository. If the docs and the code disagree, say so - that
   disagreement is more valuable than a clean answer.
2. Ask me **one scenario question at a time**. Wait for my answer before asking
   the next. Do not print the answer with the question.
3. Score each answer as correct, partially correct, or wrong, and say which file
   and line range settles it so I can go read it.
4. Favour tradeoff questions over recall questions. "Which is faster" is a bad
   question; "you have a 40-turn agent that keeps losing early context, what do
   you change first and what does it cost you" is a good one.
5. After three questions, stop and give me a one-paragraph read on where my
   understanding is thin.
6. Claims in this repo are labelled DOCUMENTED, MEASURED or INFERRED in place.
   Do not quiz me on anything labelled INFERRED, or on either side of a conflict
   the repo says is unresolved - tell me it is unsettled instead.

Do not make model calls or run any demo during the drill. This is a reading
exercise.
