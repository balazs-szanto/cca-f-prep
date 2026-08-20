"""
WHAT      The same summarising job run inline and then delegated to a subagent,
          with the delegation overhead measured rather than assumed.
WHY       A subagent's real product is a clean context window: it reads the noisy
          material and returns only a conclusion, so the parent never pays for
          the intermediate tokens. That is worth a lot when the sub-task reads a
          lot, and worth nothing when it does not.
DOMAIN    D1 Agentic Architecture and Orchestration
TRADEOFF  Delegation costs a round trip, a second system prompt, and a context
          the parent cannot see. It buys context isolation and a narrower tool
          surface. On a small task the overhead dominates - this file is built to
          show that, so expect delegation to look worse here. That is the lesson,
          not a bug.
ALTERNATIVE  Keep it inline until a sub-task's intermediate output is both large
          and disposable - a log trawl, a many-file search, a scrape. That is the
          point where a fresh context window starts paying for itself.

Model: claude-haiku-4-5 for both parent and subagent, max_turns=3.

Measured once while writing this: delegation doubled the turns and the output
tokens, added ~60% latency, and cost ~1.75x. Your numbers will differ; the
direction is the point.
"""
import asyncio
from typing import Any

from claude_agent_sdk import (
    AgentDefinition, ClaudeAgentOptions, ClaudeSDKError, ResultMessage, query,
)

from playground import teach

MODEL = "claude-haiku-4-5"

LESSON = {
    "domain": "D1 Agentic Architecture and Orchestration",
    "setup": "basics.check_auth passed. Read NOTES below first - three one-line "
             "notes is the whole reason this demo comes out the way it does.",
    "run": "uv run python -m playground.run orchestration.subagent",
    "cost": "2 model calls, the second of which fans out to a subagent",
    "expect": "A four-column table - inline, delegated, and the delta between "
              "them - for turns, latency, tokens and cost. Expect every delta to "
              "be positive, meaning delegation cost more on all four axes.",
    "learn": "A subagent's product is a clean context window, so it pays for "
             "itself only when the sub-task reads something large and "
             "disposable; on a small task you pay a round trip and a second "
             "system prompt for isolation you had no use for.",
}

# WHY: three short notes, deliberately. The whole argument of this file is that
# delegation is priced per hand-off, not per unit of work - so the work is kept
# tiny to make the fixed cost visible. Make these notes 200 lines each and the
# numbers invert, which is exactly the threshold you are trying to develop a feel
# for.
NOTES = [
    "2.1 adds retry on transient socket errors and drops Python 3.9 support.",
    "2.2 rewrites the config loader; env vars now beat the config file.",
    "2.3 fixes a leak in the connection pool that surfaced after ~6h uptime.",
]

TASK = "Summarise each release note in one sentence:\n" + "\n".join(
    f"{i}: {n}" for i, n in enumerate(NOTES)
)


def summarise(runs: list[ResultMessage]) -> dict[str, Any]:
    usage = [r.usage or {} for r in runs]
    return {
        # WHY: turns is the delegation tax made visible. A hand-off is at minimum
        # one extra turn - the parent must call Task, then read what came back.
        "turns": sum(r.num_turns for r in runs),
        "api_ms": sum(r.duration_api_ms for r in runs),
        "in_tokens": sum(u.get("input_tokens", 0) for u in usage),
        # WHY: out_tokens roughly doubles under delegation because two models
        # write prose - the subagent produces the summaries, the parent then
        # reports them. That second write is pure overhead on a task this size.
        "out_tokens": sum(u.get("output_tokens", 0) for u in usage),
        "usd": round(sum(r.total_cost_usd or 0.0 for r in runs), 6),
    }


async def collect(prompt: str, options: ClaudeAgentOptions) -> dict[str, Any]:
    """Run one query to completion and keep only the result messages."""
    # WHY: subagent activity does not surface as separate ResultMessages. The
    # parent's single result already accounts for the child's usage, which is why
    # summing over this list is a fair comparison rather than an undercount.
    runs: list[ResultMessage] = []
    # WHY the try: a cap yields the ResultMessage and then raises, and this
    # function's entire job is to collect those messages. Without the guard the
    # delegated arm - the one more likely to hit a cap, because it has further
    # to go - would take the whole comparison down with it.
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                runs.append(message)
    except ClaudeSDKError as exc:
        print(f"  raised after the result: {type(exc).__name__}")
    return summarise(runs)


async def run_inline() -> dict[str, Any]:
    options = ClaudeAgentOptions(
        model=MODEL, max_turns=3, system_prompt="Be terse. One sentence per note."
    )
    return await collect(TASK, options)


async def run_delegated() -> dict[str, Any]:
    subagent = AgentDefinition(
        # WHY: description is not a comment - it is how the parent decides whether
        # this subagent fits the job. Vague descriptions produce delegation to the
        # wrong specialist, or no delegation at all.
        description="Summarises release notes into one sentence each.",
        # WHY: the subagent gets its own system prompt and its own fresh context.
        # It cannot see the parent's conversation, so anything it needs must be in
        # this prompt or in the task text the parent sends it.
        prompt="You summarise release notes. Reply with one sentence per note, no preamble.",
        # WHY: an empty tool list is the point of a subagent, not an oversight.
        # A subagent that inherits every tool inherits every way to go wrong, and
        # you lose the narrow blast radius that justified the hand-off.
        tools=[],
        # WHY: pinned separately from the parent. A cheap worker under an
        # expensive planner is the main cost lever in multi-agent designs - the
        # parent reasons, the subagent grinds.
        model=MODEL,
        maxTurns=2,
    )
    options = ClaudeAgentOptions(
        model=MODEL,
        max_turns=3,
        # WHY: agents is a registry keyed by name. Defining one does not invoke
        # it; the parent chooses, which is why the system prompt below has to be
        # explicit or the parent will just do the work itself.
        agents={"summariser": subagent},
        # WHY: Task is the built-in tool the parent uses to hand work to a
        # subagent. Without it in the allowlist the definition above is inert and
        # the run silently degrades into the inline case.
        allowed_tools=["Task"],
        system_prompt=(
            "Delegate the summarising to the 'summariser' subagent using the Task "
            "tool. Report what it returns. Do not summarise anything yourself."
        ),
    )
    return await collect(TASK, options)


async def main() -> None:
    teach.banner(LESSON)

    inline = await run_inline()
    delegated = await run_delegated()

    print(f"\n{'metric':<12}{'inline':>12}{'delegated':>12}{'delta':>12}")
    deltas: dict[str, Any] = {}
    for key in inline:
        a, b = inline[key], delegated[key]
        deltas[key] = round(b - a, 6) if isinstance(a, float) else b - a
        print(f"{key:<12}{a:>12}{b:>12}{deltas[key]:>12}")

    worse = [k for k, v in deltas.items() if v > 0]
    teach.closing(
        LESSON,
        observed=[
            f"Delegation was more expensive on {len(worse)} of "
            f"{len(deltas)} metrics: {', '.join(worse) if worse else 'none'}.",
            f"Turns went from {inline['turns']} to {delegated['turns']}. A "
            f"hand-off is at minimum one extra turn: the parent calls Task, then "
            f"has to read what came back.",
            f"Output tokens went from {inline['out_tokens']:,} to "
            f"{delegated['out_tokens']:,}, because two models wrote prose - the "
            f"subagent produced the summaries and the parent reported them.",
            f"Cost went from ${inline['usd']} to ${delegated['usd']}, a delta of "
            f"${deltas['usd']}. That is the price of the isolation.",
        ],
        naive="Delegation reads like an optimisation: give the small job to a "
              "cheap specialist and keep the parent free. What you actually buy "
              "is a fresh, separate context window - and here there was nothing "
              "to keep out of the parent's. Three one-line notes are not noise. "
              "The right question before delegating is never 'is this a "
              "different kind of work' but 'how much would the parent have had "
              "to read, and can it be thrown away afterwards'. Make NOTES two "
              "hundred lines each and this table inverts.",
    )


if __name__ == "__main__":
    asyncio.run(main())
