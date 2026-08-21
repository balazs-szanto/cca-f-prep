"""
WHAT      The agentic loop written out in full: send, read `stop_reason`, run the
          tools it asked for, put the results back as a user turn, send again.
          Nine lines of control flow, printed as a transcript.
WHY       This is the one thing the Claude Agent SDK does for you that the exam
          asks you to do yourself. `query()` hands you typed messages and never
          shows the seam, so a reader can ship a working agent without ever
          having decided what ends a turn - and then cannot answer a question
          about the thing they never decided. Task statement 1.1 is written
          entirely against constructs that do not appear in `ClaudeAgentOptions`.
DOMAIN    D1 Agentic Architecture and Orchestration (27%),
          task statement 1.1
TRADEOFF  The loop below returns the whole `messages` array rather than just an
          answer, which makes the caller responsible for a list that grows
          without bound. That is deliberate: the growth *is* the context problem
          in D5, and hiding it behind a tidy `-> str` would delete the evidence.
          What it costs is that nothing here is reusable as-is.
ALTERNATIVE  `client.beta.messages.tool_runner`, or the Agent SDK. Both run this
          loop correctly and neither lets you see it. Use them in production and
          read this once, which is the whole argument for this file existing.

Model is irrelevant on the scripted path and never chosen here; the request
carries whatever `MODEL` says, and a live run bills a credential this repo does
not manage. Cost: free, no model call, unless a credential resolves.
"""
from __future__ import annotations

from examlab import present
from examlab.contract import TransportError, text_of, tool_result, tool_uses
from examlab.transport import choose as choose_transport
from examlab.transport import response

LESSON = {
    "domain": "D1 Agentic Architecture and Orchestration - 1.1",
    "setup": "Nothing. Read TOOLS and SCRIPT below first, then run_loop().",
    "run": "uv run python -m playground.run examlab.agentic_loop",
    "cost": "free - scripted transport, 0 model calls (1 live request per "
            "iteration if a credential resolves)",
    "expect": "Three exchanges. The first response carries prose AND a tool "
              "call in the same turn, which is the detail every wrong loop "
              "trips over. Then the stop_reason table and the budget incident.",
    "learn": "stop_reason is the termination condition and nothing else is. An "
             "iteration cap is a circuit breaker: reaching it is an incident to "
             "report, not a way to finish.",
}

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 1024

# WHY: descriptions carry input format, an example and a boundary against the
# sibling tool. That is task statement 2.1's whole content, and it is here rather
# than in the tool-design module because a loop demo with placeholder
# descriptions teaches the loop and mis-teaches the tools.
TOOLS = [
    {
        "name": "get_order",
        "description": (
            "Look up one order by its numeric order id. Returns status, total, "
            "line items and the id of the customer who placed it. Use this when "
            "the request names an order (e.g. 'order 4471', '#4471'). Does NOT "
            "accept an email address or a customer id - use get_customer for "
            "those, then follow the customer_id on the order back here."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer", "description": "Numeric order id, no '#'."},
            },
            "required": ["order_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_customer",
        "description": (
            "Look up one customer by customer id or email address. Returns name, "
            "tier and lifetime value, and nothing about any specific order. Use "
            "this to verify identity before any account-changing operation. If "
            "you only have an order number, call get_order first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "e.g. 'C-902'."},
                "email": {"type": "string", "description": "Exact address."},
            },
            "required": [],
            "additionalProperties": False,
        },
    },
]

# WHY: the first response carries a text block AND a tool_use block, because
# that is the shape the two most common wrong loops die on. A script where
# tool-use turns are silent would let both of them pass.
SCRIPT = [
    response(
        stop_reason="tool_use",
        content=[
            {"type": "text", "text": "I'll pull the order up first."},
            {"type": "tool_use", "id": "toolu_01", "name": "get_order",
             "input": {"order_id": 4471}},
        ],
        input_tokens=612, output_tokens=48,
    ),
    response(
        stop_reason="tool_use",
        content=[
            {"type": "tool_use", "id": "toolu_02", "name": "get_customer",
             "input": {"customer_id": "C-902"}},
        ],
        input_tokens=734, output_tokens=31,
    ),
    response(
        stop_reason="end_turn",
        content=[{"type": "text", "text": (
            "Order 4471 shipped on 2026-08-04 for 149.00 and belongs to Rae "
            "Moore (gold tier). It is inside the 30-day window, so a refund is "
            "allowed - say the word and I will process it."
        )}],
        input_tokens=901, output_tokens=64,
    ),
]

# WHY: fabricated, and shaped like a real backend rather than like an answer.
# get_order returns a customer_id the model has to notice and carry into the
# second call, which is what makes this two iterations instead of one.
BACKEND = {
    "get_order": '{"order_id":4471,"status":"shipped","shipped":"2026-08-04",'
                 '"total":"149.00","customer_id":"C-902"}',
    "get_customer": '{"customer_id":"C-902","name":"Rae Moore","tier":"gold"}',
}


class LoopBudgetExceeded(RuntimeError):
    """The circuit breaker tripped. Not a completion - an incident.

    Raised rather than returned so that a caller cannot mistake a truncated run
    for a finished one. The blueprint names "arbitrary iteration caps as the
    primary stopping mechanism" as an anti-pattern; a cap that raises is not
    that, because nothing downstream can read its output as an answer.
    """


def dispatch(name: str, arguments: dict) -> str:
    """Run one tool. In a real system this is where your backend call goes."""
    if name not in BACKEND:
        # WHY: reported as a tool result, not raised. The model asked for a tool
        # that does not exist - that is a fact it can recover from by picking a
        # different one, and an exception here would take the whole run down
        # instead. See tool_errors.py for the general form of this decision.
        return f'{{"error":"no such tool: {name}","isRetryable":false}}'
    return BACKEND[name]


def run_loop(transport, prompt: str, *, budget: int = 8):
    """The loop. Returns (final response, messages, iterations used).

    Read the `while True` and the two `append` calls; everything else is
    reporting. The three decisions that matter:

    1. **The condition is `stop_reason`.** Not the presence of text, not a
       keyword in the text, not an iteration count. Exactly one field decides.
    2. **The assistant turn is appended before the results.** The model's own
       `tool_use` blocks have to be in the history, or the ids the results
       reference do not exist and the request is rejected.
    3. **All results for one turn go back in a single user message.** A turn
       that asked for three tools gets one message with three `tool_result`
       blocks, not three messages.
    """
    messages: list[dict] = [{"role": "user", "content": prompt}]
    for iteration in range(1, budget + 1):
        reply = transport.create(
            model=MODEL, max_tokens=MAX_TOKENS, tools=TOOLS, messages=messages,
        )
        messages.append({"role": "assistant", "content": reply["content"]})
        requested = tool_uses(reply)
        present.exchange(
            iteration,
            sent=f"{len(messages) - 1} message(s), {len(TOOLS)} tool(s)",
            got=(f"{len(requested)} tool_use: "
                 f"{', '.join(b['name'] for b in requested)}" if requested
                 else f"text: {text_of(reply)[:44]}..."),
            stop_reason=reply["stop_reason"],
        )
        if reply["stop_reason"] != "tool_use":
            # WHY: any non-tool_use reason exits, including ones this file has
            # never seen. Whitelisting "end_turn" and looping on everything else
            # turns an unfamiliar stop reason into an infinite loop.
            return reply, messages, iteration
        messages.append({
            "role": "user",
            "content": [tool_result(b["id"], dispatch(b["name"], b["input"]))
                        for b in requested],
        })
    raise LoopBudgetExceeded(
        f"{budget} iterations without a terminal stop_reason. The model is "
        f"still asking for tools; something upstream is looping.")


# DOCUMENTED, from the Messages API tool-use pages. The set has grown over time -
# `refusal` and `pause_turn` are both later additions - so the last row is the
# one that keeps the loop correct as it grows again.
STOP_REASONS = [
    ("end_turn", "Model finished on its own", "Stop. Return the text."),
    ("tool_use", "Wants one or more tools run", "Execute, append results, resend."),
    ("max_tokens", "Truncated mid-answer", "NOT done. Raise, or continue explicitly."),
    ("stop_sequence", "Hit a stop string you set", "Stop."),
    ("pause_turn", "Long server-tool turn paused", "Resend the partial turn as-is."),
    ("refusal", "Declined on safety grounds", "Stop. Resending unchanged will not help."),
    ("<unknown>", "A value newer than your code", "Stop and log. Never treat as end_turn."),
]


def main() -> None:
    transport, note = choose_transport(SCRIPT)
    present.banner(
        title="The agentic loop, written out",
        domain="D1 Agentic Architecture and Orchestration - 1.1",
        question="What ends a turn, and what has to be in the request to continue it?",
        expect="Three exchanges, two of them tool_use. Then the budget incident.",
        note=note,
    )
    final, messages, iterations = run_loop(transport, "Can I still refund order 4471?")
    print(f"\n  {iterations} iteration(s), {len(messages)} messages in history.")
    print(f"  Final: {text_of(final)[:180]}")

    present.rule("stop_reason - the whole contract")
    present.table(("value", "means", "what the loop must do"), STOP_REASONS)

    present.rule("the circuit breaker, tripped on purpose")
    try:
        run_loop(ScriptedNeverEnds(), "loop forever", budget=2)
    except LoopBudgetExceeded as exc:
        print(f"  LoopBudgetExceeded: {exc}")
        print("  Note the type. A cap that RETURNS lets a caller print a")
        print("  truncated run as an answer; a cap that RAISES cannot.")
    except TransportError as exc:
        print(f"  TransportError: {exc}")

    present.rule()
    print("  LEARN  " + LESSON["learn"])


class ScriptedNeverEnds:
    """A transport that always asks for another tool. Exists to trip the budget.

    Not in transport.py: it is a fixture for one demonstration, and a transport
    that cannot terminate has no other legitimate use.
    """

    def create(self, **request):
        n = len(request["messages"])
        return response(
            stop_reason="tool_use",
            content=[{"type": "tool_use", "id": f"toolu_{n:02d}",
                      "name": "get_order", "input": {"order_id": 4471}}],
        )


if __name__ == "__main__":
    main()
