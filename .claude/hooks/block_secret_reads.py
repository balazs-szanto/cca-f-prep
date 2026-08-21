"""
WHAT      PreToolUse hook that denies any Read or Bash call touching credential
          files, regardless of what the model was asked to do.
WHY       The deny list in settings.json covers paths it can pattern-match. A
          hook sees the resolved tool input and can reason about it - here, it
          catches a credential path smuggled inside a Bash command string, which
          a Read(...) glob rule never inspects.
DOMAIN    D3 Claude Code Configuration and Workflows
TRADEOFF  Programmatic guardrails are deterministic and unbypassable by prompt
          injection, but they are blunt: this hook cannot tell a legitimate
          `claude auth status` from an attempt to exfiltrate a token, so it
          allows the former only because the pattern list happens to miss it.
          Every new evasion needs a new pattern - the list never finishes. It
          also fails closed on an unparseable event, which trades availability
          for safety: a schema change here stops the session rather than quietly
          disarming the guard.
ALTERNATIVE  Asking the model in the system prompt not to read secrets. That is
          cheaper and more flexible, but it is advisory: anything that can put
          text in the context can argue with it. Use prompt rules for taste and
          hooks for things that must not happen.

This file is stdlib-only on purpose: hooks run as bare subprocesses and must not
depend on the project venv being active.

UNVERIFIED, and it is the failure mode most likely to disarm this hook without
telling you. `settings.json` registers it as
`python "$CLAUDE_PROJECT_DIR/.claude/hooks/block_secret_reads.py"`. Whether that
variable expands depends on the shell Claude Code uses to run hooks, which has
not been established here on Windows - and JSON has no comments, so this
docstring is the only place the caveat can live. The hook logic itself is
MEASURED: 7/7 cases pass when invoked directly, including a BOM-prefixed payload
and an accented path. Only the invocation string is untested.

What an unexpanded variable costs: the path is invalid, the hook process fails to
start, and the guard is simply absent. Note that this defeats the fail-closed
design described above - failing closed only applies once the script is running.
A guard that never starts refuses nothing, and nothing reports it.

To check in about five minutes: replace the command with a probe that only
records the argument it was handed, trigger any Read or Bash call in a session,
and read what it wrote. An absolute path means the shell expanded the variable;
the literal text `$CLAUDE_PROJECT_DIR` means it did not, and `%CLAUDE_PROJECT_DIR%`
expanding instead would mean the hook shell is `cmd.exe`. The portable fix, if it
comes to that, is a repo-relative path rather than either syntax. The same
applies to `check_turn_cap_guard.py`, registered the same way.
"""
import json
import sys
from typing import NoReturn

# WHY: substrings, not globs. The point is to catch the path wherever it appears -
# as a Read file_path, or buried in the middle of a shell pipeline.
FORBIDDEN = (".credentials.json", "ANTHROPIC_API_KEY", ".env")


# NoReturn (not None) so type checkers know control stops here.
def deny(reason: str) -> NoReturn:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def main() -> None:
    try:
        # WHY: read bytes and decode explicitly. On Windows sys.stdin defaults to
        # the ANSI codepage, so a single accented character in a file path raises
        # UnicodeDecodeError - the guardrail would fail exactly when the input is
        # unusual. utf-8-sig also tolerates a leading BOM.
        event = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        # WHY: fail closed. If the event cannot be parsed we do not know which
        # tool is being called, and a secrets guard that guesses is not a guard.
        # The cost is real: a schema change here bricks the session until fixed,
        # which is why the reason string names this file.
        deny(f"block_secret_reads.py could not parse the hook event ({exc}).")

    # Flatten every string in the tool input; we do not care which field it was.
    haystack = json.dumps(event.get("tool_input", {}))

    for needle in FORBIDDEN:
        if needle in haystack:
            deny(
                f"Blocked by .claude/hooks/block_secret_reads.py: the tool input "
                f"references {needle!r}. This playground authenticates through the "
                f"CLI OAuth session and never reads credentials directly."
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
