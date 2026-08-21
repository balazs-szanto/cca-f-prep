"""
WHAT      The printing every module here does: a banner, section rules, and a
          transcript line for one request/response exchange.
WHY       Eight modules each printing their own header is eight chances for the
          transport note to be worded differently or forgotten, and the
          transport note is the one line a reader must not miss. Centralising it
          makes omission impossible rather than unlikely.
DOMAIN    D3 Claude Code Configuration and Workflows (20%)
TRADEOFF  A shared presenter fixes the layout for every module, so a demo that
          would be clearer in a table has to argue for its own printing instead
          of just writing it. Accepted: uniform framing is what lets a reader
          compare two modules, and the modules here are meant to be compared.
ALTERNATIVE  Import `playground/teach.py`, which does the same job. Rejected on
          the rule in this directory's CLAUDE.md: this package does not depend on
          that one, in either direction.

Not a demo, so it carries no LESSON block. Makes no model call.
"""
from __future__ import annotations

WIDTH = 78


def rule(title: str = "") -> None:
    """A section divider, with an optional inline title."""
    if not title:
        print("-" * WIDTH)
        return
    print(f"\n--- {title} " + "-" * max(0, WIDTH - len(title) - 6))


def banner(*, title: str, domain: str, question: str, expect: str, note: str) -> None:
    """Header every module prints before it does anything.

    `note` is the transport note from `transport.choose()`. It is a required
    keyword rather than defaulted so that a module cannot print a banner without
    saying where its numbers came from.
    """
    print("=" * WIDTH)
    print(title)
    print("=" * WIDTH)
    print(f"DOMAIN   {domain}")
    print(f"ASKS     {question}")
    print(f"EXPECT   {expect}")
    print()
    for line in _wrap(note):
        print(line)
    print("=" * WIDTH)


def exchange(index: int, *, sent: str, got: str, stop_reason: str) -> None:
    """One request/response pair, numbered from 1.

    The request summary comes first because that is the half a live transport
    hides, and the half a reader's own code is responsible for.
    """
    print(f"\n  [{index}] sent     {sent}")
    print(f"      got      {got}")
    print(f"      stop     {stop_reason}")


def table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    """A left-aligned table sized to its content. No dependencies."""
    # WHY: the list form rather than max(a, *b). With no rows, max(int) raises
    # TypeError - a shared helper that crashes on an empty table is a defect
    # waiting for the one caller that has nothing to show.
    widths = [max([len(h)] + [len(r[i]) for r in rows]) for i, h in enumerate(headers)]
    print("  " + "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)))
    print("  " + "  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        print("  " + "  ".join(row[i].ljust(widths[i]) for i in range(len(headers))))


def _wrap(text: str) -> list[str]:
    """Greedy wrap to WIDTH. Deliberately not textwrap - two lines, no import."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        if len(current) + len(word) + 1 > WIDTH:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return lines
