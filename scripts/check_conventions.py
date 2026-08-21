"""
WHAT      Two conventions from CLAUDE.md that were being enforced by hand: no
          Python file exceeds the declared line cap, and every KNOWN ISSUE
          paragraph that appears as a comment also appears as the constant the
          runner prints.
WHY       Both are rules the repo states and then relies on someone remembering.
          The cap was checked with `awk 'END{print NR}'` after every edit during
          the round that raised it, which is not a control, it is a habit. The
          KNOWN_ISSUE duplication is worse: the convention deliberately requires
          the same paragraph twice, once for the reader who runs the demo and
          once for the reader who only opens the file, and mandated duplication
          with no sync check is the textbook way to end up with two versions of
          a paragraph that disagree about what went wrong.
DOMAIN    D3 Claude Code Configuration and Workflows
TRADEOFF  The cap is read from CLAUDE.md, so raising it stays a one-line edit in
          the document that argues for it - but it also means a reworded
          convention line silently disables the check. It reports that case as a
          failure rather than passing quietly, which is the trade: a check that
          cannot find its own configuration must be loud about it.
ALTERNATIVE  A formatter or linter config with a max-lines rule. Standard, and
          it puts the number somewhere that does not explain itself. The number
          here is 270 because of a specific argument written down in CLAUDE.md,
          and separating the two invites raising it without reading it.

No model call. Pure filesystem and AST.

    uv run python scripts/check_conventions.py

Every check in this repo is proven against a real defect before it is trusted.
This one was run against a file padded past the cap and against a KNOWN ISSUE
comment edited out of sync with its constant, and reported both. The rule comes
from scripts/check_lessons_fresh.py, which passed its first run while its report
was useless, and from scripts/check_caveat_accounting.py, which failed on its
first contact with the real document because a filename has the same shape as a
demo name. A check that has only been seen passing has not been tested.

Exit 0 when both conventions hold, 1 otherwise.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONVENTIONS = ROOT / "CLAUDE.md"
CAP = re.compile(r"Max (\d+) lines per Python file")
# WHY: skipped wholesale rather than filtered later. .venv holds thousands of
# third-party files that this repo's conventions have no claim over, and a
# check that reports them buries its real findings.
SKIP = {".venv", "__pycache__", ".git", "node_modules"}


def normalise(text: str) -> str:
    """Collapse whitespace and case so re-wrapping is not a difference.

    The comment and the constant carry the same prose wrapped to different
    widths and with a different lead-in capital, so anything stricter than this
    reports every instance of the convention as a violation of it.
    """
    return re.sub(r"\s+", " ", text).strip().lower()


def known_issue_blocks(source: str) -> list[str]:
    """Every contiguous comment block that opens with `# KNOWN ISSUE`."""
    blocks: list[str] = []
    current: list[str] | None = None
    for line in source.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# KNOWN ISSUE"):
            current = [stripped.lstrip("#").strip()]
        elif current is not None and stripped.startswith("#"):
            current.append(stripped.lstrip("#").strip())
        elif current is not None:
            blocks.append(" ".join(current))
            current = None
    if current is not None:
        blocks.append(" ".join(current))
    return blocks


def string_constants(tree: ast.Module) -> dict[str, str]:
    """Module-level `NAME = "..."` assignments, literals only."""
    found: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
        if isinstance(value, str) and isinstance(node.targets[0], ast.Name):
            found[node.targets[0].id] = value
    return found


def main() -> int:
    if not CONVENTIONS.exists():
        print(f"missing {CONVENTIONS}", file=sys.stderr)
        return 1
    match = CAP.search(CONVENTIONS.read_text(encoding="utf-8"))
    if not match:
        # WHY: a failure, not a default. Falling back to a hardcoded number
        # would mean the check keeps reporting "clean" against a cap the
        # project no longer declares, which is the exact shape of the drift
        # this file exists to stop.
        print("cannot find the line cap in CLAUDE.md - was the convention "
              "reworded? Expected a line matching 'Max N lines per Python "
              "file'.", file=sys.stderr)
        return 1
    cap = int(match.group(1))

    over: list[str] = []
    desynced: list[str] = []
    checked = 0
    for path in sorted(ROOT.rglob("*.py")):
        if SKIP & set(path.parts):
            continue
        checked += 1
        source = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()

        lines = len(source.split("\n"))
        if source.endswith("\n"):
            lines -= 1
        if lines > cap:
            over.append(f"{rel}: {lines} lines, cap is {cap} ({lines - cap} over)")

        blocks = known_issue_blocks(source)
        if not blocks:
            continue
        try:
            constants = string_constants(ast.parse(source))
        except SyntaxError as exc:
            desynced.append(f"{rel}: will not parse ({exc})")
            continue
        for block in blocks:
            if not any(normalise(value) in normalise(block)
                       for value in constants.values()):
                desynced.append(
                    f"{rel}: a KNOWN ISSUE comment block has no matching "
                    f"constant. The convention requires the same paragraph "
                    f"twice - as the constant the runner prints and as a "
                    f"comment on the failing line - and these two have drifted.")

    if over:
        print(f"OVER THE LINE CAP ({cap}, declared in CLAUDE.md)")
        for line in over:
            print(f"  {line}")
        print("\n  Split the file, or move prose to the document that owns it.")
        print("  Raise the cap only after a split has been tried and left the")
        print("  file over anyway - CLAUDE.md says which splits were tried.\n")
    if desynced:
        print("KNOWN ISSUE TEXT OUT OF SYNC")
        for line in desynced:
            print(f"  {line}")
        print("\n  Edit whichever copy is wrong so both say the same thing.\n")

    if over or desynced:
        return 1
    print(f"clean: {checked} file(s) checked, none over {cap} lines, every "
          f"KNOWN ISSUE comment matches its constant.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
