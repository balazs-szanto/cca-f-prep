"""
WHAT      Regenerates docs/lessons.md into memory and compares it against the
          copy on disk. Exits non-zero on any difference, printing the first
          few differing lines so you can see what drifted.
WHY       lessons.md is generated from the LESSON block of every demo, and
          regenerating it is a step a human has to remember after editing one.
          On 2026-08-20 that step was forgotten: prose that had been restored to
          a LESSON was never mirrored into the generated file, and a commit went
          to a public remote carrying a docs page that disagreed with its own
          source. Nobody noticed until an unrelated check happened to run the
          generator. This script is the third in this repo written because
          remembering was not enough.
DOMAIN    D3 Claude Code Configuration and Workflows
TRADEOFF  It imports playground.run to reach DEMOS, so it costs an import that
          the other two checks avoid - and importing run.py is safe only because
          run.py itself is careful never to import a demo. If that ever stops
          being true this script starts making model calls, which is a sharp
          edge worth knowing about rather than a theoretical one.
ALTERNATIVE  A pre-commit hook that regenerates and stages the file, so drift is
          impossible rather than merely detected. Better in a team repo. Worse
          here, because silently rewriting a tracked file during a commit hides
          exactly the event this repo wants a reader to see.

No model call. Pure text comparison.

    uv run python scripts/check_lessons_fresh.py

Exit 0 when the file matches what the generator would produce. Exit 1 otherwise,
or if the file is missing.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LESSONS = ROOT / "docs" / "lessons.md"
# WHY: added to sys.path rather than relying on an editable install. This script
# has to run in a bare clone before `uv sync`, which is exactly when someone is
# most likely to be checking whether the tree is self-consistent.
sys.path.insert(0, str(ROOT / "src"))


def normalise(text: str) -> list[str]:
    """Split into lines, discarding the line-ending convention.

    WHY: the generator writes with the platform's newline and git may rewrite it
    again on checkout, so a byte comparison reports a difference on Windows for
    a file nobody touched. Comparing line lists comes at the price of not
    detecting a deliberate line-ending change, which is not a thing this repo
    cares about and is a thing .gitattributes would own if it did.
    """
    return text.replace("\r\n", "\n").split("\n")


def main() -> int:
    if not LESSONS.exists():
        print(f"missing {LESSONS}", file=sys.stderr)
        print("  Run: uv run python -m playground.lessons", file=sys.stderr)
        return 1

    from playground import lessons
    from playground.run import DEMOS

    expected = normalise(lessons.render(DEMOS))
    actual = normalise(LESSONS.read_text(encoding="utf-8"))

    if expected == actual:
        print(f"clean: docs/lessons.md matches its {len(DEMOS)} LESSON blocks.")
        return 0

    # WHY: report the differing lines, not just the fact of a difference. A bare
    # "files differ" sends you to a diff tool to find out whether you forgot to
    # regenerate or whether someone hand-edited a generated file, and those two
    # have opposite fixes.
    print("STALE: docs/lessons.md does not match the LESSON blocks it is "
          "generated from.\n")
    shown = 0
    for index in range(max(len(expected), len(actual))):
        want = expected[index] if index < len(expected) else "(end of file)"
        have = actual[index] if index < len(actual) else "(end of file)"
        if want == have:
            continue
        shown += 1
        if shown > 3:
            print("  ... further differences suppressed.")
            break
        # WHY: a window centred on the first differing CHARACTER, not the first
        # 120 characters of the line. These lines are long and a LESSON edit is
        # usually deep inside one, so head-truncating printed two identical
        # prefixes and called it a diff. That was the first version of this
        # block, and it failed on the exact drift the script was written for.
        at = next((c for c, (w, h) in enumerate(zip(want, have)) if w != h),
                  min(len(want), len(have)))
        start = max(0, at - 30)
        lead = "..." if start else ""
        print(f"  line {index + 1}, first difference at character {at + 1}:")
        print(f"    on disk:   {lead}{have[start:at + 90]}")
        print(f"    generator: {lead}{want[start:at + 90]}")

    print("\n  Either a LESSON block was edited and the file was not")
    print("  regenerated, or the generated file was edited by hand. The fix for")
    print("  the first is the command below; the fix for the second is to make")
    print("  the change in the demo module instead, because this file is")
    print("  overwritten wholesale and any hand edit is lost on the next run.")
    print("\n      uv run python -m playground.lessons")
    return 1


if __name__ == "__main__":
    sys.exit(main())
