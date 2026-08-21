"""
WHAT      The four `tool_choice` modes, a transport that honours them, and the
          loop bug that follows from forcing a tool and forgetting to stop.
WHY       `tool_choice` is the highest-leverage request field the Agent SDK does
          not expose - `docs/tool-surface.md` lists it as API-ONLY - and it is
          usually taught as a table of three values. The table is the easy half.
          The half that bites is that forcing a tool is a property of the
          REQUEST, not of the conversation, so a forced choice left in place
          across iterations compels a tool call on every turn and the loop can
          never reach `end_turn`. That failure is invisible in a single-turn
          example, which is how most of them are written.
DOMAIN    D2 Tool Design and MCP Integration (18%), task
          statement 2.3; and D4 (20%), task statement 4.3
TRADEOFF  The transport here implements the documented semantics of
          `tool_choice` rather than replaying a script, which makes the loop
          behaviour below emerge instead of being staged. The cost is that the
          demo now depends on this repo's reading of the documentation being
          right - if the real API is laxer than this, the second run would
          terminate live and not here.
ALTERNATIVE  Read the table on the `define-tools` page and move on. Faster, and
          it leaves the forced-forever bug to be discovered in a staging
          environment, which is where this one was found.

Cost: free. Every response is synthesised from the request's own `tool_choice`.
"""
from __future__ import annotations

from examlab import present
from examlab.agentic_loop import MAX_TOKENS, MODEL, TOOLS, dispatch
from examlab.contract import (
    TransportError,
    text_of,
    tool_result,
    tool_uses,
    validate_conversation,
)
from examlab.transport import response

LESSON = {
    "domain": "D2 Tool Design and MCP Integration - 2.3",
    "setup": "Read ChoiceAwareTransport, then the two loops. Decide which one "
             "terminates before you run it.",
    "run": "uv run python -m playground.run examlab.tool_choice",
    "cost": "free - responses are synthesised from the request, 0 model calls",
    "expect": "The mode table, then two loops over identical tools: one that "
              "never terminates and one that does. The only difference is a "
              "single line that removes tool_choice after the first request.",
    "learn": "tool_choice is per-request. 'any' and a named tool guarantee a "
             "tool call on EVERY request you send them with, so the loop's exit "
             "has to come from a later request that no longer forces one.",
}

# DOCUMENTED, from the tool-use `define-tools` and `overview` pages as recorded in
# docs/tool-surface.md, fetched 2026-08-20. The fourth row is the one most often
# left out of summaries, and it is not the same as passing no tools at all - the
# definitions stay in the prompt and stay billed.
MODES = [
    ('{"type": "auto"}', "default when tools are present",
     "May call a tool, may answer in text. The only mode that can end a turn "
     "with prose on the first request."),
    ('{"type": "any"}', "must call something",
     "Guarantees a tool_use block; the model picks which. Use when text is "
     "never an acceptable answer."),
    ('{"type": "tool", "name": "x"}', "must call exactly x",
     "Guarantees that one tool. Use to force a first step - then stop forcing."),
    ('{"type": "none"}', "must not call anything",
     "Tools stay defined and stay billed; the model may not use them."),
]

# DOCUMENTED, same source: the tool-use system prompt the API constructs, in
# tokens, before any of your own definitions are counted. Forcing is not free.
OVERHEAD = [
    ("Claude Opus 5", "286", "406", "+120"),
    ("Claude Sonnet 5", "354", "474", "+120"),
    ("Claude Haiku 4.5", "496", "588", "+92"),
]


class ChoiceAwareTransport:
    """Synthesises a response by reading the request's own `tool_choice`.

    Not a script. This is a model of the documented contract, which is the only
    way the loop behaviour below can be demonstrated rather than staged: if the
    responses were canned, the terminating and non-terminating loops would
    differ because the author decided they should.
    """

    def __init__(self) -> None:
        self.requests: list[dict] = []

    def create(self, **request):
        validate_conversation(request["messages"])
        self.requests.append(request)
        if len(self.requests) > 12:
            raise TransportError("12 requests; refusing to model an unbounded loop")
        choice = request.get("tool_choice") or {"type": "auto"}
        forced = choice.get("type")
        if forced == "tool":
            name = choice["name"]
        elif forced == "any":
            name = request["tools"][0]["name"]
        else:
            # WHY: auto and none both settle here. Under `auto` a real model
            # would often call a tool on the first request; this returns text so
            # that the contrast with the forcing modes is the only variable.
            return response(
                stop_reason="end_turn",
                content=[{"type": "text", "text":
                          f"Answered in prose after {len(self.requests)} request(s)."}])
        return response(
            stop_reason="tool_use",
            content=[{"type": "tool_use", "id": f"toolu_{len(self.requests):02d}",
                      "name": name, "input": {"order_id": 4471}}])


def loop(transport, *, first_choice: dict, relax: bool, budget: int = 6) -> str:
    """The agentic loop with one extra decision: what happens to `tool_choice`.

    `relax=True` sends the forced choice on the first request only. That is the
    documented pattern for "make sure extract_metadata runs before anything
    else": force it once, then let the model continue normally. `relax=False`
    is the same code with the choice left in the request, which is the version
    that reads more consistently and does not terminate.
    """
    messages: list[dict] = [{"role": "user", "content": "Refund order 4471."}]
    choice: dict | None = first_choice
    for iteration in range(1, budget + 1):
        request = {"model": MODEL, "max_tokens": MAX_TOKENS,
                   "tools": TOOLS, "messages": messages}
        if choice is not None:
            request["tool_choice"] = choice
        reply = transport.create(**request)
        messages.append({"role": "assistant", "content": reply["content"]})
        present.exchange(
            iteration,
            sent=f"tool_choice={choice if choice else 'omitted'}",
            got=(", ".join(b["name"] for b in tool_uses(reply)) or "text"),
            stop_reason=reply["stop_reason"],
        )
        if reply["stop_reason"] != "tool_use":
            return text_of(reply)
        messages.append({"role": "user", "content": [
            tool_result(b["id"], dispatch(b["name"], b["input"]))
            for b in tool_uses(reply)]})
        if relax:
            # THE WHOLE DEMO IS THIS LINE. The forced choice has done its job;
            # leaving it set re-forces a tool call on the next request, and on
            # every request after that.
            choice = None
    raise RuntimeError(f"{budget} iterations, still no terminal stop_reason")


def main() -> None:
    present.banner(
        title="tool_choice: auto, any, forced, none",
        domain="D2 Tool Design and MCP Integration - 2.3",
        question="What does forcing a tool cost, and when do you stop forcing it?",
        expect="Two loops, identical except for one line. One does not terminate.",
        note=("TRANSPORT: synthesised. Each response is derived from the "
              "request's own tool_choice according to the documented contract, "
              "so the loop behaviour below follows from the rule rather than "
              "from a script. Nothing here is a measurement of a model."),
    )
    present.rule("the four modes")
    present.table(("tool_choice", "guarantee", "what it means for your loop"),
                  [(m[0], m[1], m[2]) for m in MODES])

    present.rule("what forcing costs, per request, before your own tools")
    present.table(("model", "auto / none", "any / tool", "delta"), OVERHEAD)
    print("\n  DOCUMENTED. Forcing changes the tool-use system prompt the API")
    print("  builds, so it is charged on every request you force, not once.")

    present.rule("forced and never relaxed")
    transport = ChoiceAwareTransport()
    try:
        loop(transport, first_choice={"type": "tool", "name": "get_order"}, relax=False)
    except (RuntimeError, TransportError) as exc:
        print(f"\n  {type(exc).__name__}: {exc}")
        print("  Every request forced get_order, so every response was tool_use,")
        print("  so stop_reason was never terminal. The loop is correct and the")
        print("  request is wrong - which is why reviewing the loop finds nothing.")

    present.rule("forced once, then relaxed")
    transport = ChoiceAwareTransport()
    answer = loop(transport, first_choice={"type": "tool", "name": "get_order"}, relax=True)
    print(f"\n  terminated in {len(transport.requests)} request(s): {answer}")
    print("  Request 1 carried tool_choice; request 2 omitted it. That is the")
    print("  'force extract_metadata first, then continue' pattern in full.")

    present.rule()
    print("  LEARN  " + LESSON["learn"])


if __name__ == "__main__":
    main()
