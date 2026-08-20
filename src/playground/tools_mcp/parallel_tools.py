"""
WHAT      Two questions of identical size, one needing two independent lookups
          and one needing two where the second's input is the first's output.
          Every call is stamped on arrival and return, so the shape of the
          request and of the execution can be compared - and here they disagree.
WHY       "Claude calls tools in parallel" is usually repeated as a performance
          fact and almost never as a design constraint. It is the second: it
          decides whether your handlers can assume they run alone, whether two
          writes can interleave, and whether an ordering bug in your tools is
          reachable at all.
DOMAIN    D4 Tool Design and MCP Integration
TRADEOFF  Parallel calls cut latency and remove your ability to reason about
          order. Independent read-only lookups are safe to overlap; anything
          with shared state or side effects is now a concurrency problem you did
          not write and cannot see from the prompt.
ALTERNATIVE  Collapse the pair into one tool doing both lookups. One call, no
          interleaving, order decided by you in Python - and a tool that is
          harder to describe, harder to reuse and does two things.

Model: claude-haiku-4-5, two runs, max_turns=6.

THE RESULT, MEASURED 2026-08-20, is null at the level this file set out to
measure. No AssistantMessage in either arm carried more than one ToolUseBlock:
both reported [1, 1] and both finished in 3 turns. On the block stream the
independent question and the dependent one are the same shape.

The clock separates them by a factor near a hundred. In the independent arm the
second handler started 15 ms after the first returned; in the dependent arm,
1,285 ms after. A model round trip is not 15 ms - the dependent arm shows what
one costs - so the second call was decided before the first result was read.

INFERRED and unsettleable from here: the likeliest reading is that the
independent pair WAS requested in one assistant response and the SDK delivered
the blocks as two AssistantMessage objects, in which case the grouping below
measures the SDK's message framing rather than the model. What is known: grouping
says no parallel request, timing says the arms differ, and timing is the harder
number to explain away.

DELIBERATELY NOT DONE. The documentation
<https://platform.claude.com/docs/en/agents-and-tools/tool-use/parallel-tool-use>
fetched 2026-08-20 says parallel calling is on by default for Claude 4 and later,
and that prompting raises the rate further - it offers a ready-made
`<use_parallel_tool_calls>` system-prompt block for exactly that. That lever is
not pulled here. Both arms get the same short neutral prompt, so what is measured
is DEFAULT behaviour, and a demo that prompted for parallel calls and then
reported parallel calls would have measured the prompt rather than the model.

NOT REACHABLE FROM HERE. The same page documents `disable_parallel_tool_use`,
which lives inside the `tool_choice` object on a Messages API request and caps
the model at one tool call per response. ClaudeAgentOptions has no `tool_choice`,
so the behaviour below is observable and the switch that governs it is not -
which also means this file cannot turn parallelism off to check its own
reasoning against a controlled negative. See docs/tool-surface.md.

The 250 ms sleep in each handler is instrumentation: without it they return in
under a millisecond and no interval below is resolvable.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from claude_agent_sdk import (
    AssistantMessage, ClaudeAgentOptions, ClaudeSDKError, ResultMessage,
    create_sdk_mcp_server, query, tool,
)

from playground import teach
from playground.tools_mcp.instruments import gaps

MODEL = "claude-haiku-4-5"

LESSON = {
    "domain": "D4 Tool Design and MCP Integration",
    "setup": "basics.check_auth passed. Read the two prompts below and decide, "
             "before running, which one COULD be answered with two calls at "
             "once and which one could not.",
    "run": "uv run python -m playground.run tools_mcp.parallel_tools",
    "cost": "2 model calls, one per arm",
    "expect": "Per arm: tool names grouped by the assistant turn that asked for "
              "them, the handler timeline, and the gap between consecutive "
              "calls. MEASURED, the groupings came out identical and the gaps "
              "did not - by roughly a hundred to one.",
    "learn": "Whether two tool calls can overlap is a property of the QUESTION, "
             "not of the tools or the model - and check more than one signal "
             "when you look: the grouping and the clock disagreed here, and "
             "only the clock told the arms apart.",
}

# WHY: monotonic, not wall time. The only quantity that matters is an interval
# between two events in one process, and a wall clock can move.
START = time.monotonic()
# WHY: appended from inside each handler on start and on end. This records what
# actually ran when; the block stream records what was ASKED for, and this file
# exists because those turned out to be different.
TIMELINE: list[tuple[str, str, float]] = []


async def timed(name: str, payload: str) -> dict[str, Any]:
    """Body shared by every tool below: stamp, pause, stamp, answer."""
    TIMELINE.append((name, "start", time.monotonic() - START))
    # WHY: 250 ms is instrumentation - long enough to resolve an interval, short
    # enough not to change what the model decides to do.
    await asyncio.sleep(0.25)
    TIMELINE.append((name, "end", time.monotonic() - START))
    return {"content": [{"type": "text", "text": payload}]}


CITY = {"type": "object", "required": ["city"],
        "properties": {"city": {"type": "string", "description": "City name."}}}


@tool("get_weather", "Current weather for one city.", CITY)
async def get_weather(args: dict[str, Any]) -> dict[str, Any]:
    return await timed("get_weather", "17 degrees Celsius, light rain")


@tool("get_timezone", "IANA timezone for one city.", CITY)
async def get_timezone(args: dict[str, Any]) -> dict[str, Any]:
    return await timed("get_timezone", "Asia/Tokyo, UTC+9")


@tool("get_order", "Look up one order by id. Returns the customer id on it.",
      {"type": "object", "required": ["order_id"],
       "properties": {"order_id": {"type": "string", "description": "e.g. ORD-17."}}})
async def get_order(args: dict[str, Any]) -> dict[str, Any]:
    # WHY: the returned customer id is the whole point. It is absent from the
    # prompt, so the second tool cannot be called until this one has answered -
    # the dependency lives in the DATA, the only place it can.
    return await timed("get_order", '{"order_id": "ORD-17", "customer_id": "CUS-88"}')


@tool("get_customer", "Look up one customer by id.",
      {"type": "object", "required": ["customer_id"],
       "properties": {"customer_id": {"type": "string", "description": "e.g. CUS-88."}}})
async def get_customer(args: dict[str, Any]) -> dict[str, Any]:
    return await timed("get_customer", '{"customer_id": "CUS-88", "name": "R. Moore"}')


ARMS = [
    ("independent", "For Tokyo, tell me the current weather and the timezone.",
     [get_weather, get_timezone]),
    ("dependent", "Who placed order ORD-17? Give me the customer's name.",
     [get_order, get_customer]),
]

# WHY: identical in both arms, and deliberately silent about parallelism. See
# DELIBERATELY NOT DONE in the docstring - a nudge here would measure the nudge.
SYSTEM = "Use the tools to answer. Reply in one sentence."


async def run(arm: str, prompt: str, tools: list[Any]) -> tuple[list[list[str]], int]:
    """Return the tool names grouped by the assistant turn that asked for them."""
    options = ClaudeAgentOptions(
        model=MODEL, max_turns=6, tools=[], system_prompt=SYSTEM,
        mcp_servers={arm: create_sdk_mcp_server(name=arm, tools=tools)},
        allowed_tools=[f"mcp__{arm}__{t.name}" for t in tools],
    )
    turns_asking: list[list[str]] = []
    total = 0
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                names = [b.name.split("__")[-1] for b in message.content
                         if type(b).__name__ == "ToolUseBlock"]
                if names:
                    turns_asking.append(names)
            if isinstance(message, ResultMessage):
                total = message.num_turns
    except ClaudeSDKError as exc:
        # WHY: caught so the second arm still runs. One column reads as a result
        # rather than as a missing measurement.
        print(f"  {arm} raised {type(exc).__name__}")
    return turns_asking, total


async def main() -> None:
    teach.banner(LESSON)

    seen: dict[str, tuple[list[list[str]], int, list[tuple[str, float]]]] = {}
    for arm, prompt, tools in ARMS:
        TIMELINE.clear()
        print(f"\n--- {arm} arm ---\n  prompt: {prompt}")
        turns_asking, total = await run(arm, prompt, tools)
        for index, names in enumerate(turns_asking, start=1):
            print(f"  assistant turn {index} asked for {len(names)}: "
                  f"{', '.join(names)}")
        print(f"  {total} turn(s) in all. Handler timeline, seconds from start:")
        for name, kind, at in TIMELINE:
            print(f"    {at:7.3f}  {name} {kind}")
        measured = gaps(TIMELINE)
        for label, ms in measured:
            print(f"  GAP {label}: {ms:,.0f} ms idle")
        seen[arm] = (turns_asking, total, measured)

    ind_turns, ind_total, ind_gaps = seen["independent"]
    dep_turns, dep_total, dep_gaps = seen["dependent"]
    ind_ms, dep_ms = (g[0][1] if g else 0.0 for g in (ind_gaps, dep_gaps))
    ratio = dep_ms / ind_ms if ind_ms else 0.0

    teach.closing(
        LESSON,
        observed=[
            f"By block grouping the arms are identical: independent asked "
            f"{[len(n) for n in ind_turns]}, dependent {[len(n) for n in dep_turns]}, "
            f"finishing in {ind_total} and {dep_total} turns. No assistant "
            f"message carried two tool calls, so on this signal alone it is a "
            f"null result.",
            f"By the clock they are not identical at all: {ind_ms:,.0f} ms idle "
            f"between the independent pair against {dep_ms:,.0f} ms between the "
            f"dependent pair, about {ratio:,.0f} to 1.",
            f"The dependent gap is what a model round trip costs here and the "
            f"independent gap cannot contain one, so the second call was decided "
            f"before the first result was read. Whether the blocks arrived "
            f"together is INFERRED - see the docstring.",
        ],
        naive="The instinct is that parallelism is a capability you switch on, "
              "so a null result means the model failed. Two corrections. Look at "
              "the dependent arm: no model and no setting could have "
              "parallelised it, because the second call's argument did not exist "
              "until the first returned. Independence is a property of the "
              "question, and that is the direction worth reasoning in, because "
              "it is the one you control. Second, about measurement: the "
              "grouping said 'no difference' and was not wrong, it answered a "
              "narrower question than the one asked. The clock was in the same "
              "run, cost nothing, and disagreed. One signal reporting no "
              "difference is not evidence of no difference.",
    )


if __name__ == "__main__":
    asyncio.run(main())
