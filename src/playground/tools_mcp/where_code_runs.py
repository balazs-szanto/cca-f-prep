"""
WHAT      One question asked twice: once against a tool whose Python function
          lives in this file, once against a tool nobody here implements. Every
          content block is printed with its SDK class name, and the two streams
          turn out to be indistinguishable by type.
WHY       The most load-bearing idea in the tool-use documentation is WHERE the
          code runs: client tools produce a request your application must
          answer, server tools are executed for you. Latency, cost, trust and
          what you can debug all follow from that line. This file went looking
          for it in the SDK's own types and found it is not there.
DOMAIN    D4 Tool Design and MCP Integration
TRADEOFF  The local tool answers instantly, costs nothing beyond the tokens its
          definition and result occupy, and is exactly as correct as whoever
          last edited PINNED below. The built-in is current and cited, and in
          exchange you cannot see its code, cannot test it offline, and pay per
          search. Neither is the safe choice; they fail in opposite directions.
ALTERNATIVE  Wrap a search API in your own MCP tool. You get the freshness and
          keep the code, and you have taken on a rate limit, a credential, an
          error taxonomy and a parsing job that were somebody else's problem.

Model: claude-haiku-4-5, two runs. max_turns=6 in the search arm rather than the
repo's usual 3, because searching, reading and answering are three turns; the
local arm is capped at 3 and settled in 2.

THE FINDING, and it is not the one this file was written to show. MEASURED twice,
2026-08-20: the search arm called a tool, fetched live pages, cited its sources
and returned a version newer than PINNED - and every block it produced came back
as `ToolUseBlock(WebSearch)`, the same class as this file's own
`ToolUseBlock(mcp__rel__lookup_release)`. No `ServerToolUseBlock` appeared, though
the SDK defines that class and its `ServerToolName` literal names `web_search`.
The first draft asserted one would appear and printed a KNOWN_ISSUE when it did
not; the assertion was wrong, not the environment, and the assertion is what got
rewritten.

WHAT THAT MEANT WAS ITSELF GOT WRONG ONCE, and the correction is why this file
can claim what it claims. An earlier version of this docstring recorded an
INFERRED guess: that `WebSearch` was implemented and executed by the CLI, which
would have made both arms client-side and this comparison a comparison of two
client tools. That guess is FALSE, and the question is now DOCUMENTED rather
than open. Claude Code's own tools reference says WebSearch "runs a query
against Anthropic's web search backend", links that phrase to the Messages API
web search tool, describes a server-side loop of up to eight backend searches
per call, exposes that tool's own `allowed_domains` and `blocked_domains` with
its own mutual-exclusion rule, and states that Amazon Bedrock "doesn't expose
the server-side web search tool". The search arm below really did execute on
Anthropic's infrastructure. Full quotations, URLs and fetch dates are in
docs/tool-surface.md, finding 1, which is where the evidence lives so that this
file can stay a demo.

So the comparison is sound, and the conclusion is stronger than a guess would
have allowed: one arm was server-executed and the other ran in this process,
established from documentation rather than from a hunch, and the SDK reported
`ToolUseBlock` for both. From the Agent SDK you cannot tell who executed a tool
by looking at the block - not because the distinction is unclear, but because it
is real and the block type does not carry it. The only thing separating the two
arms is that in one of them a function in this repo ran, and we know that only
because we watched it run.

A NEAR MISS, recorded because this file survived on a choice made for the wrong
reason. Had it used `WebFetch`, the framing would have collapsed: that built-in
fetches the page itself, converts and summarises it locally with a small fast
model, sets its own `User-Agent`, and caches responses on your machine. Nothing
in it is server-executed. Two adjacent built-ins with near-identical names sit
on opposite sides of the line this demo is about, and it picked the right one by
luck. Also documented there: a session caps at 200 WebSearch calls, and a capped
call "appears in the conversation as a search that did nothing" - no error, no
exception, nothing in the block stream. That is the same silent shape as the
declined-tool trap in docs/traps.md, and it is why main() asserts that a tool
was called at all rather than trusting the arm to have worked.
"""
from __future__ import annotations

import asyncio
from typing import Any

from claude_agent_sdk import (
    AssistantMessage, ClaudeAgentOptions, ClaudeSDKError, ResultMessage,
    create_sdk_mcp_server, query, tool,
)

from playground import teach
from playground.tools_mcp.instruments import census

MODEL = "claude-haiku-4-5"

LESSON = {
    "domain": "D4 Tool Design and MCP Integration",
    "setup": "basics.check_auth passed. Before running, look at PINNED below "
             "and decide what the local arm CAN say, then ask yourself how the "
             "other arm could possibly answer the same question.",
    "run": "uv run python -m playground.run tools_mcp.where_code_runs",
    "cost": "2 model calls, one per arm, plus web searches in the second",
    "expect": "The same question twice, then a census of each arm's content "
              "blocks. Both call a tool and both report ToolUseBlock; only one "
              "prints a line from inside this file, and MEASURED, neither "
              "produces a ServerToolUseBlock.",
    "learn": "Ask of every tool: whose process runs this? You cannot answer it "
             "from the block stream - both arms below look the same there. You "
             "answer it from whether your own code was asked to do anything, "
             "and that answer decides who owns the failure and the freshness.",
}

QUESTION = (
    "What is the current stable release version of Python 3? "
    "Use a tool to find out rather than answering from memory, and say in one "
    "sentence where the number came from."
)

# WHY: a deliberately stale-able constant, and the point of the local arm. This
# value is only as correct as the last person to edit this line, which is the
# defining property of every tool you implement yourself.
PINNED = {"python": "3.12.4, pinned into this file by hand on 2026-08-20"}

# WHY: only the local arm can ever fill this - there is no handler of ours in the
# built-in arm to fill it from. An empty list on that side is not a bug, it is
# the measurement, and the ONLY signal here that separates the two arms.
HANDLED: dict[str, list[dict[str, Any]]] = {"local": [], "built-in": []}


@tool("lookup_release", "Look up the current stable release of a named project.",
      {"type": "object", "required": ["project"],
       "properties": {"project": {"type": "string",
                                  "description": "Project name, e.g. python."}}})
async def lookup_release(args: dict[str, Any]) -> dict[str, Any]:
    HANDLED["local"].append(args)
    # WHY: this print is the proof. It is the only line in the file that runs in
    # response to the model's request; if it appears, our process did the work.
    print(f"    [our process] lookup_release{args} executing here, in this file")
    answer = PINNED.get(str(args.get("project", "")).lower(), "unknown project")
    return {"content": [{"type": "text", "text": answer}]}


async def run(arm: str, options: ClaudeAgentOptions) -> tuple[list[str], str, int]:
    """Run one arm and return its block census, its answer and its turn count."""
    blocks: list[tuple[str, str]] = []
    answer, turns = "", 0
    print(f"\n--- {arm} arm ---")
    try:
        async for message in query(prompt=QUESTION, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    # WHY: the SDK's own class name, not a label of ours. Naming
                    # the blocks ourselves would let this file describe a
                    # distinction it never observed - its first draft's mistake.
                    blocks.append((type(block).__name__,
                                   str(getattr(block, "name", "") or "")))
            if isinstance(message, ResultMessage):
                answer, turns = (message.result or "").strip(), message.num_turns
                if message.is_error:
                    print(f"    run ended in error: {message.subtype}")
    except ClaudeSDKError as exc:
        # WHY: caught so the second arm still runs. A comparison with one column
        # reads as a result rather than as a missing measurement.
        answer = f"(raised {type(exc).__name__})"
    return census(blocks), answer, turns


LOCAL = ClaudeAgentOptions(
    model=MODEL, max_turns=3,
    # WHY: tools=[] removes every Claude Code built-in, so the ONLY tool here is
    # the one above. Without it the model could reach WebSearch on its own and
    # both arms would quietly become the same experiment.
    tools=[],
    mcp_servers={"rel": create_sdk_mcp_server(name="rel", tools=[lookup_release])},
    allowed_tools=["mcp__rel__lookup_release"],
    system_prompt="Use the tool. Answer in one sentence.",
)

BUILTIN = ClaudeAgentOptions(
    model=MODEL, max_turns=6,
    # WHY: the mirror image - one built-in tool, no MCP server, and nothing in
    # this repo that could execute it. No request to run anything reaches us.
    tools=["WebSearch"],
    allowed_tools=["WebSearch"],
    system_prompt="Use the tool. Answer in one sentence.",
)

# KNOWN_ISSUE text, kept as a constant so the runtime block and the comment on
# the failing line cannot drift apart. See the assertion at the end of main().
NO_TOOL_CALLED = (
    "The built-in arm called no tool at all, so there is no second column to "
    "compare against. Web search reaches the network, and whether a session may "
    "use it depends on the account and on organisation settings this repo cannot "
    "inspect - nothing in the code above can fix or work around that. The local "
    "arm's result is printed above and stands on its own; the comparison this "
    "file exists to draw does not. To find out whether search is available to "
    "you, ask an interactive Claude Code session to search for anything."
)


async def main() -> None:
    teach.banner(LESSON)
    print(f"Question, identical in both arms:\n  {QUESTION}")

    local_blocks, local_answer, local_turns = await run("local", LOCAL)
    builtin_blocks, builtin_answer, builtin_turns = await run("built-in", BUILTIN)

    print("\n--- block census, in the order the blocks arrived ---")
    for arm, blocks, turns in (("local", local_blocks, local_turns),
                               ("built-in", builtin_blocks, builtin_turns)):
        print(f"  {arm:<10}{turns} turn(s)")
        for line in blocks:
            print(f"            {line}")

    # WHY: its own section, restored after being folded into the census above to
    # save two lines. It is not a detail of the census - it is the ONLY signal in
    # this file that separates the two arms, and the census is the thing it
    # disagrees with. Printing it as a census footnote made the weaker evidence
    # look like the headline.
    print("\n--- what our own handler saw, which is the whole comparison ---")
    for arm in ("local", "built-in"):
        print(f"  {arm:<10}{HANDLED[arm] or 'nothing - no code of ours ran here'}")

    print("\n--- the answers, the least interesting part ---")
    print(f"  local     {local_answer}\n  built-in  {builtin_answer}")

    # WHY: the assertion is on "did it call a tool", not on which class arrived.
    # The first draft asserted ServerToolUseBlock, was wrong, and reported a
    # KNOWN_ISSUE for a run that worked - worse than having no check at all.
    if not any("ToolUse" in line for line in builtin_blocks):
        # KNOWN ISSUE: the built-in arm called no tool at all, so there is no
        # second column to compare against. Web search reaches the network, and
        # whether a session may use it depends on the account and on organisation
        # settings this repo cannot inspect - nothing in the code above can fix
        # or work around that. The local arm's result is printed above and stands
        # on its own; the comparison this file exists to draw does not. To find
        # out whether search is available to you, ask an interactive Claude Code
        # session to search for anything.
        teach.known_issue(LESSON, NO_TOOL_CALLED)

    server_seen = [line for line in builtin_blocks if "ServerTool" in line]
    teach.closing(
        LESSON,
        observed=[
            f"local produced {', '.join(local_blocks)}, and the line printed from "
            f"inside lookup_release is this repo's own process doing the work. "
            f"HANDLED['local'] holds {HANDLED['local']}.",
            f"built-in produced {', '.join(builtin_blocks)}, and HANDLED"
            f"['built-in'] is still {HANDLED['built-in']}: nothing here ran, "
            f"nothing was asked of us, we returned no result to anyone.",
            f"ServerToolUseBlock appeared {len(server_seen)} time(s), though the "
            f"class exists in the SDK and its ServerToolName literal names "
            f"web_search: both arms report the same block class for tools "
            f"executed in different processes.",
            f"The local answer is as old as this file; the built-in answer was "
            f"fetched during the run, in {builtin_turns} turns against "
            f"{local_turns}.",
        ],
        naive="The documentation draws a hard line between client and server "
              "tools, so the obvious expectation is that the SDK draws it too - "
              "different block types, an obvious seam. Look at the census. Both "
              "arms report ToolUseBlock, and the only thing separating them is a "
              "print statement we put inside our own handler. The line is real, "
              "and it is the most important line in tool design, but it is not "
              "in the message stream: you find it by knowing which tools you "
              "implemented. The consequence is that can_use_tool and "
              "permission_gate.py can only intercept what is asked of you - by "
              "the time a built-in's result arrives, the work is done.",
    )


if __name__ == "__main__":
    asyncio.run(main())
