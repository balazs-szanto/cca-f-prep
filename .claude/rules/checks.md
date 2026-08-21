---
paths:
  - "scripts/check_*.py"
  - "scripts/prepublish_check.py"
  - ".claude/hooks/check_*.py"
---

# Rules for a check script

These apply to every verification script in this repo, wherever it lives. There
are two such directories — `scripts/` and `.claude/hooks/` — which is why this is
a path-scoped rule and not a `CLAUDE.md` in either of them: a convention that
spans directories cannot be expressed by a file that is bound to one.

## The rule that matters most

**A check must be proven to fail on a real defect before it is trusted.** Not a
hypothetical one. Introduce the defect, run the check, read its report, and only
then keep it. Every check here exists because a rule this repo states in prose
was broken by the person who wrote the prose, and two of them passed their first
run while being useless:

- `check_lessons_fresh.py` returned the right exit code and truncated both sides
  of its diff before the difference, so its report said nothing.
- `check_caveat_accounting.py` failed on its first contact with the real
  `status.md` because a filename has the same `word.word` shape as a demo name.

Record the defect you tested against in the module docstring. A check whose
docstring cannot name the failure it caught has not been tested.

## The rest

- **Exit 0 or 1, and nothing else** — except `.claude/hooks/*.py` in hook mode,
  where the harness defines the codes. Say which mode a script is in.
- **Print the fix, not just the finding.** A report that names a stale row and
  not what to do about it makes the reader open three files to find out.
- **Fail loudly when the check cannot find its input.** `check_conventions.py`
  reads the line cap out of `CLAUDE.md`; if the convention is reworded it reports
  that as a failure rather than falling back to a hardcoded number. A check that
  silently stops checking is worse than no check.
- **No model call, ever.** These run in a loop while editing. Pure filesystem,
  text and `ast`.
- **Read source with `ast`, never by importing it.** Several demos call
  `asyncio.run()` at import time, so importing one to inspect it runs it.
- **Take an optional path argument** where the check parses a document, so it can
  be pointed at a fixture and proven against it.
- **Skip `.venv`, `.git`, `__pycache__` and `node_modules` wholesale**, at the
  directory level. A check that reports third-party files buries its own findings.
- Register a new check in the README's list and in `docs/status.md`. The README
  said "the four static checks" above six commands until 2026-08-21.
