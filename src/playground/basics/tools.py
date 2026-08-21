"""
WHAT      Define one tool in this Python process, expose it through an in-process
          MCP server, and give the agent no way to answer except by calling it.
WHY       This is the whole tool mechanism in one file: a schema, a function, a
          server, an allowlist. Every D4 demo is a variation on these four parts.
DOMAIN    D2 Tool Design and MCP Integration
TRADEOFF  An in-process server needs no transport, no versioning and no startup
          cost, and it is invisible to anything outside this program - no other
          client can reuse it, and no policy layer inspects it.
ALTERNATIVE  An external MCP server over stdio when a second client needs the
          same tools, or the tools are not written in Python. That trade, and the
          governance that comes with it, is tools_mcp/external_mcp.py.

Model: claude-haiku-4-5, max_turns=5.

Five, and the number has a history. This file originally set no cap at all, and
worked. Adding max_turns=3 to satisfy the repo's cost rule broke it immediately:
MEASURED 2026-08-20, the run ended error_max_turns having reported num_turns=4,
because (17 + 8) x 4 is two tool calls plus a final answer. Five is that
measurement plus headroom. The general lesson is worth more than the number: a
turn cap is a budget you size against the task, and sizing it by house style
rather than by measurement turns a working demo into a truncated one.

Do not try to size it from num_turns either. MEASURED seven times across five
files in this repo: num_turns routinely exceeds max_turns without erroring - 6
against a cap of 3 finishing `success`, 3 against a cap of 2, 5 against a cap of
3 - and this file is the one case where it stayed under, at 4 against a cap of 5.
The two are not counting the same thing, the gap is not a constant offset, and no
documentation this repo found explains it. Branch on `subtype == "error_max_turns"`,
never on arithmetic over num_turns. Recorded in docs/traps.md.
"""
import asyncio
from typing import Any

from claude_agent_sdk import (
    AssistantMessage, ClaudeAgentOptions, ClaudeSDKError, ResultMessage, TextBlock,
    create_sdk_mcp_server, query, tool,
)

from playground import teach

MODEL = "claude-haiku-4-5"

LESSON = {
    "domain": "D2 Tool Design and MCP Integration",
    "setup": "basics.check_auth passed. Read the four parts below before running: "
             "a schema, a function, a server, an allowlist entry.",
    "run": "uv run python -m playground.run basics.tools",
    "cost": "1 model call, four to five turns",
    "expect": "A short prose answer containing 100, then a line reporting four "
              "or so turns. The turn count above 1 is the evidence that the "
              "model left, called the tool, and came back.",
    "learn": "A tool reaches the model as four separate things that must all "
             "line up - schema, handler, server alias, allowlist entry - and "
             "getting the mcp__<alias>__<tool> name wrong removes the tool with "
             "no error at all, leaving the model to answer from its own head.",
}

# WHY: recorded so the closing block can say whether the tool was used, rather
# than inferring it from the turn count. They usually agree; when they disagree
# the interesting case is a model that answered correctly without the tool, which
# is exactly the failure the system prompt below is written to prevent.
CALLS: list[dict[str, Any]] = []


# WHY: the three arguments to @tool are name, description and input schema, and
# the model sees all three. The description is not documentation for you - it is
# the only prose the model gets about when to reach for this tool.
@tool(
    "calculate",
    "Perform basic arithmetic on two numbers.",
    {
        "type": "object",
        "properties": {
            "a":  {"type": "number"},
            "b":  {"type": "number"},
            # WHY: enum, not a free string. Without it the model will eventually
            # send "plus", "+" or "addition" and the else-branch below fires.
            "op": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
        },
        "required": ["a", "b", "op"],
    },
)
async def calculate(args: dict[str, Any]) -> dict[str, Any]:
    # WHY: tool handlers are async even when the work is synchronous. The SDK
    # awaits them inside the agent loop, so a blocking call here stalls the whole
    # run - push real I/O onto a thread or use an async client.
    CALLS.append(args)
    a, b, op = args["a"], args["b"], args["op"]
    if op == "add":          answer: float = a + b
    elif op == "subtract":   answer = a - b
    elif op == "multiply":   answer = a * b
    elif op == "divide":
        if b == 0:
            # WHY: a failed tool returns a normal result, it does not raise. The
            # model reads this text and can recover. Raising would propagate out
            # of the agent loop into your process and end the run. See
            # reliability/error_taxonomy.py for the full version of this rule.
            return {"content": [{"type": "text", "text": "Error: division by zero"}]}
        answer = a / b
    else:
        return {"content": [{"type": "text", "text": f"Unknown operation: {op}"}]}

    # WHY: the return shape is MCP's, not Python's - a dict with a "content" list
    # of typed blocks. Returning a bare number or string will not work.
    return {"content": [{"type": "text", "text": str(answer)}]}


# WHY: the server is created once at import time, not per call. It is a registry
# of tools plus a name; the name becomes part of every tool's identifier below.
calculator_server = create_sdk_mcp_server(name="calculator", tools=[calculate])


async def main() -> None:
    teach.banner(LESSON)

    options = ClaudeAgentOptions(
        model=MODEL,
        max_turns=5,
        # WHY: the dict key here is the server alias used in tool names. It does
        # not have to match the name= above, and when it does not, the alias wins.
        mcp_servers={"calculator": calculator_server},

        # WHY: the naming convention is mcp__<server-alias>__<tool-name>. Get a
        # segment wrong and the tool is simply absent - no error, the model just
        # never sees it and answers from its own head instead.
        allowed_tools=["mcp__calculator__calculate"],

        # WHY: belt and braces. The allowlist means this is the only tool
        # available, but "available" is not "used" - a model can happily do
        # arithmetic in its head. The prompt closes that gap. Compare with
        # tools_mcp/permission_gate.py, where the gate is the real control.
        system_prompt=(
            "You are a math assistant. "
            "You MUST call the `calculate` tool for every arithmetic step. "
            "Never compute a number yourself."
        ),
    )

    result: ResultMessage | None = None
    # WHY this try, in the file that is supposed to be the gentle introduction:
    # because hitting max_turns yields the ResultMessage and THEN raises, and the
    # raise takes the closing block with it. MEASURED 2026-08-20 right here - the
    # cap was one turn too low, the run printed [error_max_turns] 4 turns, and
    # then the process died before it could explain itself. Catching this is not
    # hiding an error; the subtype below is what reports it.
    try:
        async for message in query(prompt="What is (17 + 8) x 4?", options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text, end="", flush=True)
            elif isinstance(message, ResultMessage):
                # WHY: num_turns above 1 means the model called the tool, read the
                # result, and came back. That round trip is the agent loop, and it
                # is what you pay for versus a single completion.
                result = message
                print(f"\n\n[{message.subtype}] {message.num_turns} turns")
    except ClaudeSDKError as exc:
        print(f"\n\nraised after the result: {type(exc).__name__}")

    if result is None:
        raise RuntimeError("The stream ended without a ResultMessage.")

    teach.closing(
        LESSON,
        observed=[
            f"The tool handler ran {len(CALLS)} time(s), with arguments {CALLS}. "
            f"Those dicts were built by the model, validated against the schema, "
            f"and handed to a Python function in this process.",
            f"The run took {result.num_turns} turns and ended "
            f"{result.subtype!r}. One turn would have meant the model answered "
            f"without ever leaving; every turn past the first is a tool result "
            f"being read and reasoned about - and each one is billed.",
            f"The op field only ever held a value from the enum, because that is "
            f"the one part of the schema the model cannot argue with.",
        ],
        naive="It is tempting to read allowed_tools as the thing that makes the "
              "model use the tool. It is not - it only decides what may run "
              "without asking. A model handed a calculator will happily do the "
              "arithmetic in its head and never call it, which is why the system "
              "prompt above says MUST. Availability is not usage, and the two "
              "are configured in completely different places.",
    )


asyncio.run(main())
