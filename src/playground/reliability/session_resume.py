"""
WHAT      One session that learns a fact, a resumed session that still knows it,
          and a fresh session that does not - run back to back.
WHY       "Multi-turn" means two different things and people conflate them. Inside
          one connected client, continuity is free. Across process restarts it is
          a deliberate act: you must capture a session id and pass it back. Nobody
          discovers this gently; they discover it when production forgets.
DOMAIN    D1 Agentic Architecture and Orchestration, task statement 1.7
TRADEOFF  Resuming replays the transcript, so you re-pay for that history on
          every resumed turn and inherit whatever compaction already discarded.
          It also resumes mistakes: a wrong assumption made in turn 2 is now
          load-bearing context you cannot edit out without forking.
ALTERNATIVE  Re-seed a fresh session with a short state summary you own. Cheaper
          and auditable, and it loses the model's own reasoning trail - which is
          usually a feature, occasionally a serious loss.

Model: claude-haiku-4-5, max_turns=2. Three calls total.

What does NOT survive a resume, and is worth internalising: the transcript is
the only thing persisted. In-process Python state, tool closures, and SDK MCP
server instances are rebuilt from your code, so a resumed session with a
different tool list is a different agent wearing the same history.
"""
import asyncio

from claude_agent_sdk import (
    AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, ResultMessage, TextBlock,
)

from playground import teach

MODEL = "claude-haiku-4-5"

LESSON = {
    "domain": "D1 Agentic Architecture and Orchestration - 1.7",
    "setup": "basics.check_auth passed. SECRET below is a fact no model can know "
             "from training, which is the only reason step 3 is a fair test.",
    "run": "uv run python -m playground.run reliability.session_resume",
    "cost": "4 model calls across three sessions",
    "expect": "Step 1 states the fact and recalls it. Step 2, a brand new client "
              "given the session id, recalls it too, at a visibly higher token "
              "count. Step 3, identical code without the id, does not know it.",
    "learn": "'Multi-turn' means two unrelated things: continuity inside one open "
             "client is free, and continuity across a process boundary is a "
             "deliberate act that replays - and re-bills - the whole transcript.",
}

# WHY: a fact the model cannot possibly know from training. If the recall question
# could be answered from general knowledge, step 3 would appear to succeed and the
# whole demonstration would invert.
SECRET = "the deployment window is Thursday 02:00 UTC"
RECALL = "What is the deployment window? Answer in one short sentence."


async def ask(client: ClaudeSDKClient, prompt: str) -> str:
    await client.query(prompt)
    reply = ""
    # WHY: receive_response() stops at the end of this exchange.
    # receive_messages() would keep yielding across subsequent turns and hang here.
    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    reply += block.text
        elif isinstance(message, ResultMessage):
            # WHY: the session id is only reliably available on the result. Capture
            # it here or you have no handle to resume with later.
            usage = message.usage or {}
            # WHY: cache_read is included because a replayed transcript arrives as
            # cached input. Without it a resumed turn looks as cheap as a fresh one.
            billed = usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
            reply += f"\n   [session {message.session_id} | in+cache {billed:,} tok]"
    return reply.strip()


def options(resume: str | None = None) -> ClaudeAgentOptions:
    # WHY: one factory for all three runs so the only variable is `resume`. If the
    # model or system prompt differed between them, a difference in recall could
    # be blamed on that instead of on session continuity.
    return ClaudeAgentOptions(
        model=MODEL, max_turns=2, resume=resume,
        # WHY: "if you do not know, say so" matters. Without it the model may
        # invent a plausible deployment window in step 3, and a confident
        # hallucination looks exactly like successful recall.
        system_prompt="Answer in one short sentence. If you do not know, say so.",
    )


async def main() -> None:
    teach.banner(LESSON)

    print("--- 1. first session: state a fact, then recall it in the same session ---")
    async with ClaudeSDKClient(options=options()) as client:
        first = await ask(client, f"Remember this: {SECRET}. Reply with 'noted'.")
        print(f"   {first}")
        # WHY: this second question inside the same `async with` is the cheap kind
        # of continuity - no session id, no replay, the connection simply stayed
        # open. Most "multi-turn" tutorials only ever show this case.
        same = await ask(client, RECALL)
        print(f"   {same}")
        session_id = same.rsplit("[session ", 1)[-1].split(" ")[0]

    # WHY: the client is now closed. Everything below is a new connection, which
    # is what makes this a fair stand-in for a process restart.
    print(f"\n--- 2. resumed session (resume={session_id[:8]}...) ---")
    async with ClaudeSDKClient(options=options(resume=session_id)) as client:
        resumed = await ask(client, RECALL)
        print(f"   {resumed}")

    print("\n--- 3. fresh session, same code, no resume ---")
    async with ClaudeSDKClient(options=options()) as client:
        fresh = await ask(client, RECALL)
        print(f"   {fresh}")

    # WHY: parsed back out of the printed line rather than returned separately.
    # Ugly, and deliberate - it keeps ask() returning exactly what is displayed,
    # so the closing block cannot quote a number the reader never saw.
    def billed(reply: str) -> str:
        return reply.rsplit("| in+cache ", 1)[-1].rstrip("]")

    knew = "Thursday" in resumed
    teach.closing(
        LESSON,
        observed=[
            f"Step 2 was a brand new client object with no memory of step 1, and "
            f"it {'recalled' if knew else 'did NOT recall'} the deployment "
            f"window. The only thing carried across was the string "
            f"{session_id[:8]}...",
            f"Step 3 ran byte-identical code with resume=None and answered: "
            f"{fresh.splitlines()[0][:90]}",
            f"Token cost of the two: step 2 billed {billed(resumed)}, step 3 "
            f"billed {billed(fresh)}. The difference is the transcript being "
            f"replayed into the model.",
        ],
        naive="Sessions feel like they belong to the model, as if the id were a "
              "key into memory Anthropic is holding for you. It is closer to the "
              "opposite: resuming replays the transcript, so you pay for that "
              "history on every resumed turn and you inherit whatever compaction "
              "already threw away. You also inherit the mistakes - a wrong "
              "assumption made in turn 2 is now load-bearing context you cannot "
              "edit out without forking. And note what did NOT come back: only "
              "the transcript persists, so in-process Python state, tool "
              "closures and SDK MCP server instances are rebuilt from your code. "
              "Resume a session against a different tool list and you have a "
              "different agent wearing the same history. That last point is "
              "INFERRED from how the SDK is constructed, not measured here.",
    )


if __name__ == "__main__":
    asyncio.run(main())
