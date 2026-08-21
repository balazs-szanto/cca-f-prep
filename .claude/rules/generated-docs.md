---
paths:
  - "docs/lessons.md"
  - "docs/status.md"
  - "docs/tool-surface.md"
---

# Rules for the three documents that count things

`docs/` holds hand-written argument and machine-checked accounting side by side.
These three are the accounting. A path rule reaches them and a `docs/CLAUDE.md`
could not, because it would apply equally to `traps.md` and `domain-map.md`,
where none of the below is true.

## `lessons.md` is generated. Do not edit it.

It is written by `uv run python -m playground.lessons` from the `LESSON` block at
the top of each registered demo. Edit the module, then regenerate, then run
`scripts/check_lessons_fresh.py` to confirm you did. That regeneration step was
missed once and a docs file disagreeing with its own source reached a public
remote; it was found when an unrelated command happened to run the generator,
which is not a control.

## `status.md` counts itself, and the count is checked

Two scripts guard it, and both will fail on an edit that looks harmless:

- `check_caveat_accounting.py` requires the stated counts to match the
  `(see caveat)` markers in the table, and the named demos to be exactly the
  marked ones **in both directions**. Adding a row means updating a number
  written as a word and a name list, in two places.
- `check_status_freshness.py` compares each row's date against the file's mtime.
  Editing a demo — even only its `DOMAIN` line — makes its row stale. Either
  re-run it and update the date, or mark it `(see caveat)` and name it.

The table is the evidence and the prose is the summary. When they disagree, fix
the prose, unless a row's marker is itself wrong.

## `tool-surface.md` counts things and nothing checks it

Its bucket totals are stated in three places and were wrong in all three until
2026-08-21 — while the grand total of 24 was right, which is exactly why nobody
noticed. Until a script reads this page, **re-derive the counts with `grep`
against the bucket column** rather than adjusting them by hand, and say in the
edit that you did.

## Common to all three

- A row moving toward *less* coverage is the kind of correction these pages exist
  to make. `web-fetch-tool` was demoted from OBSERVABLE to API-ONLY, and the
  built-in toolset figure was corrected upward by a quarter. Neither was hidden.
- Never quote an absolute currency figure. Ratios survive a price change.
- A number that belongs to the harness rather than to this repo's code is a
  measurement with a date, not a constant. Write the date next to it.
