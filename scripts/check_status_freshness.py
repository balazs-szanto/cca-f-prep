"""
WHAT      Compares each demo's recorded run date in docs/status.md against the
          modification time of the file that row describes, and fails when the
          file is newer than the measurement that justifies it.
WHY       This repo's core claim is that it separates what was measured from what
          was assumed. The defect that keeps breaking that claim is always the
          same shape: an edit lands after the run, and the row keeps asserting an
          output nobody has seen since. It has been introduced, found and
          declared fixed four times. Prose accounting did not hold; this does.
DOMAIN    D2 Claude Code Configuration and Workflows
TRADEOFF  Modification time is a crude proxy for "the behaviour might have
          changed". A comment fix trips it exactly as loudly as a rewritten
          prompt, so it over-reports, and a caveat that fires constantly is a
          caveat people learn to skip. The sharper limit is resolution: status.md
          records a DATE, the filesystem records a timestamp, so an edit made on
          the same day as the run it invalidates cannot be ordered against it.
          That is not hypothetical - on the day this was written, every row was
          in exactly that state, so the first version of this script reported
          "clean" and proved nothing.
ALTERNATIVE  Hash the parts that affect behaviour - the LESSON block and the
          function bodies - and ignore docstring churn. More precise, and it
          needs a definition of "affects behaviour" that is itself a judgement
          call, which is the thing being automated away.

No model call. Pure filesystem and text.

    uv run python scripts/check_status_freshness.py

Exit 0 when every row is fresh or explicitly carries a caveat. Exit 1 otherwise.
A row that is stale AND says so is not a failure - that is the honest state the
caveat exists to record.
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS = ROOT / "docs" / "status.md"
DEMO_ROOT = ROOT / "src" / "playground"

# WHY: parses the table rather than importing run.py. The question this asks is
# "does the document agree with the tree", so reading the document as a document
# is the whole point - resolving the names through code would hide a row that
# names a demo which no longer exists.
ROW = re.compile(
    r"^\|\s*`(?P<demo>[a-z_]+\.[a-z_]+)`\s*\|"
    r"\s*(?P<state>[^|]+?)\s*\|"
    r"\s*(?P<date>\d{4}-\d{2}-\d{2})(?P<caveat>[^|]*)\|",
    re.M,
)


def demo_path(demo: str) -> Path:
    return DEMO_ROOT.joinpath(*demo.split(".")).with_suffix(".py")


def main() -> int:
    if not STATUS.exists():
        print(f"missing {STATUS}", file=sys.stderr)
        return 1

    rows = list(ROW.finditer(STATUS.read_text(encoding="utf-8")))
    if not rows:
        print("no rows parsed from status.md - the table format changed", file=sys.stderr)
        return 1

    stale_uncaveated: list[str] = []
    stale_caveated: list[str] = []
    same_day: list[str] = []
    missing: list[str] = []

    for m in rows:
        demo, date_s = m.group("demo"), m.group("date")
        caveated = "caveat" in m.group("caveat").lower()
        path = demo_path(demo)
        if not path.exists():
            missing.append(f"{demo}: status.md names it, {path.name} does not exist")
            continue

        run_date = dt.date.fromisoformat(date_s)
        mtime = dt.date.fromtimestamp(path.stat().st_mtime)
        rel = path.relative_to(ROOT).as_posix()
        mark = "" if caveated else "   <-- no caveat"

        if mtime < run_date:
            continue
        if mtime == run_date:
            # WHY: reported, never silently passed. Equal dates mean the ordering
            # is unknown, and treating unknown as fresh is how the first version
            # of this script announced "clean" for fourteen rows it had not
            # actually checked. Unknown is a third answer, not a quiet yes.
            same_day.append(f"{demo}: measured and modified on {run_date} ({rel}){mark}")
            continue
        note = (f"{demo}: last measured {run_date}, file modified {mtime} ({rel})")
        (stale_caveated if caveated else stale_uncaveated).append(note)

    print(f"{len(rows)} rows in status.md\n")
    if missing:
        print("ROWS NAMING A FILE THAT IS NOT THERE")
        for line in missing:
            print(f"  {line}")
        print()
    if same_day:
        print("INDETERMINATE - measured and modified on the same date")
        for line in same_day:
            print(f"  {line}")
        print("\n  status.md records a date; the filesystem records a timestamp.")
        print("  These rows cannot be ordered from a date alone, so this script")
        print("  does not claim they are fresh. Judge them by hand, or record a")
        print("  time alongside the date to make them decidable.")
        print()
    if stale_caveated:
        print("STALE, AND THE ROW SAYS SO (not a failure)")
        for line in stale_caveated:
            print(f"  {line}")
        print()
    if stale_uncaveated:
        print("STALE, AND THE ROW DOES NOT SAY SO")
        for line in stale_uncaveated:
            print(f"  {line}")
        print("\n  Each row above asserts an output that has not been produced")
        print("  since the file changed. Either re-run it and update the date,")
        print("  or mark the row '(see caveat)' and name it in the caveat list.")
        print()

    if missing or stale_uncaveated:
        return 1
    if same_day:
        print(f"no proven staleness, but {len(same_day)} row(s) are undecidable "
              f"at date resolution - see above.")
        return 0
    print("clean: every row is either fresh or explicitly caveated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
