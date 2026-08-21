"""
WHAT      The three loop-termination anti-patterns the blueprint names, plus the
          plumbing bug that produces them, each run against the same script as
          `agentic_loop.py` and each printed with what it concluded.
WHY       All three are listed as things to avoid, which is the form in which
          they are least useful. "Do not parse natural language to decide
          termination" is easy to agree with and easy to write anyway, because
          the code that does it looks reasonable and passes on the happy path.
          What makes it stick is watching the same three-response script produce
          a confident wrong answer three different ways.
DOMAIN    D1 Agentic Architecture and Orchestration (27%),
          task statement 1.1
TRADEOFF  Each wrong loop is written as its own small function rather than as one
          parameterised loop with a mode flag. More lines, and it means a reader
          can read any one of them in isolation - which is how they will meet
          them in a real codebase, one at a time, looking plausible.
ALTERNATIVE  Assert the failures in a test suite. Better as a regression guard
          and worse as a lesson: a passing test prints nothing, and the whole
          point here is what the wrong answer looks like when you believe it.

Cost: free. Reuses the script and tools from `agentic_loop`, so the two files
are answering the same question and only the control flow differs.
"""
from __future__ import annotations

from examlab import present
from examlab.agentic_loop import MAX_TOKENS, MODEL, SCRIPT, TOOLS, dispatch
from examlab.contract import TransportError, text_of, tool_result, tool_uses
from examlab.transport import ScriptedTransport

LESSON = {
    "domain": "D1 Agentic Architecture and Orchestration - 1.1",
    "setup": "Read agentic_loop.py first. This file is that loop, broken four ways.",
    "run": "uv run python -m playground.run examlab.loop_antipatterns",
    "cost": "free - scripted transport, 0 model calls",
    "expect": "Four diagnoses. Two of the wrong loops return a confident wrong "
              "answer with no error at all; the other two are caught by the "
              "request validator, not by anything the loop itself noticed.",
    "learn": "Every one of these is a termination condition that correlates with "
             "being finished instead of meaning it. The dangerous two are the "
             "ones that fail silently, and both of those return a STRING - so "
             "the caller has no way to tell.",
}


def stops_on_text(transport) -> str:
    """ANTI-PATTERN 1: treat "the response contains text" as completion.

    Looks reasonable: if the model wrote prose, surely it answered. But a turn
    may carry a preamble AND a tool call - `SCRIPT[0]` does exactly that, and it
    is the commonest shape in practice, because models narrate before acting.

    Fails on the first exchange, silently, and returns the narration.
    """
    messages: list[dict] = [{"role": "user", "content": "Can I still refund order 4471?"}]
    while True:
        reply = transport.create(model=MODEL, max_tokens=MAX_TOKENS,
                                 tools=TOOLS, messages=messages)
        messages.append({"role": "assistant", "content": reply["content"]})
        if text_of(reply):
            return text_of(reply)
        messages.append({"role": "user", "content": [
            tool_result(b["id"], dispatch(b["name"], b["input"]))
            for b in tool_uses(reply)]})


def stops_on_keyword(transport) -> str:
    """ANTI-PATTERN 2: parse the prose for a completion signal.

    The instruction "say DONE when you have finished" plus `if "done" in text`
    is the shape this takes in the wild. Two failure modes, and this script hits
    the second: the model finishes without the magic word, so the loop carries
    on past a completed turn - and the request it builds next has no tool
    results in it, because there were no tool calls to answer.
    """
    messages: list[dict] = [{"role": "user", "content": "Can I still refund order 4471?"}]
    while True:
        reply = transport.create(model=MODEL, max_tokens=MAX_TOKENS,
                                 tools=TOOLS, messages=messages)
        messages.append({"role": "assistant", "content": reply["content"]})
        if "done" in text_of(reply).lower():
            return text_of(reply)
        messages.append({"role": "user", "content": [
            tool_result(b["id"], dispatch(b["name"], b["input"]))
            for b in tool_uses(reply)] or "continue"})


def stops_on_count(transport) -> str:
    """ANTI-PATTERN 3: an iteration cap as the primary stopping mechanism.

    Two turns is enough for most requests, so the cap is set to two and the last
    response is returned. On this script the second response is a pure tool_use
    turn, so the "answer" is the empty string - and an empty string is exactly
    what a caller renders as a blank reply rather than as a failure.
    """
    messages: list[dict] = [{"role": "user", "content": "Can I still refund order 4471?"}]
    reply: dict = {}
    for _ in range(2):
        reply = transport.create(model=MODEL, max_tokens=MAX_TOKENS,
                                 tools=TOOLS, messages=messages)
        messages.append({"role": "assistant", "content": reply["content"]})
        requested = tool_uses(reply)
        if not requested:
            break
        messages.append({"role": "user", "content": [
            tool_result(b["id"], dispatch(b["name"], b["input"])) for b in requested]})
    return text_of(reply)


def forgets_the_assistant_turn(transport) -> str:
    """PLUMBING BUG: append the results without appending the model's own turn.

    Not on the blueprint's list, and the one that costs the most debugging time,
    because the mental model behind it is nearly right - "add the tool results
    to the history" - and it omits the half that makes the ids resolvable. The
    `tool_use` blocks have to be in the transcript for a `tool_use_id` to refer
    to anything.

    Caught as rule 4, not rule 2 - which is worth noticing, because it is not
    where you would look. Skipping the assistant turn leaves two `user` messages
    adjacent, so the roles stop alternating one check *before* anyone asks
    whether the `tool_use_id` resolves. The error you get therefore talks about
    roles and says nothing about tool ids, and the bug is in the tool plumbing.
    """
    messages: list[dict] = [{"role": "user", "content": "Can I still refund order 4471?"}]
    while True:
        reply = transport.create(model=MODEL, max_tokens=MAX_TOKENS,
                                 tools=TOOLS, messages=messages)
        requested = tool_uses(reply)
        if not requested:
            return text_of(reply)
        messages.append({"role": "user", "content": [
            tool_result(b["id"], dispatch(b["name"], b["input"])) for b in requested]})


CASES = [
    (stops_on_text, "text present means finished"),
    (stops_on_keyword, "keyword in the prose means finished"),
    (stops_on_count, "two iterations is always enough"),
    (forgets_the_assistant_turn, "results appended, model's turn not"),
]


def main() -> None:
    present.banner(
        title="Four ways to end the loop wrongly",
        domain="D1 Agentic Architecture and Orchestration - 1.1",
        question="Which failures announce themselves, and which just return a string?",
        expect="Two silent wrong answers, two validator rejections.",
        note=("TRANSPORT: scripted for all four cases, deliberately. These are "
              "control-flow defects, and a live model would let two of them "
              "pass on a lucky response - which is exactly why they survive in "
              "real codebases."),
    )
    rows: list[tuple[str, ...]] = []
    for function, summary in CASES:
        transport = ScriptedTransport(SCRIPT)
        present.rule(f"{function.__name__} - {summary}")
        try:
            conclusion = function(transport)
        except TransportError as exc:
            print(f"  raised TransportError after {len(transport.requests)} request(s)")
            print(f"  {exc}")
            rows.append((function.__name__, str(len(transport.requests)),
                         "raised", "loud - the request was refused"))
            continue
        blank = "<empty string>" if not conclusion else f"{conclusion[:56]}..."
        print(f"  returned after {len(transport.requests)} request(s): {blank}")
        print("  No exception. Nothing logged. A caller renders this as the answer.")
        rows.append((function.__name__, str(len(transport.requests)),
                     "returned", "SILENT - indistinguishable from success"))

    present.rule("how each one fails")
    present.table(("loop", "requests", "outcome", "how you find out"), rows)
    print()
    print("  The correct loop needed 3 requests (see agentic_loop). Every row")
    print("  above stopped early or ran long, and only half of them said so.")
    present.rule()
    print("  LEARN  " + LESSON["learn"])


if __name__ == "__main__":
    main()
