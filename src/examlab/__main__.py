"""
WHAT      A signpost. `python -m examlab` prints the command that actually runs
          these modules and exits non-zero.
WHY       This file used to hold a second registry and a second dispatcher, so
          the repo had two lists of runnable things and two `--list` commands.
          That is the failure `playground/lessons.py` names in its own WHY - two
          lists disagree eventually, and the one people trust is the wrong one -
          and it had a cost before it had a chance to drift: the modules were
          invisible to anyone who ran the documented `--list` and stopped there.
          The registry now lives in `playground/run.py` with everything else.
WHY NOT DELETE IT  Because `python -m examlab` is what someone will type, and
          `No module named examlab.__main__` teaches nothing. A wrong guess
          deserves the right command, not a stack trace.
DOMAIN    D3 Claude Code Configuration and Workflows (20%)
TRADEOFF  `playground/run.py` now indexes a package it must not import. That is
          why `lessons.module_of()` exists and why the dispatcher uses `runpy`
          and `find_spec`: both resolve a module by name without binding it, so
          the registry spans two packages and creates no import edge between
          them. The cost is one shared helper that has to know the package names.
ALTERNATIVE  Keep the second dispatcher and have `run.py --list` merely mention
          it. Rejected: that is the same two lists, with a cross-reference
          papering over them.

Exits 1, because you asked to run something and nothing ran.
"""
from __future__ import annotations

import sys

MESSAGE = """\
examlab has no dispatcher of its own. Its modules are registered in
playground/run.py alongside the Agent SDK demos, so there is one list and one
entry point:

    uv run python -m playground.run --list
    uv run python -m playground.run examlab.agentic_loop

The eight examlab entries appear after a boundary line in --list. They are the
ones whose D-numbers are the official blueprint's, and they are free and offline
by default - see src/examlab/CLAUDE.md for the auth rule that applies to them."""


def main() -> int:
    print(MESSAGE, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
