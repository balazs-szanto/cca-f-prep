"""
WHAT      The smallest useful Agent SDK call: one prompt in, streamed text out.
WHY       Everything else in this repo is this file plus one idea. If the message
          loop below is not completely clear, nothing later will be.
DOMAIN    D1 Agentic Architecture and Orchestration
TRADEOFF  query() is a one-shot: it opens a session, runs, and closes. That makes
          it trivially simple and means there is no way to ask a follow-up - the
          context is gone when the iterator finishes.
ALTERNATIVE  ClaudeSDKClient keeps the session open across several exchanges. Use
          it the moment you need a second turn that remembers the first; see
          reliability/session_resume.py.

Model: claude-haiku-4-5, max_turns=1.

This file used to pass no options at all, to show what "the bare minimum" looks
like. That was a nice idea and a bad demo: with no model pinned the run bills
whatever the CLI happens to default to that week, which breaks the one house rule
this repo cannot afford to break (see the cost section of CLAUDE.md). Two options
are now set, and they are the two that a demo is never allowed to omit - the
model, so the bill is predictable, and max_turns, whose real default is *no
limit*. Everything else is still absent.

max_turns=1 is safe here specifically because there is no tool and no
output_format. MEASURED 2026-08-20: the same call with an output_format needs 2,
because producing the structured answer consumes the turn.
"""
import asyncio

from claude_agent_sdk import (
    AssistantMessage, ClaudeAgentOptions, ClaudeSDKError, ResultMessage, TextBlock,
    query,
)

from playground import teach

MODEL = "claude-haiku-4-5"

LESSON = {
    "domain": "D1 Agentic Architecture and Orchestration",
    "setup": "basics.check_auth passed. No tools, no schema, no session - one "
             "prompt and the two options every demo here must set.",
    "run": "uv run python -m playground.run basics.hello",
    "cost": "1 model call",
    "expect": "One sentence appearing in chunks rather than all at once, then a "
              "line reading [success] 1 turn(s) with an API duration, then a "
              "session id you could hand to reliability.session_resume.",
    "learn": "query() is an async generator over a stream of typed messages, not "
             "a function that returns a response: the run IS the loop, and every "
             "number you will ever want about it arrives once, on the final "
             "ResultMessage.",
}


async def main() -> None:
    teach.banner(LESSON)
    print("Prompt -> Claude\n")

    # WHY: counted rather than assumed. The closing block claims the text arrived
    # in pieces, and that claim has to come from this run, not from what usually
    # happens - one chunk would mean the streaming lesson did not demonstrate.
    chunks = 0
    result: ResultMessage | None = None

    options = ClaudeAgentOptions(model=MODEL, max_turns=1)

    # WHY the try, in the simplest file in the repo: because max_turns is set,
    # and hitting a cap yields the ResultMessage and THEN raises. Even here,
    # where the cap has never been hit, the guard belongs - a demo that models
    # the loop without it is the demo people copy. Enforced by
    # .claude/hooks/check_turn_cap_guard.py, which exists because this exact
    # omission was made three times before anyone automated the check.
    try:
        # WHY: query() is an async generator, not a coroutine returning a result.
        # It yields as the agent works, which is why there is no `await query()`
        # here and no single "response" object to inspect. The run is the loop.
        async for message in query(prompt="Say hello in exactly one sentence.",
                                   options=options):

            # WHY: the stream carries several message types and you are expected
            # to ignore most of them. SystemMessage (init, config), UserMessage
            # (tool results echoed back) and StreamEvent (partial deltas) all
            # flow past. Match on the two you care about and let the rest go by -
            # filtering with isinstance is the intended pattern, not a shortcut.
            if isinstance(message, AssistantMessage):

                # WHY: content is a list of blocks, not a string. One assistant
                # turn can mix TextBlock, ThinkingBlock and ToolUseBlock, so
                # there is no single .text to read. Later demos match
                # ToolUseBlock here instead.
                for block in message.content:
                    if isinstance(block, TextBlock):
                        chunks += 1
                        # WHY: flush=True because stdout is block-buffered when
                        # piped. Without it the "streaming" arrives in one lump
                        # at the end, defeating the point of streaming at all.
                        print(block.text, end="", flush=True)

            elif isinstance(message, ResultMessage):
                # WHY: exactly one ResultMessage arrives, last, and it is the
                # only place the run's metadata exists - cost, token usage,
                # session id, turn count, permission denials. If you do not
                # capture it here it is gone. Every measurement in this repo
                # comes from this message.
                result = message
                print(f"\n\n[{message.subtype}] {message.num_turns} turn(s), "
                      f"{message.duration_api_ms} ms of API time")
                print(f"session id: {message.session_id}")
    except ClaudeSDKError as exc:
        print(f"\n\nraised after the result: {type(exc).__name__}")

    if result is None:
        raise RuntimeError("The stream ended without a ResultMessage.")

    usage = result.usage or {}
    teach.closing(
        LESSON,
        observed=[
            f"The sentence arrived as {chunks} TextBlock(s) inside "
            f"AssistantMessage; nothing you printed came from a return value.",
            f"Exactly one ResultMessage closed the stream: subtype "
            f"{result.subtype!r}, {result.num_turns} turn(s), "
            f"{result.duration_api_ms} ms of API time.",
            f"That one message also carried the session id "
            f"({result.session_id[:8]}...), the cost "
            f"({result.total_cost_usd}) and the usage "
            f"({usage.get('input_tokens')} in / "
            f"{usage.get('output_tokens')} out, "
            f"{usage.get('cache_read_input_tokens')} read from cache).",
        ],
        naive="The shape you expect is `response = await query(prompt)`, one "
              "object with a .text on it. There is no such object. If you throw "
              "away the ResultMessage while iterating - and it is easy to, it "
              "carries no text and looks like housekeeping - the cost, the token "
              "counts and the session id are gone for good. Look at how many "
              "later demos in this repo do nothing but read that one message.",
    )


# WHY: no `if __name__ == "__main__"` guard, deliberately. The dispatcher runs
# demos with runpy.run_module(..., run_name="__main__"), so both styles work; the
# newer files use the guard, and this one is left bare to show the difference.
asyncio.run(main())
