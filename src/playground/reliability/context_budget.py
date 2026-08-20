"""
WHAT      An instrument, not an argument. It reads the real context-window
          breakdown before and after one exchange, prints the measured cost of
          that exchange, and works out how many more like it fit before
          auto-compaction fires - then says plainly that compaction did not fire
          here and what it would take.
WHY       Most people picture the context window as "my conversation". It is not:
          the system prompt, tool schemas, memory files and skill descriptions are
          resident before you type a character. This file exists to replace that
          picture with four numbers you measured yourself.
DOMAIN    D5 Context Management and Reliability
TRADEOFF  Measuring the approach to a threshold is not the same as measuring what
          happens when you cross it, and this file only does the first. The
          arithmetic below assumes every future turn costs what this one cost,
          which is false the moment a tool returns a large result. Treat the
          estimate as an order of magnitude, not a countdown.
ALTERNATIVE  Force a crossing: loop a large prompt until the threshold is passed
          and diff the transcript. That measures the thing that actually matters
          and costs real quota, which is why this file stops short of it and says
          so instead of implying otherwise.

Model: claude-haiku-4-5, max_turns=2. get_context_usage() costs no tokens; the
single query between the two readings is the only billed part.

WHAT THIS FILE USED TO CLAIM. It carried a confident paragraph about what
compaction costs you - lossy, automatic, verbatim detail replaced by a summary -
next to a demo that had never triggered one. The claim is documented
(<https://code.claude.com/docs/en/costs>, and the /compact behaviour in
<https://code.claude.com/docs/en/memory>, both fetched 2026-08-20), so it is not
wrong; it was just presented as if this run had shown it. It has been demoted to
where it belongs: a labelled DOCUMENTED note, printed after the measurements it
is not derived from.
"""
import asyncio
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultMessage

from playground import teach

MODEL = "claude-haiku-4-5"

LESSON = {
    "domain": "D5 Context Management and Reliability",
    "setup": "basics.check_auth passed. Nothing else - this demo measures a "
             "session it opens itself, so it starts from the same resting cost "
             "any of your own sessions would.",
    "run": "uv run python -m playground.run reliability.context_budget",
    "cost": "1 model call; both context readings are free",
    "expect": "Two category breakdowns with a five-figure token total in each, "
              "the delta between them, the auto-compact threshold, and an "
              "explicit line saying compaction did NOT happen during this run.",
    "learn": "The window has a floor and a ceiling that neither the percentage "
             "nor the 'Free space' line tells you about: several thousand tokens "
             "are resident before you speak, and the ceiling that governs a long "
             "session is the auto-compact threshold, not the window size.",
}


def read(usage: dict[str, Any], label: str) -> int:
    """Print one context reading and return its total token count."""
    print(f"\n--- {label} ---")
    # WHY: percentage is of maxTokens, which is the *usable* window. rawMaxTokens
    # is the model's nominal limit and is larger; the difference is reserved
    # headroom you do not get to spend.
    print(
        f"{usage['model']}: {usage['totalTokens']:,} of {usage['maxTokens']:,} tokens "
        f"({usage['percentage']:.1f}%)"
    )
    for category in sorted(usage["categories"], key=lambda c: -c["tokens"]):
        # WHY: zero-token categories are noise here, but their names are worth
        # reading in the SDK types - they show what *could* be resident. Note also
        # that deferred tools are listed but excluded from totalTokens; they are
        # loaded on demand, so they cost nothing until something needs them.
        if category["tokens"]:
            print(f"  {category['name']:<30}{category['tokens']:>9,}")
    return int(usage["totalTokens"])


def project(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """Turn two readings into the only numbers worth acting on."""
    resting, now = int(before["totalTokens"]), int(after["totalTokens"])
    delta = now - resting
    threshold = after.get("autoCompactThreshold")
    lines = [
        f"resting cost before any message : {resting:,} tokens "
        f"({before['percentage']:.1f}% of the usable window)",
        f"this one exchange added         : {delta:,} tokens",
    ]
    if not threshold:
        # WHY: reported, not skipped. A missing threshold means auto-compaction is
        # off for this session, which changes the operational advice completely -
        # you now run into a hard wall instead of a silent summarisation.
        lines.append("auto-compact threshold          : not reported "
                     "(auto-compaction appears to be disabled for this session)")
        return lines
    headroom = int(threshold) - now
    lines.append(f"auto-compact fires at           : {int(threshold):,} tokens "
                 f"(enabled={after['isAutoCompactEnabled']})")
    lines.append(f"headroom left right now         : {headroom:,} tokens")
    # WHY: printed next to each other because they disagree, and the SDK reports
    # the larger one as a category called "Free space". The difference is space
    # you can technically fill and cannot use without triggering a summarisation
    # of your own transcript, which makes "free" an optimistic word for it.
    free = next((c["tokens"] for c in after["categories"]
                 if c["name"] == "Free space"), None)
    if free is not None:
        lines.append(f"...but the reading above calls {int(free):,} tokens 'Free "
                     f"space': {int(free) - headroom:,} of those are past the "
                     f"threshold")
    # WHY: guard the division rather than assume delta > 0. A cached, trivial
    # exchange can report a delta of zero, and a ZeroDivisionError in the
    # instrument would destroy the reading it was taking.
    if delta > 0:
        lines.append(f"exchanges of THIS size before compaction: about "
                     f"{headroom // delta:,}")
    else:
        lines.append("exchanges before compaction     : not estimable, this "
                     "exchange measured no growth")
    return lines


async def main() -> None:
    teach.banner(LESSON)

    options = ClaudeAgentOptions(
        model=MODEL, max_turns=2, system_prompt="Answer in one short sentence."
    )

    async with ClaudeSDKClient(options=options) as client:
        # WHY: taken before any prompt is sent. Everything reported here is the
        # fixed rent you pay on every single turn for the rest of the session.
        # Adding an MCP server or a skill raises this line permanently.
        before = await client.get_context_usage()
        read(before, "at startup, before any message")

        await client.query(
            "In one sentence, what is the difference between compaction and "
            "context editing?"
        )
        billed: dict[str, Any] = {}
        async for message in client.receive_response():
            if isinstance(message, ResultMessage):
                # WHY: printed raw rather than summarised. The nesting matters -
                # cache_read_input_tokens usually dwarfs input_tokens, and seeing
                # the whole dict once is the fastest cure for quoting the wrong
                # field in a cost estimate later.
                billed = message.usage or {}
                print(f"\nthis turn billed: {billed}")

        after = await client.get_context_usage()
        read(after, "after one exchange")

    print("\n--- projection ---")
    numbers = project(before, after)
    for line in numbers:
        print(f"  {line}")

    # WHY: stated as an outcome, not omitted. A demo about compaction that never
    # compacts has to say so in its own output, or every reader will assume the
    # numbers above are post-compaction numbers.
    print("\n--- what did NOT happen ---")
    print("  Compaction did not run during this session. Nothing above is a")
    print("  measurement of compaction; it is a measurement of the distance to")
    print("  it. To trigger one you would have to cross the threshold in the")
    print("  projection above - many more exchanges, or one tool result large")
    print("  enough to jump the gap in a single turn.")
    print("  DOCUMENTED, not measured here: compaction replaces older turns with")
    print("  a summary, so exact strings, ids and error text inside the compacted")
    print("  range survive only as whatever the summariser kept.")

    teach.closing(
        LESSON,
        observed=numbers + [
            f"The billed usage for that single turn was "
            f"{billed.get('input_tokens')} uncached input against "
            f"{billed.get('cache_read_input_tokens')} read from cache - the "
            f"resting cost is paid on every turn, but mostly at cache rates.",
        ],
        naive="The intuitive model is an empty window that fills as you talk and "
              "a limit you hit when it is full. Both halves are wrong, and the "
              "second one is wrong in a way the SDK's own output encourages. "
              "Look at the 'Free space' category above and then at the headroom "
              "line in the projection: they are different numbers, and the "
              "smaller one is the real one. Free space is measured against the "
              "window; the threshold sits below that, so a chunk of what is "
              "reported as free is space you cannot use without triggering a "
              "summarisation of your own history. Whichever way the arithmetic "
              "lands on your model, the operational number is the headroom, "
              "never the percentage - and the floor under it all is the resting "
              "cost, which you did nothing to incur and pay on every turn.",
    )


if __name__ == "__main__":
    asyncio.run(main())
