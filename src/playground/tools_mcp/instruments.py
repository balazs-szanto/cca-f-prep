"""
WHAT      The three measuring instruments the D4 demos use: a census of the
          content-block classes a run produced, the idle time between one tool
          handler returning and the next one starting, and a context reading
          polled until it stops moving.
WHY       These were extracted from the demos that use them, and the reason is
          the same reason all three exist. Each was written after its obvious
          version had already been tried and had returned a confident wrong or
          narrower answer - a plausible zero, a "no difference", a number taken
          before the thing being measured had arrived. Keeping them here gives
          each instrument room to explain what it does NOT answer, which is the
          part that matters and the first part trimmed when it lives inside a
          demo that is against its line cap.
DOMAIN    D2 Tool Design and MCP Integration
TRADEOFF  A shared module means a reader of one demo has to open a second file
          to see how its numbers were produced, and the indirection hides how
          small these functions are. Against that: when they lived inside the
          demos, the explanation of each one was the first thing squeezed out
          when the file hit its line cap, and in a study repo the explanation is
          the product.
ALTERNATIVE  Leave them inline in each demo, which is where they started. That
          keeps a demo readable top to bottom with no imports to chase, and it
          is what pushed both files against the cap and cost them the paragraphs
          this module now carries.

Makes no model call. Pure functions over data the demos have already collected.

A note that belongs to both functions. Neither one is a general-purpose
utility, and neither should be reached for by default. They exist because a
specific measurement was ambiguous, and each answers exactly one question. If
you are about to use one, the useful step is to write down what question you
are asking first, then check that it is the question the function answers.
"""
from __future__ import annotations

from typing import Any

from claude_agent_sdk import ClaudeSDKClient


async def settle(client: ClaudeSDKClient) -> tuple[int, dict[str, Any], int]:
    """Read the context breakdown, then poll until two readings agree.

    Returns the first reading's total, the settled reading, and the poll count.

    WHY POLL AT ALL, when one call returns a complete-looking answer. MEASURED
    2026-08-20: read immediately after connecting, a session with eight
    in-process MCP tools reported the same total as a session with none, and no
    `MCP tools` category at all. The tools were always going to be there; the
    reading had been taken before they were counted. The settling is a RACE, not
    a fixed number of steps - the poll counts differ between runs - so no
    hard-coded number of retries is correct either.

    The `polls > 1` guard below is load-bearing rather than defensive. On the
    first pass the reading usually still equals the on-connect value, so without
    it the loop would stop on the very number it exists to move past. That is
    not a hypothetical: it is what the first version of this function did, and
    it got 226 tokens right and 1,773 wrong in the same run.

    WHAT THIS DOES NOT ANSWER: why the reading lags. INFERRED, and unconfirmable
    from this repo, is lazy registration of in-process MCP servers. The
    behaviour is what is measured, and the rule follows from the behaviour
    alone: poll until it stops moving, then trust it.
    """
    first = await client.get_context_usage()
    previous, usage, polls = int(first["totalTokens"]), first, 0
    for polls in range(1, 7):
        # WHY: the return value is discarded. The call is here for its side
        # effect - it drives the MCP handshake forward - and is never printed,
        # because it describes whatever MCP servers the reader's machine has.
        await client.get_mcp_status()
        usage = await client.get_context_usage()
        current = int(usage["totalTokens"])
        if current == previous and polls > 1:
            break
        previous = current
    return int(first["totalTokens"]), usage, polls


def census(blocks: list[tuple[str, str]]) -> list[str]:
    """Collapse a block stream into `ClassName(name) xN` lines, in order seen.

    Takes (class_name, tool_name) pairs, where the class name is read from the
    SDK object with `type(block).__name__` rather than assigned by the caller.
    That is deliberate: a demo that labels the blocks itself can describe a
    distinction it never observed, which is exactly the mistake the first draft
    of where_code_runs.py made when it asserted a ServerToolUseBlock would
    appear and printed a KNOWN_ISSUE when one did not.

    WHAT THIS DOES NOT ANSWER: who executed the tool. MEASURED 2026-08-20, and
    now DOCUMENTED as well - a genuinely server-executed tool and a tool
    implemented in the calling process both arrive as `ToolUseBlock`. The census
    tells you the shape of the stream and nothing about where the work happened.
    For that, look at whether your own handler was invoked.
    """
    ordered: list[tuple[str, str]] = []
    counts: dict[tuple[str, str], int] = {}
    for item in blocks:
        if item not in counts:
            ordered.append(item)
        counts[item] = counts.get(item, 0) + 1
    return [f"{cls}{f'({name})' if name else ''} x{counts[(cls, name)]}"
            for cls, name in ordered]


def gaps(events: list[tuple[str, str, float]]) -> list[tuple[str, float]]:
    """Idle milliseconds between one handler returning and the next starting.

    Takes (name, "start" | "end", seconds) triples in the order they happened.

    WHY THIS RATHER THAN OVERLAP, which is the obvious instrument and the one
    tried first. Overlap answers "did two handlers run at the same moment",
    and in parallel_tools.py the answer was no in both arms - the independent
    question and the dependent one looked identical, and the demo read as a
    null result. The gap answers a different question: "was there room for a
    model round trip in between". Measured, the two arms differed by about a
    hundred to one, and the arms were not doing the same thing after all.

    The generalisation is the reason this docstring is longer than the function.
    A measurement that only reports the question you thought to ask is how a
    null result gets mistaken for no difference. Overlap was not wrong. It was
    answering something narrower than what was being asked, and it said so in
    the same confident format it would have used for a real finding.

    WHAT THIS DOES NOT ANSWER: whether the calls were REQUESTED together. A
    short gap is evidence that the second call was decided before the first
    result could have been read; it is not evidence about how the API framed
    the request. That distinction is left as INFERRED in parallel_tools.py and
    this repo cannot settle it.
    """
    ends = [(n, at) for n, kind, at in events if kind == "end"]
    starts = [(n, at) for n, kind, at in events if kind == "start"]
    return [(f"{ends[i - 1][0]} -> {name}", (at - ends[i - 1][1]) * 1000)
            for i, (name, at) in enumerate(starts[1:], start=1)]
