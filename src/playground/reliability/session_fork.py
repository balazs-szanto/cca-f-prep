"""
WHAT      One baseline session, two forks off it, and then a re-resume of the
          baseline itself - to find out what a fork inherits, what it hides from
          its sibling, and whether it writes back into its parent.
WHY       `fork_session` is the answer to the problem `session_resume.py` ends
          on. Resuming inherits mistakes: a wrong assumption made in turn 2 is
          load-bearing context you cannot edit out. Forking is how you keep an
          expensive shared analysis and then try two incompatible things against
          it without either one contaminating the other or the original. That is
          a three-way isolation claim, and each of the three is separately
          testable, which is why this demo asks four questions rather than one.
DOMAIN    D1 Agentic Architecture and Orchestration, task statement 1.7
TRADEOFF  A fork still replays the whole baseline transcript, so it costs the
          same per turn as a resume - the saving is that you only paid for the
          analysis ONCE, not that the branches are cheap. Two forks off a large
          baseline therefore cost roughly twice a resume, not half. If the
          branches are long-lived, re-seeding each with a written summary is
          cheaper and loses the model's reasoning trail.
ALTERNATIVE  Run the analysis once, write the conclusion down yourself, and start
          two fresh sessions from that text. Auditable, cheaper per turn, and it
          throws away everything the model concluded but did not say. Prefer it
          when the baseline is stale; prefer forking when it is expensive and
          still true.

Model: claude-haiku-4-5, max_turns=2. Four calls total.

This file lives in `reliability/` next to `session_resume.py` because they are
one subject, and it is labelled D1 because the blueprint puts session state in
1.7 rather than in D5. Directory and domain are different questions here, as
they already are in `basics/`.
"""
import asyncio

from claude_agent_sdk import (
    AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, ResultMessage, TextBlock,
)

from playground import teach

MODEL = "claude-haiku-4-5"

LESSON = {
    "domain": "D1 Agentic Architecture and Orchestration - 1.7",
    "setup": "basics.check_auth passed, and read session_resume.py first - this "
             "demo is the answer to the problem that one ends on.",
    "run": "uv run python -m playground.run reliability.session_fork",
    "cost": "4 model calls: one baseline, one per fork, one re-resume of the parent",
    "expect": "Both forks know BASELINE. Fork B does not know BRANCH_A. The "
              "re-resumed parent does not know BRANCH_A either - which is the "
              "assertion worth the fourth call. Watch the session ids: a fork "
              "gets a new one, a plain resume does not.",
    "learn": "A fork inherits the transcript and then diverges: siblings cannot "
             "see each other and neither writes back into the parent. It is "
             "copy-on-write for context - and you still re-pay the baseline on "
             "every branch turn, so the saving is on the analysis, not the run.",
}

# WHY two facts a model cannot know from training, and deliberately unrelated to
# each other. If BRANCH_A were guessable from BASELINE, fork B answering it
# correctly would look like a leak when it was inference, and the whole isolation
# claim would be unfalsifiable.
BASELINE = "the payment retry ceiling is 7 attempts"
BRANCH_A = "branch A renames the ceiling to max_retry_budget"

# WHY one question that tests inheritance and isolation together: it halves the
# call count, and it makes the two results impossible to report separately by
# accident. A session that knows neither is a broken fork; one that knows both is
# a leak; one that knows only the first is correct.
PROBE = (
    "Answer both parts in one short sentence each, and say 'I do not know' for "
    "either part you were not told. (1) What is the payment retry ceiling? "
    "(2) What does branch A rename it to?"
)


async def ask(client: ClaudeSDKClient, prompt: str) -> tuple[str, str]:
    """Send one prompt; return (reply text, session id).

    The session id is returned rather than parsed back out of the printed line -
    the difference from `session_resume.py`, which parses it, and the reason is
    that this demo needs to COMPARE ids across four runs. A string that has to
    be re-extracted from display text is a string that will be extracted wrongly
    the first time the format changes.
    """
    await client.query(prompt)
    reply = ""
    session_id = ""
    # WHY receive_response() and not receive_messages(): the former stops at the
    # end of this exchange. The latter keeps yielding and hangs here.
    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    reply += block.text
        elif isinstance(message, ResultMessage):
            session_id = message.session_id or ""
            usage = message.usage or {}
            # WHY cache_read is added in: a replayed transcript arrives as cached
            # input, so without it a forked turn looks as cheap as a fresh one.
            billed = usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
            reply += f"\n   [in+cache {billed:,} tok]"
    return reply.strip(), session_id


def options(*, resume: str | None = None, fork: bool = False) -> ClaudeAgentOptions:
    # WHY one factory: `resume` and `fork_session` are the only two variables in
    # this demo. If the model, the cap or the system prompt differed between
    # runs, any difference in recall could be blamed on those instead.
    #
    # WHY the system prompt insists on admitting ignorance: without it the model
    # will invent a plausible rename for part (2), and a confident hallucination
    # is indistinguishable from a context leak. That instruction is what makes
    # the isolation claim falsifiable at all.
    return ClaudeAgentOptions(
        model=MODEL, max_turns=2, resume=resume, fork_session=fork,
        system_prompt="Answer in one short sentence per part. If you were not "
                      "told something, say 'I do not know' rather than guessing.",
    )


def knows(reply: str, needle: str) -> bool:
    """Whether a reply contains the distinctive token of a fact."""
    return needle.lower() in reply.lower()


async def main() -> None:
    teach.banner(LESSON)

    print("--- 1. baseline session: the expensive shared analysis ---")
    async with ClaudeSDKClient(options=options()) as client:
        _, baseline_id = await ask(
            client, f"Remember this: {BASELINE}. Reply with 'noted'.")
    print(f"   baseline session {baseline_id[:8]}...")

    print("\n--- 2. fork A: resume the baseline with fork_session=True ---")
    async with ClaudeSDKClient(
            options=options(resume=baseline_id, fork=True)) as client:
        a_reply, fork_a_id = await ask(
            client, f"Remember also: {BRANCH_A}. Then state the payment retry "
                    f"ceiling in one short sentence.")
        print(f"   {a_reply}")
    print(f"   fork A session  {fork_a_id[:8]}...")

    print("\n--- 3. fork B: same baseline, same flag, different branch ---")
    async with ClaudeSDKClient(
            options=options(resume=baseline_id, fork=True)) as client:
        b_reply, fork_b_id = await ask(client, PROBE)
        print(f"   {b_reply}")
    print(f"   fork B session  {fork_b_id[:8]}...")

    # WHY this fourth call exists: without it the demo shows that a sibling
    # cannot see a sibling, and says nothing about the parent. "Fork A wrote its
    # turn somewhere" is compatible with both isolation and with the parent being
    # quietly extended, and only one of those makes forking safe.
    print("\n--- 4. the parent, re-resumed WITHOUT fork_session ---")
    async with ClaudeSDKClient(
            options=options(resume=baseline_id, fork=False)) as client:
        parent_reply, parent_id = await ask(client, PROBE)
        print(f"   {parent_reply}")
    print(f"   parent session  {parent_id[:8]}...")

    a_kept = knows(a_reply, "7") or knows(a_reply, "seven")
    b_kept = knows(b_reply, "7") or knows(b_reply, "seven")
    b_leaked = knows(b_reply, "max_retry_budget")
    p_kept = knows(parent_reply, "7") or knows(parent_reply, "seven")
    p_leaked = knows(parent_reply, "max_retry_budget")
    new_ids = len({baseline_id, fork_a_id, fork_b_id}) == 3

    teach.closing(
        LESSON,
        observed=[
            f"Inheritance: fork A {'kept' if a_kept else 'LOST'} the baseline "
            f"fact and fork B {'kept' if b_kept else 'LOST'} it. Both were built "
            f"from the same id, {baseline_id[:8]}..., and neither was told it.",
            f"Sibling isolation: fork B {'LEAKED' if b_leaked else 'did not know'} "
            f"branch A's rename. Fork A had already written it into its own "
            f"transcript before B ran, so this is an ordering test as well as an "
            f"isolation one.",
            f"Parent integrity: the re-resumed baseline "
            f"{'LEAKED' if p_leaked else 'did not know'} branch A's rename, and "
            f"{'kept' if p_kept else 'LOST'} its own fact. This is the assertion "
            f"the fourth call bought.",
            f"Session ids: baseline {baseline_id[:8]}, fork A {fork_a_id[:8]}, "
            f"fork B {fork_b_id[:8]}, plain resume {parent_id[:8]}. Three "
            f"distinct ids for the forks: {new_ids}.",
        ],
        naive="Forking sounds like a cheap operation on a pointer, and the id "
              "changing encourages that reading. It is closer to a copy: the new "
              "session starts with the parent's whole transcript, so every turn "
              "on every branch re-pays for it. What forking saves is the analysis "
              "itself - you ran it once - and what it buys is that a branch "
              "cannot corrupt the baseline you would otherwise have to re-derive. "
              "The corollary people miss: forking does not make a stale baseline "
              "fresh. If the files it analysed have changed, both branches "
              "inherit the same wrong picture with more confidence than a fresh "
              "session would have, and the fix is a new session seeded with a "
              "summary you wrote, not another fork. Choose resume when the prior "
              "context is mostly still true, fork when it is true and you need "
              "two futures from it, and start fresh when it is stale.",
    )


if __name__ == "__main__":
    asyncio.run(main())
