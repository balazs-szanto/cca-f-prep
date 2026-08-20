"""
WHAT      What a tools array costs before anything calls it. Six sessions with
          different toolsets, each read with get_context_usage() before a single
          prompt is sent - once on connect, then repeatedly until the reading
          stops moving. The two numbers disagree, the gap is a race, and both
          halves are the demo.
WHY       Tool definitions are input tokens. The name, the description and the
          whole JSON schema are rendered into the prompt for the life of the
          session, whether or not the model ever calls them. The instinct is to
          attach a tool because it might be useful; this file prices that
          instinct, then shows that the instrument you would price it with reads
          zero if you ask it too early.
DOMAIN    D4 Tool Design and MCP Integration
TRADEOFF  Resident cost is not total cost. An uncalled tool still costs its
          definition every turn, mostly at cache rates; a tool that IS called
          adds a tool_use block, a tool_result block and at least one extra
          turn, none of which appear below. This prices the floor only.
ALTERNATIVE  Count the tokens yourself with the token-counting endpoint before
          sending. More precise, and it needs the Messages API - see
          docs/tool-surface.md.

Zero model calls. get_context_usage() and get_mcp_status() are control requests,
not inference requests, so this file is free to run as often as you like - which
is the only reason the finding below was affordable to chase across three
rewrites. At inference prices it would have been cheaper to ship the wrong number.

MEASURED 2026-08-20, and it is why this file polls instead of reading once. Read
immediately after connecting, a session with eight in-process MCP tools reported
the same total as one with none - 1,316 tokens, no `MCP tools` category at all.
The tools were always going to be there; the instrument had not counted them yet.
Worse, settling is a RACE: the poll counts in the table below are not the same
from run to run, and the first draft of this file, which asked once and believed
the answer, got 226 tokens right and 1,773 wrong in a single run. INFERRED and
left as inference: the likeliest cause is lazy registration of in-process MCP
servers, which this repo cannot see inside the CLI to confirm. The behaviour is
what is measured, and the rule follows from the behaviour alone.

RELATION TO reliability/context_budget.py, which must not be duplicated. That
file measures the resting total and the distance to the auto-compact threshold -
the floor and the ceiling of one session, with the toolset held fixed. This file
holds everything else fixed and changes a single variable, the toolset, so the
two are the same instrument pointed at different questions. Read that one for
what a window costs; read this one for what a tool costs inside it.

DOCUMENTED and NOT measurable here, from
<https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview> fetched
2026-08-20: the API builds a tool-use system prompt whose size depends on
`tool_choice` - on Opus 5, 286 tokens for `auto`/`none` against 406 for
`any`/`tool`, so forcing a call costs about 120 tokens every turn before your own
definitions are counted. `tool_choice` is a Messages API parameter with no
ClaudeAgentOptions equivalent, so that figure is quoted, not claimed. What else
is out of reach, and why: docs/tool-surface.md.
"""
from __future__ import annotations

import asyncio
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions, ClaudeSDKClient, create_sdk_mcp_server, tool,
)

from playground import teach
from playground.tools_mcp.instruments import settle

LESSON = {
    "domain": "D4 Tool Design and MCP Integration",
    "setup": "basics.check_auth passed. Read DESCRIPTION and SCHEMA below and "
             "guess, before running, what one tool of that shape costs you per "
             "session, on every turn, including the turns nobody calls it.",
    "run": "uv run python -m playground.run tools_mcp.tool_overhead",
    "cost": "free - 0 model calls, every reading is a control request",
    "expect": "Six toolsets read before any prompt is sent, each showing its "
              "on-connect total, its settled total and the polls between them; "
              "then a straight-line fit giving cost per tool and fixed server "
              "overhead, checked against the rows it was not fitted on.",
    "learn": "A tool you never call is not free - its definition is resident "
             "for the whole session. And an instrument can return a clean, "
             "plausible, wrong number simply because it was asked too early, "
             "which is the more dangerous of the two lessons here.",
}

# WHY: a long description on purpose. Real tool descriptions are long - the
# official guidance is 3-4 sentences minimum - and measuring a five-word
# description would price a tool nobody would ship, then report it as typical.
DESCRIPTION = (
    "Perform one action against a support ticket in the ticketing system. Use "
    "this when the user asks to change the state of a specific ticket that they "
    "have identified by id. Do not use it to look a ticket up or to list "
    "tickets; it only writes. The action parameter selects which change is "
    "made, and the note is recorded on the ticket's audit trail verbatim."
)

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "ticket_id": {"type": "string", "description": "Ticket id, e.g. TCK-003."},
        "action": {"type": "string", "enum": ["close", "reopen", "escalate"],
                   "description": "Which state change to apply."},
        "note": {"type": "string", "description": "Audit-trail note, verbatim."},
    },
    "required": ["ticket_id", "action"],
    "additionalProperties": False,
}

# WHY: 1, 2, 4 and 8 rather than 1 and 8 alone. Two points define a line and
# cannot test one; the middle rows exist so the fit below can be checked against
# measurements it was not derived from.
COUNTS = [0, 1, 2, 4, 8]
PRESET: dict[str, Any] = {"type": "preset", "preset": "claude_code"}


def make_tool(index: int) -> Any:
    """One realistically-shaped tool. The handler is never reached."""
    async def handler(args: dict[str, Any]) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": "ok"}]}
    # WHY: @tool is a decorator factory, so calling it directly is how you build
    # tools in a loop. Eight decorated functions would measure the same thing and
    # hide the fact that a tool is just a value.
    return tool(f"ticket_action_{index}", DESCRIPTION, SCHEMA)(handler)


async def measure(label: str, config: dict[str, Any]) -> tuple[int, int, int]:
    options = ClaudeAgentOptions(
        # WHY: a fixed short system prompt in every arm. The claude_code preset
        # prompt is large and varies with the working directory, which would
        # swamp the one difference this file is trying to isolate.
        system_prompt="Answer in one short sentence.",
        **config,
    )
    async with ClaudeSDKClient(options=options) as client:
        first, usage, polls = await settle(client)
    named = ", ".join(
        f"{c['name']} {int(c['tokens']):,}{' DEFERRED' if c.get('isDeferred') else ''}"
        for c in sorted(usage["categories"], key=lambda c: -c["tokens"])
        # WHY: the two padding categories are dropped. They are large, identical
        # in every arm, and would bury the one category that moves.
        if c["tokens"] and c["name"] not in ("Free space", "Autocompact buffer")
    )
    total = int(usage["totalTokens"])
    print(f"  {label:<22}{first:>9,}{total:>9,}{polls:>7}   {named}")
    return first, total, polls


async def main() -> None:
    teach.banner(LESSON)
    print(f"  {'toolset':<22}{'connect':>9}{'settled':>9}{'polls':>7}   categories")

    mcp: dict[int, int] = {}
    first_seen: dict[int, int] = {}
    polls_seen: dict[int, int] = {}
    for count in COUNTS:
        servers = {} if not count else {
            "tk": create_sdk_mcp_server(
                name="tk", tools=[make_tool(i) for i in range(count)])}
        label = "no tools at all" if not count else f"{count} MCP tool(s)"
        first, total, polls = await measure(label,
                                            {"tools": [], "mcp_servers": servers})
        mcp[count], first_seen[count], polls_seen[count] = total, first, polls
    _, preset, _ = await measure("claude_code built-ins",
                                 {"tools": PRESET, "mcp_servers": {}})

    floor = mcp[0]
    lo, hi = COUNTS[1], COUNTS[-1]
    # WHY: the slope is fitted on the two extreme rows only, so the middle rows
    # stay independent and can falsify it. A fit using every point would always
    # look good and would prove nothing about linearity.
    slope = (mcp[hi] - mcp[lo]) // (hi - lo)
    overhead = mcp[lo] - floor - slope
    print(f"\n  per tool {slope:,} tokens, plus {overhead:,} fixed for the "
          f"server, fitted on the\n  {lo}- and {hi}-tool rows only. "
          f"Checked against the rest:")
    predicted = {n: floor + overhead + slope * n for n in COUNTS[1:]}
    for count, guess in predicted.items():
        print(f"    {count:>2} tools: predicted {guess:,}, "
              f"measured {mcp[count]:,}, off by {mcp[count] - guess:+,}")
    worst = max(abs(mcp[n] - predicted[n]) for n in predicted)

    print("\n--- what this run did NOT measure ---")
    print("  Nothing above includes a tool_use block, a tool_result block or the")
    print("  extra turn a real call costs: no prompt was sent. DOCUMENTED and")
    print("  unreachable from the Agent SDK - tool_choice any/tool costs about")
    print("  120 more system-prompt tokens per turn on Opus 5 than auto/none")
    print("  (406 vs 286), and ClaudeAgentOptions has no tool_choice at all.")

    teach.closing(
        LESSON,
        observed=[
            f"A session with no tools at all still rests at {floor:,} tokens, so "
            f"the floor is not zero and nothing here is measured against zero.",
            f"One tool of the shape above costs {slope:,} tokens every turn, "
            f"called or not. Fitted on two rows, it predicts the others to "
            f"within {worst:,} token(s): the cost is linear in the number of "
            f"tools, plus about {overhead:,} tokens for the server itself.",
            f"The claude_code built-in toolset rested at {preset:,}, "
            f"{preset - floor:+,} against the same floor - the harness's own "
            f"tools are a line item you did not choose and pay anyway. Its row "
            f"also names a DEFERRED category, listed but excluded from the "
            f"total: definitions that load on demand and cost nothing until "
            f"something needs them.",
            f"Every MCP row read {first_seen[hi]:,} on connect however many tools "
            f"it carried, taking {min(polls_seen.values())} to "
            f"{max(polls_seen.values())} polls to reach its real value - and "
            f"those counts move between runs, which is what makes this a race "
            f"and not a fixed number of steps you could hard-code.",
        ],
        naive="The obvious reading is 'tools are cheap, attach them all'. Two "
              "things argue otherwise. Tokens are not the cost that bites: "
              "tool-selection accuracy degrades as a toolset grows, the "
              "documented reason the tool search tool exists - unreachable here, "
              "so the only lever this repo has is not attaching the tool. Worse, "
              "compare the connect column with the settled column. The early "
              "reading is not an error, a warning, or a zero that looks wrong. "
              "It is a plausible, correctly formatted number a capacity estimate "
              "would have been built on, and it is what you get measuring the "
              "way anyone would measure. An instrument that reads low when asked "
              "early is worse than one that fails: nothing says ask again.",
    )


if __name__ == "__main__":
    asyncio.run(main())
