"""
WHAT      The banner, the closing block and the known-issue block that every demo
          in this repo prints around its own output.
WHY       A demo that only prints results teaches whoever already knew what to
          look for. The banner states the setup and the expected output before
          anything runs, so you can compare; the closing block restates the
          lesson against the numbers that actually appeared, so the conclusion is
          attached to evidence instead of floating next to it.
DOMAIN    D3 Claude Code Configuration and Workflows
TRADEOFF  Every demo now pays about fifteen lines of ceremony, and the console
          output is roughly twice as long. On a small screen the banner can push
          the real output out of view. That is accepted because the alternative -
          a bare table of numbers - only reads correctly for the person who wrote
          it.
ALTERNATIVE  Put the framing in the docs and leave the console bare. Cheaper, and
          it splits the lesson from its evidence: the reader has to hold a
          paragraph from another file in their head while reading a number here.

Makes no model call. Every function in this file is pure printing.
"""
from __future__ import annotations

import sys
import textwrap
from typing import Mapping, NoReturn, Sequence

# WHY: a Mapping, not a TypedDict. Every demo declares LESSON as a plain dict
# literal so that lessons.py can read it back with ast.literal_eval without
# importing the module - and importing a demo module runs it. A TypedDict would
# document the keys better and would make that trick impossible.
Lesson = Mapping[str, str]

WIDTH = 78
HEAVY = "=" * WIDTH
LIGHT = "-" * WIDTH

# WHY: the keys are checked, not assumed. A demo that forgets "expect" would
# otherwise print a banner with a hole in it and nobody would notice, because a
# missing field looks like a field that was not relevant.
REQUIRED = ("domain", "setup", "run", "cost", "expect", "learn")


def _field(label: str, text: str) -> None:
    """One wrapped `label   text` row, hanging-indented under the label."""
    pad = " " * 10
    wrapped = textwrap.fill(text, width=WIDTH, initial_indent=pad, subsequent_indent=pad)
    # WHY: wrap with the indent already applied, then overwrite the first ten
    # characters with the label. Wrapping the bare text and indenting afterwards
    # gives the first line ten characters more room than the rest, which shows up
    # as a ragged left-hand column the eye reads as a mistake.
    print(f"{label:<10}" + wrapped[10:])


def _check(lesson: Lesson) -> None:
    missing = [k for k in REQUIRED if not lesson.get(k)]
    if missing:
        raise KeyError(f"LESSON is missing or has empty keys: {missing}")


def banner(lesson: Lesson) -> None:
    """Print the setup contract before the demo body runs."""
    _check(lesson)
    print(f"\n{HEAVY}")
    print(f"LESSON    {lesson['domain']}")
    print(LIGHT)
    _field("setup", lesson["setup"])
    _field("run", lesson["run"])
    _field("cost", lesson["cost"])
    _field("expect", lesson["expect"])
    print(f"{HEAVY}\n")


def closing(lesson: Lesson, observed: Sequence[str], naive: str = "") -> None:
    """Restate the lesson against what this particular run just printed.

    `observed` must be built from values the run actually produced. Hardcoding a
    sentence here that describes the usual outcome would turn this block into
    decoration, and the first time the demo behaved differently the block would
    quietly lie about it.
    """
    _check(lesson)
    print(f"\n{LIGHT}")
    print("WHAT YOU JUST SAW")
    for line in observed:
        print(textwrap.fill(line, width=WIDTH, initial_indent="  - ",
                            subsequent_indent="    "))
    # WHY: the naive expectation is printed *before* the lesson, not after. A
    # counterintuitive result only lands if the reader's own guess is named first
    # and then taken apart; stating the conclusion first invites agreement
    # without the reader ever noticing they believed something else.
    if naive:
        print()
        _field("EXPECTED", naive)
    print()
    _field("LESSON", lesson["learn"])
    print(f"{HEAVY}\n")


def known_issue(lesson: Lesson, text: str) -> NoReturn:
    """Report a demo that cannot complete here, and stop without faking a result.

    Called at the exact point the demo gives up. The same paragraph must also
    appear as a comment on that line, because a reader who never runs the file
    still has to find out why it does not finish.
    """
    _check(lesson)
    print(f"\n{HEAVY}")
    print("KNOWN ISSUE - this demo cannot complete in this environment")
    print(LIGHT)
    print(textwrap.fill(text, width=WIDTH))
    print(LIGHT)
    _field("learn", lesson["learn"])
    print("          Nothing above was simulated. The demo stops here rather than")
    print("          printing a plausible result it did not obtain.")
    print(f"{HEAVY}\n")
    # WHY: exit 0, deliberately, and it is arguable. A known issue is a
    # documented state, and a non-zero exit code makes the shell, the dispatcher
    # and any future CI treat it as a crash - which is the one reading this block
    # exists to prevent. The cost is that a script chaining demos with && will
    # walk straight past it, so the block has to be loud enough to catch a human.
    sys.exit(0)
