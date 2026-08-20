"""
WHAT      Single dispatcher that lists and runs every demo in this playground.
WHY       A study repo needs one obvious entry point; hunting for file paths is
          friction that stops you from actually running the examples.
DOMAIN    D2 Claude Code Configuration and Workflows
TRADEOFF  The registry below is hand-maintained, so a new demo file stays
          invisible until someone adds a line to it. Auto-discovery by globbing
          the package would fix that, but would lose both the curated one-line
          descriptions and the deliberate reading order.
ALTERNATIVE  For a package meant to be installed rather than read, declare
          [project.scripts] console entry points and let the installer put them
          on PATH; you drop the registry but gain nothing while studying.

Makes no model call itself. Run `--list` first.
"""
from __future__ import annotations

import argparse
import importlib.util
import runpy
import sys

from playground import lessons

# WHY: ordered by teaching sequence, not alphabetically. `--list` doubles as the
# reading order, so the insertion order of this dict is load-bearing - Python
# dicts have preserved insertion order since 3.7, which is what makes this work.
DEMOS: dict[str, str] = {
    "basics.check_auth": "D0  Find out which credential the CLI will actually use",
    "basics.hello": "D0  Smallest possible query() call and the async iterator",
    "basics.prompt_shape": "D3  Same text, two prompt constructions, one variable",
    "basics.structured": "D0  Force a JSON schema and validate the payload shape",
    "basics.tools": "D0  One in-process MCP tool the agent is forced to call",
    "orchestration.triage": "D1  A decomposition that works, and why it splits there",
    "orchestration.workflow_vs_agent": "D1  One task as a fixed workflow and as an agent, measured",
    "orchestration.subagent": "D1  Delegate to a subagent, and when that costs more than it saves",
    "tools_mcp.where_code_runs": "D4  Whose process runs a tool, and why you cannot tell",
    "tools_mcp.schema_design": "D4  One tool, weak vs strong schema, behaviour compared",
    "tools_mcp.parallel_tools": "D4  Independent vs dependent calls, grouped and timed",
    "tools_mcp.tool_overhead": "D4  What a tools array costs before anything calls it",
    "tools_mcp.external_mcp": "D4  Connect to an external MCP server over stdio",
    "tools_mcp.permission_gate": "D4  Block a destructive tool call with can_use_tool",
    "reliability.session_resume": "D5  Resume a session, and see what does not survive",
    "reliability.error_taxonomy": "D5  Host, environment, argument and reasoning failures, sorted",
    "reliability.context_budget": "D5  Read real context usage and the compaction threshold",
}


def _exists(demo: str) -> bool:
    # WHY: find_spec locates a module without importing it. Importing to test
    # existence would execute the module, and several demos call asyncio.run() at
    # import time - listing the demos would run them.
    try:
        return importlib.util.find_spec(f"playground.{demo}") is not None
    except ModuleNotFoundError:
        # WHY: find_spec raises rather than returning None when a *parent* package
        # is missing, so the two failure modes need one answer between them.
        return False


def _marker(name: str) -> str:
    """One character summarising what running this demo costs you."""
    if not _exists(name):
        return "?"
    data = lessons.extract(lessons.path_of(name))
    # WHY: the known-issue marker outranks the cost marker. If a demo cannot
    # complete here, what it would have cost is not the thing you need to know.
    if data.get("KNOWN_ISSUE"):
        return "!"
    if not data.get("LESSON"):
        return "?"
    return " " if lessons.is_free(data["LESSON"]) else "$"


def _list() -> None:
    print("Demos, in reading order:\n")
    seen: set[str] = set()
    for name, description in DEMOS.items():
        marker = _marker(name)
        seen.add(marker)
        print(f" {marker} {name:<34} {description}")
    # WHY: the legend only lists markers that actually appeared. A permanent
    # footer explaining every possible symbol trains you to skip the column.
    legend = {
        "$": "$ = makes model calls, so it spends quota",
        "!": "! = declares a KNOWN_ISSUE; may not complete, and says why if not",
        "?": "? = module missing, or missing its LESSON block",
        " ": "  = free: no model call at all",
    }
    print()
    for key in ("$", "!", "?", " "):
        if key in seen:
            print(f"  {legend[key]}")
    # WHY: `uv run python`, not bare `python`. The demos import playground and
    # mockserver from .venv, so a system interpreter fails with ModuleNotFound
    # before any demo code runs - the single most likely first failure for
    # someone who just cloned this.
    print("\nRun one with:  uv run python -m playground.run <demo>")
    print("               (or activate .venv and drop the `uv run` prefix)")


def main() -> None:
    parser = argparse.ArgumentParser(prog="uv run python -m playground.run")
    parser.add_argument("demo", nargs="?", help="demo to run, e.g. basics.hello")
    parser.add_argument("--list", action="store_true", help="list every demo")
    args = parser.parse_args()

    # WHY: no argument means list, rather than an error. The most likely reason
    # you typed this command with nothing after it is that you forgot the names.
    if args.list or args.demo is None:
        _list()
        return

    if args.demo not in DEMOS:
        # WHY: print the list on a wrong name too. A bare "unknown demo" makes you
        # run a second command to find out what you should have typed.
        print(f"Unknown demo: {args.demo}\n", file=sys.stderr)
        _list()
        sys.exit(1)

    # WHY: run_name="__main__" makes modules that call asyncio.run() at import
    # time (the basics/ files) behave exactly as they do when run directly. Plain
    # import would load them without triggering the guarded entry points, and the
    # newer files - which do use `if __name__ == "__main__"` - would do nothing.
    runpy.run_module(f"playground.{args.demo}", run_name="__main__")


if __name__ == "__main__":
    main()
