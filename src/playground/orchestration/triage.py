"""
WHAT      A three-stage triage pipeline that works, with the reasoning for each
          boundary stated at the boundary. Free Python, then one constrained
          model call, then - only when the first two prove it necessary - one
          agent with a tool.
WHY       Every other orchestration demo here argues against a default. This one
          is the positive case: a decomposition that is right, and the rule that
          made it right. Without it the D1 material is a list of things not to
          do, anchored to nothing.
DOMAIN    D1 Agentic Architecture and Orchestration
TRADEOFF  Three stages mean three places to look when the answer is wrong, and a
          routing rule that can itself be wrong - a request misclassified at
          stage 2 never reaches the stage that could have handled it. You are
          buying cost and blast-radius control with debuggability.
ALTERNATIVE  Hand the whole thing to one agent with every tool attached. Fewer
          moving parts, genuinely simpler, and it pays full agent price for
          requests a regex could have rejected - and it can reach every tool on
          every request, including the ones it had no business touching.

Model: claude-haiku-4-5. Two calls per request at most, one when stage 2 settles
it, zero when stage 1 rejects it - five across the four requests below rather
than eight, as a consequence of the shape rather than an optimisation.

THE DESIGN RULE, which is the whole point of the file: give each stage exactly
the capability its question needs, and escalate only when the previous stage has
proved the escalation necessary. Capability means power and reach - tokens,
tools, freedom to choose - and the boundaries fall where the KIND of question
changes, not the subject matter. "A different topic" is not a reason to split;
"a different kind of answering" always is.

STAGE 3 NOTE, which argues for the design better than a clean run would have.
MEASURED across two runs: stages 1 and 2 gave identical results both times, stage
3 did not. Once it declined to use its tool at all, replying that the lookup
"requires authentication" and should be authorised interactively - for an
in-process tool with no transport, credentials or server to authorise. Same
code, options and prompt. MEASURED twice here, in two unrelated demos; the
cause is INFERRED and unconfirmable from this repo, most likely the model
reasoning about MCP from general knowledge rather than from the tool in front of
it.

The shape of that failure is the dangerous part: a `success` turn with zero tool
calls and a plausible wrong explanation, invisible to `subtype`, `is_error` and
`permission_denials` alike, so any pipeline assuming the tool ran carries it
forward silently. The rule that follows: if a step MUST call a tool, assert that
it did. Full write-up in docs/traps.md.

So unpredictability concentrates in the stage with the most capability - exactly
the stage this pipeline works hardest to avoid reaching. A regex cannot change
its mind and a closed vocabulary bounds how far a classification drifts. Not
luck: it is what "least capability that answers its kind" buys.
"""
import asyncio
import json
import re
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions, ClaudeSDKError, ResultMessage, create_sdk_mcp_server, query, tool,
)
from mockserver import state
from playground import teach

MODEL = "claude-haiku-4-5"

LESSON = {
    "domain": "D1 Agentic Architecture and Orchestration",
    "setup": "basics.check_auth passed. Read the three stage functions below "
             "before running, and for each one ask what question it answers.",
    "run": "uv run python -m playground.run orchestration.triage",
    "cost": "5 model calls across 4 requests - 2, 2, 1 and 0 respectively",
    "expect": "Four requests, four different paths. MEASURED twice, identical "
              "routing both times: one rejected by stage 1 for zero model calls, "
              "one settled by stage 2 alone, two escalated to stage 3 - five "
              "model calls where an unconditional pipeline would make eight. "
              "Stage 3 is the unreliable part: of four escalated calls across "
              "the two runs, one declined to use its tool. See the STAGE 3 NOTE.",
    "learn": "Put a boundary where the KIND of question changes - decidable by "
             "rule, decidable from the text, or decidable only by going and "
             "looking - and give each stage the least capability that answers "
             "its kind.",
}

# WHY: the closed vocabulary is declared once, here, because stage 2's schema and
# stage 3's routing rule must agree about it. Two copies of a vocabulary is how a
# router quietly stops being able to route to one of its branches.
INTENTS = ["status_question", "priority_complaint", "reassignment_request"]
NEEDS_LOOKUP = {"status_question", "priority_complaint"}

REQUESTS = [
    "What's happening with TCK-003? It's been quiet for days.",
    "TCK-002 is still open and it's just a typo, why is that not done yet?",
    "Please move TCK-007 over to lchen, rmoore is swamped.",
    "Can someone look at the thing with the login page?",
]

# WHY: a plain regex, not a model. Whether a string contains a ticket id is
# decidable, so a model here would add latency, cost and a failure mode to a
# question that already has an exact answer.
TICKET_ID = re.compile(r"\bTCK-\d{3}\b")


@tool("get_ticket", "Look up one ticket by id.",
      {"type": "object", "required": ["ticket_id"],
       "properties": {"ticket_id": {"type": "string"}}})
async def get_ticket(args: dict[str, Any]) -> dict[str, Any]:
    try:
        return {"content": [{"type": "text",
                             "text": json.dumps(state.get(args["ticket_id"]))}]}
    except KeyError:
        return {"content": [{"type": "text", "text": "no such ticket"}],
                "is_error": True}


def stage1_admit(request: str) -> str | None:
    """Decidable by rule. Returns a ticket id, or None to reject.

    BOUNDARY 1 is between "a rule decides this" and "language understanding
    decides this". Everything on this side is free, exact, unit-testable and
    cannot hallucinate. The temptation is to let the model do it too, since it
    is already being called - but then a malformed request costs the same as a
    real one, and the rejection becomes something you cannot test offline.
    """
    match = TICKET_ID.search(request)
    if match is None:
        return None
    # WHY: existence is checked here rather than being left to the tool in stage
    # 3. An id that does not exist is still a rule-decidable fact, and catching
    # it now means stages 2 and 3 can assume a valid subject.
    return match.group(0) if match.group(0) in state.TICKETS else None


async def stage2_classify(request: str) -> tuple[str | None, ResultMessage | None]:
    """Decidable from the text alone. One constrained call, no tools.

    BOUNDARY 2 is between "the answer is in what I was given" and "the answer is
    somewhere else". This stage has everything it needs in the request string,
    so it gets no tools at all - not as a restriction, but because there is
    nothing for a tool to contribute. A stage with tools it does not need will
    eventually use one.
    """
    schema = {"type": "object", "required": ["intent"], "additionalProperties": False,
              "properties": {"intent": {"type": "string", "enum": INTENTS}}}
    options = ClaudeAgentOptions(
        model=MODEL, max_turns=2,
        output_format={"type": "json_schema", "schema": schema},
    )
    result: ResultMessage | None = None
    try:
        async for message in query(prompt=f"Classify this request: {request}",
                                   options=options):
            if isinstance(message, ResultMessage):
                result = message
    except ClaudeSDKError as exc:
        print(f"    stage 2 raised: {type(exc).__name__}")
    if result is None or not result.result:
        return None, result
    raw = result.result
    payload = json.loads(raw) if isinstance(raw, str) else raw
    return payload.get("intent"), result


async def stage3_answer(request: str, ticket_id: str) -> tuple[str, ResultMessage | None]:
    """Decidable only by going and looking. An agent, with exactly one tool.

    BOUNDARY 3 is where control flow genuinely has to move to the model: it must
    decide what to fetch and how to use it, and that sequence is not knowable in
    advance. Note what it still does NOT get - one tool, a turn cap, and a
    subject that stages 1 and 2 already validated. Escalating capability is not
    the same as removing limits.
    """
    options = ClaudeAgentOptions(
        model=MODEL, max_turns=4,
        mcp_servers={"t": create_sdk_mcp_server(name="t", tools=[get_ticket])},
        allowed_tools=["mcp__t__get_ticket"],
        system_prompt="Look the ticket up and answer in one sentence. Be specific.",
    )
    reply, result = "", None
    try:
        async for message in query(
            prompt=f"Request about {ticket_id}: {request}", options=options
        ):
            if isinstance(message, ResultMessage):
                result = message
                reply = message.result or ""
    except ClaudeSDKError as exc:
        reply = f"(raised {type(exc).__name__})"
    return reply.strip(), result


async def main() -> None:
    teach.banner(LESSON)

    calls, rejected, answered = 0, [], []
    for request in REQUESTS:
        print(f"\n> {request}")

        ticket_id = stage1_admit(request)
        if ticket_id is None:
            print("  stage 1: rejected, no known ticket id - 0 model calls")
            rejected.append(request)
            continue
        print(f"  stage 1: admitted, subject {ticket_id}")

        intent, _ = await stage2_classify(request)
        calls += 1
        print(f"  stage 2: intent {intent!r}")

        if intent not in NEEDS_LOOKUP:
            print("  stage 3: not needed, the intent is actionable as it stands")
            answered.append((request, intent, None))
            continue

        reply, _ = await stage3_answer(request, ticket_id)
        calls += 1
        print(f"  stage 3: {reply}")
        answered.append((request, intent, reply))

    teach.closing(
        LESSON,
        observed=[
            f"{len(rejected)} of {len(REQUESTS)} requests were rejected by stage 1 "
            f"for zero model calls, by a regex and a dict that cannot be argued with.",
            f"{calls} model call(s) in total, against the {len(REQUESTS) * 2} an "
            f"unconditional two-stage pipeline would have made - and "
            f"{len([a for a in answered if a[2] is None])} request(s) stopped at "
            f"stage 2, where the classification was already the deliverable.",
            "Only the final stage held a tool, and exactly one - on a subject the "
            "earlier stages had already proved exists.",
        ],
        naive="The instinct when a task has parts is to split by SUBJECT - one "
              "step for tickets, one for users, one for billing. That produces "
              "stages that all look alike and all need everything. Split by the "
              "kind of question instead and they come out different shapes, "
              "which is the sign you cut in the right place: stage 1 has no "
              "model, stage 2 no tools, stage 3 exactly one.",
    )


if __name__ == "__main__":
    asyncio.run(main())
