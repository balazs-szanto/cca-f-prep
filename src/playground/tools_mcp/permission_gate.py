"""
WHAT      A can_use_tool callback that inspects a destructive call, looks up the
          record it targets, and refuses it on a rule the schema cannot express.
WHY       allowed_tools is a static decision made before the run starts: a tool
          is either available or it is not. can_use_tool is a dynamic decision
          made per call, with the actual arguments in hand, which is the only
          place you can say "deleting is fine, deleting THAT is not".
DOMAIN    D4 Tool Design and MCP Integration
TRADEOFF  The gate runs in your process on every call, so it is a latency and a
          correctness liability: a slow or throwing callback stalls or breaks the
          agent loop. It also sees one call at a time, so it cannot stop a
          sequence that is destructive only in aggregate - three individually
          permitted deletions that together empty a queue.
ALTERNATIVE  Enforce the rule inside the tool body. Simpler, unbypassable, and it
          costs you the audit record: the model then learns of the refusal as an
          ordinary tool result, indistinguishable from the record not existing,
          and nothing lands in ResultMessage.permission_denials.

Model: claude-haiku-4-5, max_turns=3.

WHY this serves delete_ticket in-process instead of spawning src/mockserver:
the mock exposes the same tool over stdio, and that is the better illustration.
It could not be attached in the environment this was written in (see
external_mcp.py, which declares that as a KNOWN_ISSUE). The state module is
imported from mockserver so the data and the destructive operation are identical;
only the transport differs. That swap is itself the D4 lesson: an in-process
server is not subject to whatever governs external ones, because from the outside
there is nothing to inspect - which is convenient, and is exactly why the
external kind is the one that tends to get governed.
"""
import asyncio
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKError,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    ToolPermissionContext,
    create_sdk_mcp_server,
    query,
    tool,
)
from mockserver import state
from playground import teach

MODEL = "claude-haiku-4-5"

LESSON = {
    "domain": "D4 Tool Design and MCP Integration",
    "setup": "basics.check_auth passed. Read gate() and then read the "
             "allowed_tools argument in main() - the relationship between those "
             "two is the entire demo.",
    "run": "uv run python -m playground.run tools_mcp.permission_gate",
    "cost": "1 model call",
    "expect": "Ten seeded tickets, a request to delete four of them, and then: "
              "the priority-1 ones still present, the others gone, and two "
              "entries in permission_denials naming the refused ids.",
    "learn": "can_use_tool is the only place a rule can depend on the actual "
             "arguments of a call - and it is skipped entirely for any tool an "
             "allow rule already auto-approved, which turns a guard into "
             "decoration without a single error message.",
}

# WHY: a rule about data, not about ids. A hardcoded deny-list would be a worse
# demo because allowed_tools could almost express it; "never delete a priority 1"
# depends on a field the caller never sends, so the gate must look it up.
PROTECTED_PRIORITY = 1


@tool(
    "delete_ticket",
    "Permanently delete one ticket by id. Cannot be undone.",
    {
        "type": "object",
        "properties": {
            "ticket_id": {"type": "string"},
            "confirm": {"type": "boolean"},
        },
        "required": ["ticket_id", "confirm"],
    },
)
async def delete_ticket(args: dict[str, Any]) -> dict[str, Any]:
    # WHY: no priority check in here, deliberately. If the gate is the control,
    # the gate has to be the thing that stops it - a second check in the body
    # would mask a failure in the mechanism this file exists to demonstrate.
    if not args.get("confirm"):
        return {"content": [{"type": "text", "text": "refused: confirm was not true"}]}
    try:
        removed = state.delete(args["ticket_id"])
    except KeyError:
        return {"content": [{"type": "text", "text": f"no ticket {args['ticket_id']}"}]}
    return {"content": [{"type": "text", "text": f"deleted {removed['id']}"}]}


async def gate(
    tool_name: str, input_data: dict[str, Any], context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    # WHY: endswith, not equality. The name arrives fully qualified as
    # mcp__tickets__delete_ticket, and matching the whole string would couple this
    # policy to the server alias chosen further down.
    if tool_name.endswith("__delete_ticket"):
        ticket_id = input_data.get("ticket_id", "")
        try:
            ticket = state.get(ticket_id)
        except KeyError:
            # WHY: allow it through. A nonexistent id is the tool's problem to
            # report, not a policy violation, and denying here would teach the
            # model that the gate is what rejects unknown ids.
            return PermissionResultAllow(updated_input=input_data)
        if ticket["priority"] == PROTECTED_PRIORITY:
            return PermissionResultDeny(
                # WHY: written as an instruction, not an error code. "cannot be
                # deleted, continue with the rest" produces a sensible next move;
                # "PERMISSION_DENIED" produces a retry or a stall.
                message=(
                    f"{ticket_id} is priority {PROTECTED_PRIORITY} and cannot be "
                    f"deleted. Skip it and continue with the remaining tickets."
                ),
                # WHY: interrupt=False lets the agent absorb the refusal and carry
                # on. interrupt=True aborts the whole turn, which is what you want
                # when a denial means the plan itself was wrong.
                interrupt=False,
            )
    # WHY: the allow branch returns updated_input, so the gate is also a rewrite
    # point - clamp a limit, redirect a path, inject a tenant id. Veto is only
    # half of what this callback can do.
    return PermissionResultAllow(updated_input=input_data)


async def main() -> None:
    teach.banner(LESSON)

    before = {t: state.TICKETS[t]["priority"] for t in sorted(state.TICKETS)}
    print(f"seed: {len(before)} tickets, priorities {before}\n")

    options = ClaudeAgentOptions(
        model=MODEL,
        max_turns=3,
        mcp_servers={"tickets": create_sdk_mcp_server(name="tickets",
                                                      tools=[delete_ticket])},
        # WHY delete_ticket is NOT in allowed_tools, and this is the whole trap:
        # an allow rule AUTO-APPROVES, and only "tools not covered by allow rules
        # trigger your canUseTool callback" (code.claude.com/docs/en/agent-sdk/
        # agent-loop, fetched 2026-08-20). Listing the tool here silences the gate
        # completely. MEASURED: the first version of this file did list it, and
        # every protected ticket was deleted with permission_denials empty - a
        # guard that reported success while enforcing nothing.
        #
        # The tool is still available: mcp_servers is what exposes it. The
        # allowlist only decides what runs WITHOUT asking.
        #
        # The SDK detects this exact mistake and says so. MEASURED at connect
        # time, zero tokens: the buggy config emits CanUseToolShadowedWarning,
        # "can_use_tool will not be invoked for: mcp__tickets__delete_ticket",
        # and this config emits nothing. It went unnoticed for one full run
        # because the run was piped with 2>$null to hide unrelated stderr noise.
        # Python warnings go to stderr. Do not silence a channel you have not read.
        allowed_tools=[],
        # WHY: default mode routes unapproved calls to the callback. In "dontAsk"
        # the same omission would deny everything instead.
        permission_mode="default",
        can_use_tool=gate,
        system_prompt="Delete each ticket with the tool. Do not ask for confirmation.",
    )

    # WHY: priority-1 and non-priority-1 ids interleaved. A prompt asking only for
    # forbidden deletions would show a refusal but not that the agent recovers and
    # finishes the rest of the job.
    prompt = "Delete these tickets: TCK-002, TCK-003, TCK-005, TCK-010."

    result: ResultMessage | None = None
    # WHY the try: this run has MEASURED num_turns=6 against a cap of 3 and
    # still finished success, so the relationship between the counter and the cap
    # gives no useful warning. A guard is the only thing that makes a cap safe.
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                result = message
                survivors = sorted(state.TICKETS)
                print(f"still present : {survivors}")
                print(f"deleted       : {sorted(set(before) - set(survivors))}")
                print(f"denials       : {message.permission_denials}")
                print(f"[{message.subtype}, {message.num_turns} turns]")
    except ClaudeSDKError as exc:
        print(f"raised after the result: {type(exc).__name__}")

    if result is None:
        raise RuntimeError("The stream ended without a ResultMessage.")

    asked = ["TCK-002", "TCK-003", "TCK-005", "TCK-010"]
    protected = [t for t in asked if before.get(t) == PROTECTED_PRIORITY]
    gone = sorted(set(before) - set(state.TICKETS))
    teach.closing(
        LESSON,
        observed=[
            f"The agent was asked to delete {asked}. Of those, {protected} were "
            f"priority {PROTECTED_PRIORITY} and {gone} were actually deleted.",
            f"permission_denials holds {len(result.permission_denials)} entry/"
            f"entries. That list is the audit record, and it exists only because "
            f"the refusal happened in the permission layer rather than inside "
            f"the tool body.",
            f"The run still ended {result.subtype!r} in {result.num_turns} "
            f"turns: a denial is something the agent absorbs and works around, "
            f"not a crash, because gate() returned interrupt=False.",
            "The rule the gate enforced - never delete a priority 1 - depends on "
            "a field the caller never sends. No allowlist entry could have "
            "expressed it, because an allowlist matches names and arguments, not "
            "the record behind them.",
        ],
        naive="The natural way to write this is to put the tool in allowed_tools "
              "AND pass the gate, on the theory that two layers are safer than "
              "one. That configuration enforces nothing at all. The documented "
              "order is hooks, deny, ask, mode, allow, canUseTool - an allow "
              "rule resolves the call at step five, so step six never runs. "
              "MEASURED: the first version of this file did exactly that, every "
              "protected ticket was deleted, permission_denials came back empty, "
              "and the run reported success. The SDK does emit a "
              "CanUseToolShadowedWarning about it, on stderr, which is easy to "
              "pipe away. A guard that fails open and reports success is worse "
              "than no guard, because you stop looking.",
    )


if __name__ == "__main__":
    asyncio.run(main())
