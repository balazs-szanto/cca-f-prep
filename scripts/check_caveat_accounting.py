"""
WHAT      Checks that the caveat bookkeeping in docs/status.md agrees with its
          own table: the stated count matches the number of "(see caveat)"
          markers, the named demos are exactly the marked ones, and every demo
          named anywhere in that section actually exists in the run registry.
WHY       status.md is the file this repo's credibility rests on, and its caveat
          accounting is the part that has been wrong most often. An earlier
          version said "six rows" while seven were marked and five were named -
          three numbers, no two agreeing, in the document whose whole job is
          telling you what has and has not been observed. It was found by review
          rather than by the author, and then the same section was rewritten by
          hand twice more. Prose that counts things is prose that goes stale.
DOMAIN    D3 Claude Code Configuration and Workflows
TRADEOFF  It parses two hand-written lists out of Markdown, so a rewording of
          the headings breaks the check rather than the document. That is the
          right way round - a check that silently stops finding its input is
          worse than one that fails loudly - but it does mean editing those
          headings means editing this file.
ALTERNATIVE  Generate the caveat paragraphs from the table the way lessons.md is
          generated from LESSON blocks. Removes the whole class of error, and
          costs the thing that makes those paragraphs worth reading: they
          explain WHY each row is caveated, which no generator can write.

No model call. Pure text.

    uv run python scripts/check_caveat_accounting.py [path/to/status.md]

The optional path argument exists so this can be pointed at a fixture and proven
to fail on a real defect before being trusted. That is not a hypothetical
precaution: scripts/check_lessons_fresh.py was written, run, reported the right
exit code, and its report turned out to be useless because it truncated both
sides of the diff before the difference. A check that has only ever been seen
passing has not been tested.

Exit 0 when the three assertions hold, 1 otherwise.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

# WHY: matches the table rows the same way check_status_freshness.py does, so
# the two checks cannot disagree about what counts as a row.
ROW = re.compile(
    r"^\|\s*`(?P<demo>[a-z_]+\.[a-z_]+)`\s*\|"
    r"\s*(?P<state>[^|]+?)\s*\|"
    r"\s*(?P<date>\d{4}-\d{2}-\d{2})(?P<caveat>[^|]*)\|",
    re.M,
)
# WHY the negative lookahead: a demo name and a filename have the same
# `word.word` shape, so the first version of this pattern read
# `check_status_freshness.py` out of the uncaveated paragraph and reported it as
# a demo named but not marked. The check failed on its first contact with the
# real file, which is the argument for running these against reality before
# trusting them - see the module docstring. Extensions are excluded by name
# rather than by requiring a match against the registry, because a genuine typo
# in a demo name must still be caught rather than silently filtered out.
DEMO_NAME = re.compile(r"`([a-z_]+\.(?!py\b|md\b|json\b|toml\b|lock\b)[a-z_]+)`")
CAVEATED = re.compile(r"\*\*(\w+) rows are marked", re.I)
UNCAVEATED = re.compile(r"\*\*The (\w+) rows with no caveat\*\*", re.I)

# WHY this table goes past twenty: it stopped at twenty and the repo grew
# past it. On 2026-08-21 the uncaveated set reached thirty, `stated()`
# returned None for "thirty", and the check reported "heading reworded?" -
# a real failure with a misleading diagnosis, because the heading was fine
# and the vocabulary was not. Extended rather than switched to digits: the
# prose reads better in words, and a lookup that fails loudly on an unknown
# word is still the right shape. Add the next decade when it is needed.
WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
         "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
         "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
         "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
         "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
         "fifty": 50}


def stated(text: str, pattern: re.Pattern[str]) -> int | None:
    """The number word in a heading, as an int, or None if absent."""
    match = pattern.search(text)
    if not match:
        return None
    word = match.group(1).lower()
    return WORDS.get(word, int(word) if word.isdigit() else None)


def names_after(text: str, pattern: re.Pattern[str]) -> set[str]:
    """Demo names appearing between a heading and the next blank-line-then-bold.

    WHY bounded rather than "to the next blank line": the caveat list is wrapped
    across several source lines with blanks in it, and the uncaveated list runs
    inline through a sentence with parentheses. Reading to the next bold heading
    is the only boundary both share.
    """
    match = pattern.search(text)
    if not match:
        return set()
    rest = text[match.end():]
    end = rest.find("\n**")
    return set(DEMO_NAME.findall(rest if end < 0 else rest[:end]))


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "status.md"
    if not path.exists():
        print(f"missing {path}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8")

    rows = list(ROW.finditer(text))
    if not rows:
        print("no rows parsed - the table format changed", file=sys.stderr)
        return 1

    marked = {m.group("demo") for m in rows
              if "caveat" in m.group("caveat").lower()}
    unmarked = {m.group("demo") for m in rows} - marked
    problems: list[str] = []

    # 1. the stated counts against the markers actually in the table
    for label, pattern, actual in (("caveated", CAVEATED, marked),
                                   ("uncaveated", UNCAVEATED, unmarked)):
        claim = stated(text, pattern)
        if claim is None:
            problems.append(f"no stated {label} count found - heading reworded?")
        elif claim != len(actual):
            problems.append(f"{label}: prose says {claim}, table marks "
                            f"{len(actual)}")

    # 2. the named demos against the marked ones, both directions
    for label, pattern, actual in (("caveated", CAVEATED, marked),
                                   ("uncaveated", UNCAVEATED, unmarked)):
        named = names_after(text, pattern)
        for demo in sorted(named - actual):
            problems.append(f"{label}: {demo} is named but not marked that way "
                            f"in the table")
        for demo in sorted(actual - named):
            problems.append(f"{label}: {demo} is marked in the table but not "
                            f"named in the list")

    # 3. every demo named anywhere in the table exists in the registry
    try:
        from playground.run import DEMOS
    except ImportError as exc:
        print(f"cannot import the demo registry: {exc}", file=sys.stderr)
        return 1
    for demo in sorted({m.group("demo") for m in rows} - set(DEMOS)):
        problems.append(f"{demo} has a row but is not registered in run.py")

    if problems:
        print(f"{len(problems)} problem(s) in {path.name}:\n")
        for line in problems:
            print(f"  {line}")
        print("\n  The table is the evidence and the prose is the summary, so")
        print("  fix the prose to match the table unless a row's marker is")
        print("  itself wrong. This section has been wrong three times.")
        return 1

    print(f"clean: {len(marked)} caveated and {len(unmarked)} uncaveated rows, "
          f"counted, named and registered consistently.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
