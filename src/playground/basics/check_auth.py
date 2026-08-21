"""
WHAT      Establish which credential the Claude Code CLI will actually use, and
          say clearly whether it matches the one this repo is written around.
WHY       The SDK does not authenticate. It spawns the CLI, and the CLI resolves
          credentials by its own precedence rules - an API key in the environment
          silently outranks an OAuth session. Without this check, "it works"
          and "it is billing the account I meant" are different questions.
DOMAIN    D3 Claude Code Configuration and Workflows
TRADEOFF  Shelling out to the CLI costs a subprocess on every startup and ties
          this file to the CLI's output format: if `auth status --json` changes
          its field names, this breaks. That is accepted because the alternative
          is worse - see below.
ALTERNATIVE  Parse the CLI's credential file directly. No subprocess, and wrong:
          a credential file on disk proves a token exists, not that the CLI will
          prefer it over an environment variable. This file used to do that and
          reported success while an API key would have won.

Makes no model call. Run it first; every other demo assumes it passed.

A note on what this file deliberately does NOT print. `claude auth status --json`
also returns the account email, the organisation name and the plan tier. Those
identify you; they do not answer the question this file asks, which is only
"which KIND of credential pays". Printing them would put identifiers into
whatever terminal, screenshot or CI log this output lands in, for no teaching
value. Read the raw JSON yourself if you want them.
"""
import json
import os
import shutil
import subprocess
import sys
from typing import NoReturn

from playground import teach

LESSON = {
    "domain": "D3 Claude Code Configuration and Workflows",
    "setup": "The Claude Code CLI on PATH and an authenticated session. Nothing "
             "else in this repo needs to have run first.",
    "run": "uv run python -m playground.run basics.check_auth",
    "cost": "free - no model call, one subprocess",
    "expect": "Two fields - authMethod and apiProvider - and then either 'session "
              "matches this repo's assumption' or a block explaining that yours "
              "does not, what this repo assumes, and how to proceed anyway.",
    "learn": "The SDK does not authenticate anything - it spawns the CLI, and the "
             "CLI picks a credential by its own precedence, where an environment "
             "API key silently outranks an interactive session.",
}

# WHY: two fields, not five. Both are closed vocabularies describing the kind of
# credential; neither identifies a person, an organisation or a plan.
FIELDS = ("authMethod", "apiProvider")

# WHY: the repo's own assumption, named once here rather than assumed everywhere.
EXPECTED_METHOD = "claude.ai"
OVERRIDE = "PLAYGROUND_ALLOW_ANY_AUTH"


# WHY: NoReturn, not None. Type checkers use it to know control stops here, which
# is what lets the caller treat a post-fail() variable as definitely assigned.
def fail(msg: str) -> NoReturn:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def explain_mismatch(method: str | None) -> None:
    """The branch most readers will hit. It must leave them somewhere to go."""
    # WHY: printed to stdout and NOT an error until the last line. A reader whose
    # setup differs has not done anything wrong; they have hit an assumption this
    # repo makes for its own reasons, and the useful response is to explain the
    # assumption rather than to exit 1 at them.
    print(f"\n{'-' * 70}")
    print("Your session does not match what this repo assumes.\n")
    print(f"  found    : authMethod = {method!r}")
    print(f"  expected : authMethod = {EXPECTED_METHOD!r}\n")
    print("THE RULE. Every demo here is written to run against an interactive")
    print("Claude Code login rather than an API key.\n")
    print("WHY IT EXISTS. It is a cost-attribution rule, not a technical one. The")
    print("demos make real model calls, and the author wanted them charged to a")
    print("subscription rather than to a metered API account where a runaway loop")
    print("turns into an invoice. Nothing in the SDK requires this.\n")
    print("WHAT TO DO, pick one:")
    print("  1. Authenticate the CLI interactively (`claude auth login`) and")
    print("     re-run. This is what the rest of the repo assumes.")
    print("  2. Keep your current setup and read rather than run. Every free")
    print("     item still works: `--list`, docs/lessons.md, the mock server")
    print("     driven by hand, and the whole of docs/.")
    print(f"  3. Keep your setup and run anyway, knowingly: set {OVERRIDE}=1.")
    print("     The demos will work. They will bill whatever your CLI resolves,")
    print("     and each demo's banner tells you its cost before it runs.")
    print(f"{'-' * 70}")


def main() -> None:
    teach.banner(LESSON)

    # WHY: checked first and separately from the CLI status below. This variable
    # is read by the CLI subprocess we are about to spawn, so by the time
    # `auth status` reports anything it has already been influenced by it.
    if os.environ.get("ANTHROPIC_API_KEY"):
        fail(
            "ANTHROPIC_API_KEY is set in your environment.\n\n"
            "It outranks an interactive CLI session, so calls would bill your\n"
            "API account. This repo is written around the other case - see the\n"
            "auth rule in CLAUDE.md, which exists for cost attribution.\n\n"
            "If that is genuinely what you want, this repo is still worth\n"
            "reading; it is just not budgeted for it. To run the demos as\n"
            "written, clear the variable for this shell:\n\n"
            "  PowerShell -> Remove-Item Env:ANTHROPIC_API_KEY\n"
            "  bash/zsh   -> unset ANTHROPIC_API_KEY"
        )

    # WHY: resolve the path explicitly rather than trusting the OS to find it.
    # This also gives a clear error instead of a FileNotFoundError raised from
    # deep inside subprocess.
    claude = shutil.which("claude")
    if claude is None:
        fail("`claude` CLI not found on PATH. Install it, then authenticate it.")

    result = subprocess.run(
        [claude, "auth", "status", "--json"], capture_output=True, text=True
    )
    if result.returncode != 0:
        fail(f"`claude auth status` failed:\n{result.stderr.strip()}")

    status = json.loads(result.stdout)
    if not status.get("loggedIn"):
        fail("Not logged in. Authenticate the CLI, then re-run.")

    for key in FIELDS:
        print(f"{key:<17}: {status.get(key)}")

    method = status.get("authMethod")
    matched = method == EXPECTED_METHOD
    if not matched:
        explain_mismatch(method)
        # WHY: the override is read AFTER the explanation is printed, so someone
        # who set it still sees what they opted out of. A silent escape hatch
        # teaches nothing and gets cargo-culted into the next repo.
        if not os.environ.get(OVERRIDE):
            sys.exit(1)
        print(f"\n{OVERRIDE} is set - continuing anyway, knowingly.")
    else:
        print("\nSession matches this repo's assumption.")

    teach.closing(
        LESSON,
        observed=[
            f"authMethod came back {method!r} and apiProvider "
            f"{status.get('apiProvider')!r}. That pair answers 'what KIND of "
            f"credential is paying', which is the only part your code can act on.",
            "Both values were read from the CLI by running it as a subprocess. "
            "No code in this repository holds, reads or forwards a credential.",
            "ANTHROPIC_API_KEY was absent from the environment, which is the only "
            "reason the check above could reach the CLI's own session at all.",
        ],
        naive="You would expect a program that calls Claude to hold a credential. "
              "Nothing here does. The SDK launches `claude` as a subprocess and "
              "inherits whatever that process resolves, so the only honest thing "
              "your code can do is inspect the outcome and decide whether to "
              "proceed - which is what the branch above is. Note that this makes "
              "'it works' and 'it is billing what I intended' genuinely separate "
              "questions, and only one of them shows up in your test suite.",
    )


if __name__ == "__main__":
    main()
