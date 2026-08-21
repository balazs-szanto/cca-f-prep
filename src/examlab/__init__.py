"""
WHAT      The code-level half of the CCA-F material: the raw agentic loop, tool
          choice, prompt chaining, structured output, validation-retry, and the
          batch API. Everything the Claude Agent SDK owns on your behalf and
          therefore never shows you.
WHY       `playground/` runs on the Agent SDK over a Claude Code OAuth session.
          That SDK builds the requests, runs the tool round trip and hands you
          typed messages - which is the right trade for building an agent and
          the wrong one for learning what an agent *is*. Six task statements in
          the official blueprint are written against request-level constructs
          (`stop_reason`, `tool_choice`, `tool_result`, `custom_id`) that have
          no `ClaudeAgentOptions` equivalent. `docs/tool-surface.md` counts ten
          of twenty-four official tool-use pages as API-ONLY for this reason.
DOMAIN    D1 (27%), D2 (18%), D4 (20%). See CLAUDE.md in this
          directory for why those numbers do not match `playground/`'s.
TRADEOFF  Every module here runs end to end with no credential, against a
          fabricated response script. That buys a package a reader can execute
          on any machine for nothing, and it costs the one thing a live run
          gives you: the responses are what the author decided the model would
          say, so nothing here is evidence about model behaviour. Each module
          says so in its own banner rather than relying on you remembering it.
ALTERNATIVE  Write it as prose in `docs/` and skip the code. Cheaper, and it
          fails at the one thing that matters here - a loop you can read but
          not run is a loop whose bugs you cannot find.

Nothing in this package imports `claude_agent_sdk`, and nothing in `playground/`
imports this - not even the dispatcher that lists it, which resolves these
modules by name. The separation is the point; see CLAUDE.md.

There is one entry point for the whole repo, and it is not in this package:

    uv run python -m playground.run --list
    uv run python -m playground.run examlab.agentic_loop
"""
