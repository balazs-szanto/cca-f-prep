"""
WHAT      A static check that flags an agent loop which sets max_turns but is not
          wrapped in a try. Runs standalone over the repo, or as a PostToolUse
          hook over the file that was just edited.
WHY       Hitting max_turns yields a ResultMessage and THEN raises, so an
          unguarded loop loses everything after it - usually the part that
          reports what the run measured. This bug has been written and fixed
          three separate times in this repo by someone who knew about it and had
          documented it twice. Knowing a rule is not the same as enforcing it.
DOMAIN    D3 Claude Code Configuration and Workflows
TRADEOFF  It parses the AST rather than the text, so it understands structure and
          is blind to intent: a bare `except Exception: pass` satisfies it
          completely. It proves a try exists, never that the handler is sensible.
ALTERNATIVE  A runtime wrapper - a helper every demo calls instead of query() -
          which would make the mistake unrepresentable rather than merely
          detectable. Rejected here because the demos exist to show the raw SDK
          surface, and hiding the sharp edge would delete the lesson.

Makes no model call. Pure AST inspection.

    python .claude/hooks/check_turn_cap_guard.py            # scan the repo
    python .claude/hooks/check_turn_cap_guard.py FILE...    # scan named files
    <hook json on stdin> | python .claude/hooks/check_turn_cap_guard.py --hook
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__"}

# WHY two severities rather than one list. query() is DOCUMENTED to yield the
# ResultMessage and then raise, so an unguarded loop over it is a defect.
# receive_response() belongs to a streaming ClaudeSDKClient session, which is
# documented NOT to raise on a cap - so the same shape there is a note, not an
# error. Reporting both at one severity would be easier and would train the
# reader to dismiss the output, which is how a checker stops working.
RAISES = ("query",)
ADVISORY = ("receive_response",)


def _iter_name(node: ast.expr) -> str | None:
    """The callee name of `async for x in <call>`, if it is a call at all."""
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _sets_turn_cap(tree: ast.AST) -> bool:
    # WHY: module-scoped, not per-call. Without a cap the loop cannot raise for
    # this reason, so flagging it would be noise; with one anywhere in the file,
    # every loop in that file is a candidate. Coarse on purpose - a precise
    # version would have to resolve which options object reached which call.
    return any(
        isinstance(node, ast.keyword) and node.arg == "max_turns"
        for node in ast.walk(tree)
    )


def _unguarded_loops(tree: ast.AST) -> list[tuple[int, str]]:
    """Every guarded-iterator loop with no ast.Try anywhere above it."""
    found: list[tuple[int, str]] = []

    def walk(node: ast.AST, in_try: bool) -> None:
        for child in ast.iter_child_nodes(node):
            # WHY: only the body counts as protected. A loop written inside the
            # `except` or `finally` clause of some other try is not covered by
            # it, and treating the whole Try node as protective would miss that.
            if isinstance(child, ast.Try):
                for stmt in child.body:
                    walk(stmt, True)
                for clause in child.handlers + child.orelse + child.finalbody:
                    walk(clause, in_try)
                continue
            if isinstance(child, (ast.AsyncFor, ast.For)):
                name = _iter_name(child.iter)
                if name in RAISES + ADVISORY and not in_try:
                    found.append((child.lineno, name or "?"))
            walk(child, in_try)

    walk(tree, False)
    return found


def check(path: Path) -> tuple[list[str], list[str]]:
    """Return (defects, notes) for one file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError) as exc:
        return ([f"{path}: could not be parsed ({type(exc).__name__})"], [])
    if not _sets_turn_cap(tree):
        return ([], [])
    rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
    defects, notes = [], []
    for line, name in _unguarded_loops(tree):
        if name in RAISES:
            defects.append(
                f"{rel}:{line}: `async for ... in {name}(...)` is not inside a "
                f"try, and this file sets max_turns.\n"
                f"    Hitting the cap yields the ResultMessage and THEN raises, "
                f"so everything after this loop is lost.\n"
                f"    Wrap it: `try: ... except ClaudeSDKError as exc:` and "
                f"report `message.subtype` rather than swallowing it."
            )
        else:
            notes.append(
                f"{rel}:{line}: `async for ... in {name}(...)` is unguarded. A "
                f"streaming session is documented not to raise on a cap, so this "
                f"is probably fine - but it is the same shape as the defect "
                f"above, and the two are easy to copy between."
            )
    return (defects, notes)


def _hook_paths() -> list[Path]:
    """Read a PostToolUse payload and return the file it touched, if any."""
    # WHY: bytes then decode with utf-8-sig, not json.load(sys.stdin). On Windows
    # the text stream uses the ANSI code page, so one accented character in a
    # path raises UnicodeDecodeError - the exact bug already fixed once in
    # block_secret_reads.py. Two hooks, same trap.
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8-sig") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []
    target = (payload.get("tool_input") or {}).get("file_path")
    if not target:
        return []
    path = Path(target)
    # WHY this fails OPEN, unlike block_secret_reads.py which fails closed: that
    # one is a security guard, where refusing on doubt is correct. This is a
    # lint. A lint that blocks every edit whose path it could not resolve gets
    # switched off within the hour, and then it guards nothing at all. The cost
    # is real - an unresolvable path means the check silently did not run - so
    # the standalone scan over the whole repo stays the authoritative form.
    return [path] if path.suffix == ".py" and path.exists() else []


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--hook"]
    hook_mode = "--hook" in sys.argv

    if hook_mode:
        paths = _hook_paths()
    elif args:
        paths = [Path(a) for a in args]
    else:
        paths = [p for p in ROOT.rglob("*.py")
                 if not any(part in SKIP_DIRS for part in p.parts)]

    defects: list[str] = []
    notes: list[str] = []
    for path in paths:
        found, noted = check(path)
        defects += found
        notes += noted

    stream = sys.stderr if hook_mode else sys.stdout
    for line in defects:
        print(line, file=stream)
    # WHY: notes are printed even when there are defects, but never affect the
    # exit code. A check that fails on advisories gets suppressed wholesale.
    if notes and not hook_mode:
        print(f"\n{len(notes)} advisory note(s), not counted as failures:")
        for line in notes:
            print(f"  {line}")
    if defects:
        # WHY: exit 2 in hook mode. That is the code Claude Code treats as
        # actionable feedback rather than as a broken hook, so the message above
        # reaches the agent that just wrote the bug, not a log nobody reads.
        return 2 if hook_mode else 1
    if not hook_mode:
        print(f"\nclean: {len(paths)} file(s) checked, every capped query() "
              f"loop is inside a try.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
