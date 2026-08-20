"""
WHAT      A static scan for things that should not be in a public repo: home
          directory paths, uuid-shaped identifiers, currency figures from real
          runs, plan-tier strings, email addresses, and claims phrased as if one
          machine's behaviour were universal.
WHY       The sweep that produced this file was done by reading every file, which
          works exactly once. A pattern scan is worse at judgement and much
          better at not getting bored, so it is the half worth automating.
DOMAIN    D2 Claude Code Configuration and Workflows
TRADEOFF  Every rule here is a regex, so every rule is both over- and
          under-inclusive. It will flag a deliberate example and miss a leak
          phrased in prose. Treating a clean exit as proof of anything is the
          failure mode this file is most likely to cause.
ALTERNATIVE  A commit hook that blocks the push. Better enforcement, and it
          belongs in the repo that is being published rather than in this one,
          which is a study repo where you want to see the finding and argue.

Zero dependencies, stdlib only. No model call.

    python scripts/prepublish_check.py            # scan, exit 1 on findings
    python scripts/prepublish_check.py --list     # show the rules and exit

WHAT THIS CANNOT DO, stated so it is not mistaken for coverage: it cannot detect
a bare organisation or product name, because recognising one requires knowing it,
and hardcoding a list of names into a file that ships would publish exactly the
strings the scan exists to remove. Names are a human review step. The email rule
below is the only reason most of them get caught at all.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = Path(__file__).resolve()

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".mypy_cache",
             ".ruff_cache", ".pytest_cache", "dist", "build"}
SCAN_SUFFIXES = {".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".cfg",
                 ".ini", ".sh", ".ps1", ""}

# WHY: a per-line escape hatch. Some findings are deliberate - a doc explaining
# what a uuid looks like needs to contain one. Without a suppression marker the
# only way to keep such a line is to weaken the rule for everybody.
ALLOW_MARKER = "prepublish: allow"

RULES: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "home-path",
        "an absolute path containing a user or machine name",
        # WHY: the username segment is required. Bare "/home/" or "C:\\Users\\"
        # in prose is a description; with a name attached it is someone's box.
        re.compile(r"(?:[A-Za-z]:[\\/]+Users[\\/]+|/home/|/Users/)[A-Za-z0-9._~-]+"),
    ),
    (
        "uuid",
        "a uuid-shaped identifier (session id, request id, account id)",
        re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                   r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"),
    ),
    (
        "currency",
        "a concrete currency figure - keep ratios, drop absolute amounts",
        # WHY: two shapes. An explicit amount, and a bare high-precision float,
        # which is what a cost figure copied out of a run looks like once the
        # currency symbol has been dropped. "$1" is not matched, so a shell or
        # slash-command placeholder does not trip this.
        re.compile(r"\$\s?\d+\.\d+|\$\s?\d{3,}|\b0\.\d{5,}\b"),
    ),
    (
        "plan-tier",
        "a plan, tier or subscription identifier",
        # WHY: one (?i) at the very start. Python rejects an inline global flag
        # anywhere else, and the alternation below reads as if each branch had
        # its own - it does not, and the compile error is how you find out.
        re.compile(r"(?i)\b(?:rate_?limit_?tier|subscription_?type|plan_?tier)\b"
                   r"|\b[a-z]+_[a-z_]*_\d+x\b"
                   r"|\b(?:max|pro|team)_?\d+x\b"),
    ),
    (
        "email",
        "an email address",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
    (
        "local-claim",
        "a claim scoped to one environment that a reader will read as universal",
        # WHY: assembled from parts rather than written out, so that this file
        # does not match its own rule and report itself. The self-skip below is
        # belt; this is braces.
        re.compile(r"(?i)\bon\s+th(?:is|e\s+author's)\s+"
                   + r"(?:mach" + r"ine|account|box|laptop|setup)\b"
                   + r"|\bin\s+my\s+environment\b"),
    ),
]


def files() -> list[Path]:
    out: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix.lower() not in SCAN_SUFFIXES:
            continue
        # WHY: the scanner holds every pattern it looks for, so scanning itself
        # produces guaranteed noise that trains you to ignore the output.
        if path.resolve() == SELF:
            continue
        out.append(path)
    return out


def scan(path: Path) -> list[tuple[int, str, str, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        # WHY: unreadable is reported as a finding of its own rather than
        # skipped. A file the scan cannot read is a file nobody has reviewed.
        return [(0, "unreadable", "could not be decoded as UTF-8", path.name)]
    hits: list[tuple[int, str, str, str]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if ALLOW_MARKER in line:
            continue
        for name, _, pattern in RULES:
            found = pattern.search(line)
            if found:
                hits.append((number, name, found.group(0)[:60], line.strip()[:90]))
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(prog="prepublish_check")
    parser.add_argument("--list", action="store_true", help="print the rules")
    args = parser.parse_args()

    if args.list:
        for name, description, pattern in RULES:
            print(f"{name:<14}{description}\n{'':<14}/{pattern.pattern[:70]}/")
        return 0

    total = 0
    for path in sorted(files()):
        hits = scan(path)
        if not hits:
            continue
        rel = path.relative_to(ROOT).as_posix()
        for number, name, match, line in hits:
            total += 1
            print(f"{rel}:{number}: [{name}] {match!r}")
            print(f"    {line}")

    scanned = len(files())
    if total:
        print(f"\n{total} finding(s) across {scanned} files.")
        print(f"Fix, or mark a deliberate line with `{ALLOW_MARKER}`.")
        return 1
    print(f"clean: {scanned} files scanned, no findings.")
    print("Note: this cannot detect a bare organisation name. Read the diff too.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
