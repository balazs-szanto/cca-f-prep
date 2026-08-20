"""
WHAT      One classification task solved twice - as a fixed workflow your code
          drives and as an agent that drives itself - measured side by side.
WHY       "Agent" is not a maturity level you graduate to. The real choice is who
          owns control flow, and the measured gap usually settles it.
DOMAIN    D1 Agentic Architecture and Orchestration
TRADEOFF  The workflow buys reproducibility and a control flow you can read off
          the page, and can only do what you scripted: a ticket needing a lookup
          first gets classified wrong, confidently. It does NOT reliably buy
          cheapness. The agent absorbs inputs you did not anticipate, and costs
          you the ability to predict what it does.
ALTERNATIVE  A workflow with one agentic escape hatch - script the known path,
          hand off to an agent only when an input fails a precondition.

Model: claude-haiku-4-5, max_turns=3 on the agent; watch num_turns for truncation.
The cost comparison is not restated here on purpose - the closing block prints
the numbers from the run in front of you, and a paragraph quoting an older run
would be the first thing to go stale.
"""
import asyncio
import json
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions, ClaudeSDKError, ResultMessage, create_sdk_mcp_server, query, tool,
)

from playground import teach

MODEL = "claude-haiku-4-5"
URGENCIES = ["critical", "normal", "cosmetic"]

LESSON = {
    "domain": "D1 Agentic Architecture and Orchestration",
    "setup": "basics.check_auth passed. Read run_workflow() and run_agent() "
             "first and predict which column will be cheaper before you run it.",
    "run": "uv run python -m playground.run orchestration.workflow_vs_agent",
    "cost": "4 model calls - three for the workflow, one for the agent",
    "expect": "Two label lists that usually agree, then a table of api_calls, "
              "turns, latency, tokens, cache and cost with a column for each "
              "approach. The workflow column is the more expensive one.",
    "learn": "The choice is not workflow-or-agent, it is who owns control flow - "
             "and the bill is driven by how many separate calls you make, not by "
             "which of the two labels you attached to the design.",
}

TICKETS = [
    "Card declined at checkout, customer is on the phone now.",
    "Typo in the footer of the pricing page.",
    "All API requests have returned 500 since 09:00.",
]

# WHY: module-level capture. The tool handler runs inside the agent loop with no
# return path back to main(), so recording into a module global is the simplest
# way to observe what the model actually did. In real code this would be a queue
# or a database write - the point is that the handler's return value goes to the
# model, not to you.
AGENT_CALLS: list[dict[str, Any]] = []


def summarise(runs: list[ResultMessage]) -> dict[str, Any]:
    """Fold a list of run results into one comparable row of numbers."""
    # WHY: usage can be None on an errored run, so normalise before summing.
    usage = [r.usage or {} for r in runs]
    return {
        # WHY: api_calls and turns are different axes and both matter. Three calls
        # of one turn each and one call of three turns cost very different amounts
        # because each *call* re-sends the system prompt and tool schemas.
        "api_calls": len(runs),
        "turns": sum(r.num_turns for r in runs),
        # WHY: duration_api_ms, not duration_ms. The latter includes time your own
        # Python spent between messages, which is not what you are comparing.
        "api_ms": sum(r.duration_api_ms for r in runs),
        "in_tokens": sum(u.get("input_tokens", 0) for u in usage),
        # WHY: input_tokens counts only uncached input. Without these two the
        # workflow looks almost free on the input side, which it is not - a real
        # turn here reported input_tokens 10 alongside cache_read 11,200.
        "cache_write": sum(u.get("cache_creation_input_tokens", 0) for u in usage),
        "cache_read": sum(u.get("cache_read_input_tokens", 0) for u in usage),
        "out_tokens": sum(u.get("output_tokens", 0) for u in usage),
        # WHY: total_cost_usd is the SDK's own figure and is the only number here
        # that already accounts for cache pricing. Trust it over arithmetic on
        # the token counts above.
        "usd": round(sum(r.total_cost_usd or 0.0 for r in runs), 6),
    }


async def run_workflow() -> tuple[list[str], dict[str, Any]]:
    """Python owns the loop: one constrained call per ticket, then aggregate."""
    schema = {"type": "object", "required": ["urgency"], "additionalProperties": False,
              "properties": {"urgency": {"type": "string", "enum": URGENCIES}}}
    # WHY: 2, not 1, because max_turns=1 trips here even though this call has no
    # tools. The documentation describes the cap as counting tool-use round trips,
    # which predicts that a no-tool call should fit inside 1. MEASURED, it does
    # not: the output_format below consumes the turn. That conflict is unresolved
    # - the documented rule and the observation disagree, and this repo has not
    # established which description is incomplete.
    # Note what the SDK does at the limit: it yields a ResultMessage with subtype
    # error_max_turns AND THEN raises. Both, documented and intentional. Raising
    # the cap is the workaround; a try around the loop is the actual fix.
    options = ClaudeAgentOptions(
        model=MODEL, max_turns=2, output_format={"type": "json_schema", "schema": schema}
    )

    labels: list[str] = []
    runs: list[ResultMessage] = []
    # WHY: this for-loop is the entire difference between the two approaches. The
    # sequence, the retry policy and the aggregation all live in Python, where you
    # can unit-test them. Nothing about the job shape is visible to the model.
    for ticket in TICKETS:
        # WHY the try is INSIDE the for, not around it: a cap on ticket 2 should
        # cost you ticket 2, not tickets 2 and 3. Where you put the guard decides
        # how much of the batch a single failure takes with it, and that choice
        # is the workflow's real advantage over the agent - it is yours to make.
        try:
            async for message in query(prompt=f"Classify this ticket: {ticket}",
                                       options=options):
                if isinstance(message, ResultMessage):
                    runs.append(message)
                    raw = message.result
                    payload = json.loads(raw) if isinstance(raw, str) else (raw or {})
                    labels.append(payload.get("urgency", "?"))
        except ClaudeSDKError:
            labels.append("?")
    return labels, summarise(runs)


@tool("record", "Record the urgency of one ticket.",
      {"type": "object", "required": ["ticket_index", "urgency"],
       "properties": {"ticket_index": {"type": "integer"},
                      "urgency": {"type": "string", "enum": URGENCIES}}})
async def record(args: dict[str, Any]) -> dict[str, Any]:
    # WHY: ticket_index exists so the model must tell us which ticket it is
    # labelling. Without it the results arrive in whatever order the model chose
    # and cannot be aligned with TICKETS - a real hazard with parallel tool calls.
    AGENT_CALLS.append(args)
    return {"content": [{"type": "text", "text": "recorded"}]}


async def run_agent() -> tuple[list[str], dict[str, Any], str]:
    """The model owns the loop: one call, it decides how many tool calls to make."""
    options = ClaudeAgentOptions(
        model=MODEL, max_turns=3,
        mcp_servers={"tickets": create_sdk_mcp_server(name="tickets", tools=[record])},
        allowed_tools=["mcp__tickets__record"],
        # WHY: "do not summarise afterwards" keeps the comparison fair. Without
        # it the agent adds a closing paragraph the workflow never produces, and
        # the output token counts stop measuring the same work.
        system_prompt="Record every ticket with the tool. Do not summarise afterwards.",
    )
    # WHY: all three tickets in one prompt. This is the actual lever - the agent
    # pays the per-call overhead once. Send them one at a time and the agent's
    # advantage disappears, because you have rebuilt the workflow's cost shape.
    listing = "\n".join(f"{i}: {t}" for i, t in enumerate(TICKETS))
    runs: list[ResultMessage] = []
    try:
        async for message in query(prompt=f"Classify each ticket:\n{listing}",
                                   options=options):
            if isinstance(message, ResultMessage):
                runs.append(message)
    except ClaudeSDKError:
        # WHY: documented behaviour - on a limit, query() yields the ResultMessage
        # and THEN raises. Without this except the raise escapes and discards the
        # accounting we just collected. Catching it is not swallowing an error:
        # the subtype below is what reports the failure.
        pass

    # WHY: sort by index rather than trusting call order. The model may emit
    # several tool_use blocks in one turn, and their execution order is not
    # guaranteed to match the order it listed them.
    ordered = sorted(AGENT_CALLS, key=lambda c: c["ticket_index"])
    subtype = runs[-1].subtype if runs else "no-result"
    return [c["urgency"] for c in ordered], summarise(runs), subtype


async def main() -> None:
    teach.banner(LESSON)

    wf_labels, wf = await run_workflow()
    ag_labels, ag, ag_subtype = await run_agent()

    print(f"\nworkflow labels: {wf_labels}")
    print(f"agent labels   : {ag_labels}  [{ag_subtype}]")
    # WHY: the subtype, not a length comparison. A length check only catches a
    # truncation that happens to lose a label, and misses a run cut off after the
    # last tool call. MEASURED 2026-08-20 in error_taxonomy.py and again in
    # basics/tools.py: the SDK emits subtype 'error_max_turns' and then raises,
    # so this branch is reachable. It has not fired in THIS file.
    if ag_subtype == "error_max_turns":
        print("  agent hit the turn cap - the labels above are partial")

    print(f"\n{'metric':<12}{'workflow':>12}{'agent':>12}")
    for key in wf:
        print(f"{key:<12}{wf[key]:>12}{ag[key]:>12}")

    cheaper = "workflow" if wf["usd"] < ag["usd"] else "agent"
    teach.closing(
        LESSON,
        observed=[
            f"Both approaches produced labels: workflow {wf_labels}, agent "
            f"{ag_labels}. Quality is not what separates them here.",
            f"The workflow made {wf['api_calls']} API call(s) and the agent "
            f"{ag['api_calls']}, for {wf['turns']} and {ag['turns']} turns.",
            f"Cache read was {wf['cache_read']:,} tokens against "
            f"{ag['cache_read']:,} - each separate call re-sends the system "
            f"prompt and tool schemas, so the fixed cost is paid per call.",
            f"Total cost: workflow ${wf['usd']}, agent ${ag['usd']}. The "
            f"{cheaper} was cheaper on this run.",
        ],
        naive="The received wisdom is that a scripted workflow is the cheap, "
              "predictable option and an agent is the expensive, unpredictable "
              "one. The cost half of that is not what this measures. The "
              "workflow's three small calls each re-pay a fixed per-call "
              "overhead that dwarfs the actual classifying, so it lost on price "
              "while winning on predictability. Batch granularity is the lever, "
              "not the label - send the agent one ticket at a time and you "
              "rebuild the workflow's cost shape inside it.",
    )


if __name__ == "__main__":
    asyncio.run(main())
