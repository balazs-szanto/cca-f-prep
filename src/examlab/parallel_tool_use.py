"""
WHAT      One assistant turn that asks for three tools at once, answered the way
          the API requires, and then three ways of answering it that it rejects -
          each one run, each with the rule that actually catches it printed.
WHY       `agentic_loop.py` deliberately uses two DEPENDENT tools, so it never
          shows more than one `tool_use` block in a turn. That leaves the most
          common production shape undemonstrated: a question whose answer needs
          three independent lookups, which the model requests in a single turn.
          The plumbing for that is not "the loop again" - all the results go back
          in ONE user message, and every wrong version of that is wrong in a way
          whose error message names a different rule than the mistake suggests.
DOMAIN    D1 Agentic Architecture and Orchestration (27%), task statement 1.1
TRADEOFF  A fan-out turn cannot be answered partially, so the round trip is
          bounded by the SLOWEST tool. Three 50 ms lookups and one 4 s lookup
          cost 4 s, and there is no way to send the fast three ahead. Sequential
          calling would have surfaced the first three answers earlier; it just
          costs three round trips to do it.
ALTERNATIVE  `tool_choice={"type": "auto", "disable_parallel_tool_use": True}`
          caps every turn at one `tool_use` block, which makes this whole file
          unnecessary and turns an N-tool question into N round trips. Prefer it
          when your tools have side effects and you need them ordered; see
          `docs/tool-surface.md` for where that switch is reachable from.

Model is irrelevant on the scripted path. Cost: free, no model call, unless a
credential resolves - see `src/examlab/CLAUDE.md`.
"""
from __future__ import annotations

from examlab import present
from examlab.contract import TransportError, text_of, tool_result, tool_uses
from examlab.transport import ScriptedTransport, response
from examlab.transport import choose as choose_transport

LESSON = {
    "domain": "D1 Agentic Architecture and Orchestration - 1.1",
    "setup": "Read agentic_loop.py first. This is the same loop with one thing "
             "changed: the turn asks for three tools instead of one.",
    "run": "uv run python -m playground.run examlab.parallel_tool_use",
    "cost": "free - scripted transport, 0 model calls (2 live requests per arm "
            "if a credential resolves)",
    "expect": "The correct arm finishes in 2 requests with one user message "
              "carrying three tool_result blocks, one of them is_error. Then "
              "three broken arms, and the rule number each one trips.",
    "learn": "One turn's results go back in one user message, all of them, "
             "including the ones that failed. A tool that raised is still owed a "
             "result block - is_error=True - because the alternative is an "
             "unanswered id, and then the API rejects the whole request rather "
             "than just the tool call.",
}

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 1024

# WHY three tools that share no inputs and no outputs: independence is the
# precondition for a fan-out, and it is the reason this file does not import
# agentic_loop.TOOLS. Those two are dependent on purpose - get_order returns the
# customer_id that get_customer needs - so a model asking for both in one turn
# would be making a mistake, not parallelising. You cannot demonstrate correct
# fan-out with tools that have to be ordered.
def tool(name: str, description: str, prop: str, kind: str) -> dict:
    """One single-parameter tool.

    WHY the schemas are folded into a helper here and written out longhand in
    `agentic_loop.py` and `schema_design.py`: those files are about what a
    description and a schema have to contain. This one is about where results go,
    and three hand-written schemas would be thirty lines of the wrong lesson.
    """
    return {
        "name": name, "description": description,
        "input_schema": {
            "type": "object", "properties": {prop: {"type": kind}},
            "required": [prop], "additionalProperties": False,
        },
    }


TOOLS = [
    tool("get_order", "Look up one order by numeric id. Returns status and total.",
         "order_id", "integer"),
    tool("get_shipment", "Carrier tracking for one order id, independent of get_order.",
         "order_id", "integer"),
    tool("get_refund_policy", "The refund window in days for one region code.",
         "region", "string"),
]

# WHY the first response carries prose AND three tool_use blocks: the same trap
# as in agentic_loop, one size larger. Code that reads `content[0]` to find the
# tool call finds a text block; code that reads `content[-1]` finds the third
# tool and silently drops two. Only iterating and filtering by type is correct.
SCRIPT = [
    response(
        stop_reason="tool_use",
        content=[
            {"type": "text", "text": "Let me check all three at once."},
            {"type": "tool_use", "id": "toolu_01", "name": "get_order",
             "input": {"order_id": 4471}},
            {"type": "tool_use", "id": "toolu_02", "name": "get_shipment",
             "input": {"order_id": 4471}},
            {"type": "tool_use", "id": "toolu_03", "name": "get_refund_policy",
             "input": {"region": "CH"}},
        ],
        input_tokens=688, output_tokens=96,
    ),
    response(
        stop_reason="end_turn",
        content=[{"type": "text", "text": (
            "Order 4471 shipped and is out for delivery. The refund-policy "
            "service is down, so I could not confirm the window for CH - the "
            "other two facts are current as of this call."
        )}],
        input_tokens=1012, output_tokens=71,
    ),
]

BACKEND = {
    "get_order": '{"order_id":4471,"status":"shipped","total":"149.00"}',
    "get_shipment": '{"carrier":"DPD","state":"out_for_delivery"}',
}

# WHY one tool that raises: a fan-out where everything succeeds hides the only
# decision in this file that is genuinely a decision. Three tools means three
# chances for one to be down, and what you do with the other two is the lesson.
FAILING = {"get_refund_policy"}


def dispatch(name: str, arguments: dict) -> str:
    """Run one tool. Raises for FAILING, the way a real client does on a 503."""
    if name in FAILING:
        raise RuntimeError(f"{name} returned 503")
    return BACKEND[name]


def results_for(requested: list[dict], *, mode: str) -> list[dict]:
    """The `content` of the user message that answers one fan-out turn.

    Only `together` is correct. The other three are not exotic - each is the
    natural shape of one plausible belief about how tool results work, which is
    why each gets a row in DIAGNOSES rather than a comment saying "do not".
    """
    blocks: list[dict] = []
    for index, block in enumerate(requested):
        try:
            output = dispatch(block["name"], block["input"])
            blocks.append(tool_result(block["id"], output))
        except RuntimeError as exc:
            if mode == "skip_the_failure":
                # WHY this is the interesting bug: the code looks defensive. It
                # caught the exception, it kept the run alive, it did not crash.
                # It also dropped a pending id, so the request it builds next is
                # rejected before the model sees either of the two good results.
                continue
            blocks.append(tool_result(block["id"], f'{{"error":"{exc}"}}', is_error=True))
        if mode == "one_at_a_time" and index == 0:
            break
    if mode == "stale_id" and blocks:
        # WHY a well-formed id and not garbage: this is what a retry that reuses
        # a transcript from an earlier run produces, and what a hand-written test
        # fixture produces. The id looks right and belongs to nothing.
        blocks[-1] = dict(blocks[-1], tool_use_id="toolu_47")
    return blocks


def fan_out(transport, prompt: str, *, mode: str = "together", budget: int = 4):
    """The loop from agentic_loop.py with `results_for` as the only variable.

    Returns (final response, messages, iterations). Raises TransportError from
    the transport's validator when `mode` builds a request the real API would
    reject - which is the point of every mode but the first.
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
            sent=f"{len(messages) - 1} message(s)",
            got=(f"{len(requested)} tool_use in ONE turn: "
                 f"{', '.join(b['name'] for b in requested)}" if requested
                 else f"text: {text_of(reply)[:40]}..."),
            stop_reason=reply["stop_reason"],
        )
        if reply["stop_reason"] != "tool_use":
            return reply, messages, iteration
        blocks = results_for(requested, mode=mode)
        flagged = sum(1 for b in blocks if b.get("is_error"))
        print(f"     -> 1 user message, {len(blocks)} tool_result block(s)"
              f"{f', {flagged} is_error' if flagged else ''}")
        messages.append({"role": "user", "content": blocks})
    raise RuntimeError("budget exhausted")


BROKEN = [
    ("one_at_a_time", "answer the first tool, send, then answer the next",
     "each tool call is its own round trip"),
    ("skip_the_failure", "catch the exception and drop that result block",
     "a tool that failed has no result to report"),
    ("stale_id", "reuse a tool_use_id from an earlier transcript",
     "the id is just a correlation string, so any id will do"),
]

# WHY the last column and not just the rule number: the exam asks which rule was
# violated, and the skill that survives the exam is reading an error backwards to
# the belief that produced it. Note that not one of these three messages mentions
# parallelism, fan-out, or the number of tools.
DIAGNOSES = [
    ("one_at_a_time", "rule 3", "2 of 3 pending ids unanswered",
     "a batching bug, and it says so"),
    ("skip_the_failure", "rule 3", "1 of 3 pending ids unanswered",
     "same diagnosis, different cause: error handling"),
    ("stale_id", "rule 2", "tool_result for an id no turn requested",
     "fires first, though an id is also missing"),
]


def main() -> None:
    transport, note = choose_transport(SCRIPT)
    present.banner(
        title="Three tools in one turn, and four ways to answer it",
        domain="D1 Agentic Architecture and Orchestration - 1.1",
        question="Where do N tool results go, and what about the one that failed?",
        expect="One correct arm in 2 requests, then three rejected requests.",
        note=note,
    )
    prompt = "Can I still refund order 4471, and where is it now?"

    present.rule("correct: every result, one user message")
    final, messages, iterations = fan_out(transport, prompt)
    print(f"\n  {iterations} iteration(s), {len(messages)} messages - the same")
    print("  count a SINGLE-tool turn produces in agentic_loop.py. Three tools")
    print("  cost one round trip, not three: that is what fan-out buys.")
    print(f"  Final: {text_of(final)[:150]}")

    for mode, what, belief in BROKEN:
        present.rule(f"broken: {what}")
        print(f"  the belief behind it: {belief}")
        # WHY a fresh ScriptedTransport per arm, and never the live one: the
        # counter runs against the script, so reusing one transport would kill
        # the second arm with script exhaustion and hide its rule violation. And
        # a broken arm stays scripted even when a credential resolves - the real
        # API would answer these with a 400, which would be better evidence than
        # the validator, and that comparison is an open gap in docs/status.md
        # rather than something to spend a stranger's quota on by default.
        try:
            fan_out(ScriptedTransport(SCRIPT), prompt, mode=mode)
            print("  ACCEPTED - which would mean the validator has a hole.")
        except TransportError as exc:
            present.paragraph(f"TransportError: {exc}", indent="     ")

    present.rule("what the error says vs what you did")
    present.table(("mode", "caught by", "message", "read it backwards"), DIAGNOSES)

    present.rule("the cost nobody quotes")
    present.paragraph(
        "The correct arm sent 2 requests where sequential calling would send 4, "
        "and that saving is real. What it pays for that with: the user message "
        "cannot be sent until every tool has returned, so the turn takes as long "
        "as the "
        "slowest one and one hanging tool stalls the whole answer. No timing was "
        "measured here - that claim would be SCRIPTED, which is worth nothing. "
        "tools_mcp/parallel_tools.py measured timing for real, one layer up.")

    present.rule()
    print("  LEARN  " + LESSON["learn"])


if __name__ == "__main__":
    main()
