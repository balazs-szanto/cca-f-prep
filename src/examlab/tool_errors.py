"""
WHAT      Four error categories returned as structured tool results, the generic
          alternative, and a host-side recovery policy run against both so the
          difference is a behaviour rather than an assertion.
WHY       "Return structured errors" is advice nobody argues with and few
          implement, because the generic version works: the call fails, the
          agent apologises, the ticket gets closed. What it costs is invisible
          until you try to write the recovery, and then you find there is
          nothing to branch on. This file makes that concrete by writing the
          recovery twice - once over metadata, once over a string - and showing
          that the second one cannot be written at all.
DOMAIN    D2 Tool Design and MCP Integration (18%), task
          statement 2.2; and D5 (15%), task statement 5.3
TRADEOFF  The recovery policy here is host-side Python reading `isRetryable`.
          Real agents often let the MODEL read the error text and decide, which
          is more flexible and less predictable. Choosing the host-side version
          makes the demo deterministic and slightly misrepresents where the
          decision usually lives - so the closing block says which parts
          transfer to the model-decides design and which do not.
ALTERNATIVE  Let the model see the error and pick the next action. That is the
          normal Agent SDK shape and `playground/reliability/error_taxonomy.py`
          covers the failure classes from that side. This file is the tool
          author's side of the same boundary.

Cost: free. No model call at all - every response is a tool result this file
constructs, which is the whole subject.
"""
from __future__ import annotations

from examlab import present
from examlab.contract import tool_result

LESSON = {
    "domain": "D2 Tool Design and MCP Integration - 2.2",
    "setup": "Read STRUCTURED and GENERIC below, then recover(). The two tool "
             "surfaces return the same failures with different metadata.",
    "run": "uv run python -m playground.run examlab.tool_errors",
    "cost": "free - 0 model calls",
    "expect": "Six cases against both tool surfaces. The structured surface "
              "retries exactly one of them and explains the rest; the generic "
              "surface retries all six or none, because it cannot tell.",
    "learn": "An error is retryable, or a policy violation, or a bad argument, "
             "or a missing permission - and a valid empty result is none of "
             "those. Collapsing them into one string does not lose detail, it "
             "loses the decision.",
}

# WHY: `is_error` on the block is the transport-level flag - the result still
# comes back as a tool_result, the turn continues, and the model reads the
# content. It is NOT an exception and it does not stop anything. The categories
# below live inside the content because the flag has room for exactly one bit.
STRUCTURED = {
    "timeout": {
        "error": "inventory service did not respond within 5000ms",
        "errorCategory": "transient", "isRetryable": True, "retryAfterMs": 2000,
    },
    "bad_argument": {
        "error": "order_id must be an integer; received 'ORD-4471'",
        "errorCategory": "validation", "isRetryable": False,
        "hint": "strip the 'ORD-' prefix and pass 4471",
    },
    "policy": {
        "error": "refund of 812.00 exceeds the 500.00 auto-approval limit",
        "errorCategory": "business", "isRetryable": False,
        "customerMessage": "This refund needs a supervisor's approval.",
        "nextAction": "escalate_to_human",
    },
    "forbidden": {
        "error": "this API token may not write to accounts in region EU",
        "errorCategory": "permission", "isRetryable": False,
        "nextAction": "escalate_to_human",
    },
    "not_found": {
        "error": "no order with id 9999",
        "errorCategory": "validation", "isRetryable": False,
    },
    # WHY: not an error at all, and the row that catches most designs out. A
    # successful query with nothing to report must not be reachable through the
    # same channel as a failure, or the agent cannot tell "there are no matching
    # orders" from "I could not look".
    "empty": {"results": [], "status": "ok", "matched": 0},
}

GENERIC = {name: {"error": "Operation failed"} for name in STRUCTURED}
GENERIC["empty"] = {"error": "Operation failed"}


def recover(payload: dict) -> tuple[str, str]:
    """The host's decision, given one tool result. Returns (action, why).

    Read the order of the branches. `status` is checked before `error`, because
    a successful empty result must never fall through into failure handling -
    and it is the branch a generic error surface makes unreachable.
    """
    if payload.get("status") == "ok":
        return "report", f"query succeeded with {payload.get('matched')} matches"
    category = payload.get("errorCategory")
    if payload.get("isRetryable"):
        return "retry", f"{category}, retry after {payload.get('retryAfterMs')}ms"
    if payload.get("nextAction") == "escalate_to_human":
        return "escalate", f"{category}, and the caller cannot resolve it"
    if category == "validation":
        return "fix and re-call", f"{category}: {payload.get('hint', 'no hint given')}"
    if category is None:
        # WHY: the honest answer for an unclassified failure, and the reason the
        # generic column below is uniform. "Guess" is not a policy; it is the
        # absence of one, and naming it that way is the finding.
        return "guess", "no category, no retryable flag - nothing to branch on"
    return "give up", f"{category}, not retryable, no next action"


def main() -> None:
    present.banner(
        title="Structured tool errors, and the recovery you cannot write without them",
        domain="D2 Tool Design and MCP Integration - 2.2",
        question="What can the caller decide, given only what the tool returned?",
        expect="Six identical failures, two tool surfaces, one usable column.",
        note=("TRANSPORT: none. Every payload below is constructed by this file "
              "and the recovery policy is ordinary Python. Nothing here is a "
              "measurement; the subject is what a tool's return value makes "
              "possible, and that is decidable by reading it."),
    )
    present.rule("the same six failures, twice")
    rows: list[tuple[str, ...]] = []
    for name in STRUCTURED:
        structured_action, structured_why = recover(STRUCTURED[name])
        generic_action, _ = recover(GENERIC[name])
        rows.append((name, structured_action, generic_action, structured_why[:46]))
    present.table(("case", "structured -> action", "generic -> action",
                   "why (structured only)"), rows)

    print("\n  The middle column is the point. Six distinct situations, one")
    print("  answer, and that answer is 'guess'. Note especially the last row:")
    print("  a successful query with no matches is reported as a failure, so an")
    print("  agent will retry it, and retrying it will succeed at finding")
    print("  nothing, forever.")

    present.rule("what goes on the wire")
    ok = tool_result("toolu_01", '{"results":[],"status":"ok","matched":0}')
    bad = tool_result("toolu_02", '{"error":"...","errorCategory":"transient",'
                      '"isRetryable":true}', is_error=True)
    print(f"  success, empty : {ok}")
    print(f"  failure        : {bad}")
    print("\n  Both are tool_result blocks and both continue the turn. `is_error`")
    print("  is one bit for the transport; everything a caller acts on is in the")
    print("  content, which is why the content needs a shape.")

    present.rule("where this transfers, and where it does not")
    print("  Transfers: the categories, the retryable flag, the separation of")
    print("  empty-result from access-failure, and customerMessage as a field")
    print("  distinct from `error` - one is for a person, one is for a log.")
    print("  Does not transfer: the branch order. When the MODEL reads the error")
    print("  instead of your code, ordering is a prompt problem, and a")
    print("  well-shaped payload is necessary but no longer sufficient.")
    print("\n  Subagent rule that follows from the same fields: recover locally")
    print("  from anything isRetryable, and propagate the rest upward WITH what")
    print("  was attempted and any partial results. A coordinator that receives")
    print("  'search unavailable' has been told less than the subagent knew.")
    present.rule()
    print("  LEARN  " + LESSON["learn"])


if __name__ == "__main__":
    main()
