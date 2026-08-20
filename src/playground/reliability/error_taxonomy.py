"""
WHAT      Four failure classes provoked deliberately and sorted by who can
          recover: the host, the environment, the caller, or nobody.
WHY       The instinct is one try/except around the agent call. Only one of these
          four is an exception at all, and two of the remaining three arrive as
          successful-looking tool results. Sorting by who can act is the
          difference between an agent that degrades and one that lies.
DOMAIN    D5 Context Management and Reliability
TRADEOFF  Four code paths and no single place to look when something breaks. A
          catch-all is genuinely simpler and genuinely wrong: it turns a
          reasoning failure, which needs validation, into a retry, which will
          cheerfully reproduce the same wrong answer.
ALTERNATIVE  If you truly cannot afford four paths, pick validation. An
          unvalidated success is more dangerous than a loud crash.

Model: claude-haiku-4-5, max_turns=3. The host case costs zero tokens.

TRANSPORT NOTE. flaky_search below is the same tool as mockserver.server's, with
the same state module and the same failure semantics, but served in-process
rather than over stdio. It was written for external_mcp.py, which could not be
completed in the environment this was written in - see the KNOWN_ISSUE there.
One thing genuinely differs. Over stdio the framework
catches a raised exception and delivers isError plus text; in-process the wrapper
below does that catching explicitly. The model sees the same thing either way,
which is why the coded prefixes matter more than the exception type - MEASURED
over stdio, the exception class does not cross the transport at all.
"""
import asyncio
import json
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions, ClaudeSDKError, ResultMessage, create_sdk_mcp_server, query, tool,
)
from mockserver import state
from playground import teach

MODEL = "claude-haiku-4-5"
OBSERVED: list[tuple[str, str]] = []

LESSON = {
    "domain": "D5 Context Management and Reliability",
    "setup": "basics.check_auth passed. Case 1 needs no network and no quota; "
             "cases 2 to 4 each make one call. The mock backend is deterministic "
             "- its first search per process always fails, so restart to re-arm.",
    "run": "uv run python -m playground.run reliability.error_taxonomy",
    "cost": "3 model calls; case 1 is free",
    "expect": "Four labelled sections, then a verdict listing which bucket each "
              "provoked failure landed in. Two distinct buckets means the "
              "taxonomy discriminates; one means it is decorative.",
    "learn": "Only one of these four failures is an exception you can catch - the "
             "other three arrive as ordinary-looking results - so the useful axis "
             "is not 'what went wrong' but 'who can act on it': the host, the "
             "environment, the caller, or nobody.",
}


def classify(text: str) -> str:
    """The taxonomy. Prefix-based, because that is all that survives a transport."""
    if state.UPSTREAM_CODE in text:
        return "ENVIRONMENT: retry the identical call"
    if state.ARGUMENT_CODE in text:
        return "ARGUMENTS: the caller must change something"
    return "UNCLASSIFIED"


@tool("flaky_search", "Search ticket titles. The backend is unreliable on first contact.",
      {"type": "object", "required": ["query"],
       "properties": {"query": {"type": "string"}, "limit": {"type": "string"}}})
async def flaky_search(args: dict[str, Any]) -> dict[str, Any]:
    try:
        rows = state.search(args["query"])
        limit = args.get("limit", "10")
        try:
            n = int(limit)
        except ValueError as exc:
            raise ValueError(
                f"{state.ARGUMENT_CODE}: limit must be an integer, got {limit!r}. "
                f"Retrying unchanged will fail identically."
            ) from exc
    except (state.UpstreamUnavailable, ValueError) as exc:
        # WHY: caught and returned as is_error rather than allowed to propagate.
        # That mirrors what the stdio server's framework does automatically, and
        # it keeps the failure inside the conversation where the model can act on
        # it. Note the class distinction is lost here exactly as it is on the
        # wire - only the message text reaches the model.
        OBSERVED.append((args["query"], classify(str(exc))))
        return {"content": [{"type": "text", "text": str(exc)}], "is_error": True}
    return {"content": [{"type": "text", "text": json.dumps(rows[:n])}]}


async def host_failure() -> None:
    """The host is broken. Python raises; the model never sees anything."""
    print("\n--- 1. HOST failure (zero tokens) ---")
    options = ClaudeAgentOptions(model=MODEL, cli_path="./no-such-claude-binary")
    try:
        async for _ in query(prompt="anything", options=options):
            pass
    except ClaudeSDKError as exc:
        # WHY: the SDK base class, not Exception. It covers CLINotFoundError,
        # ProcessError and CLIJSONDecodeError without swallowing your own bugs.
        print(f"raised {type(exc).__name__}, caught outside the agent loop")
        print("recovery: fix the host. No prompt change can help.")


async def _search_run(label: str, prompt: str) -> None:
    options = ClaudeAgentOptions(
        model=MODEL, max_turns=3,
        mcp_servers={"tickets": create_sdk_mcp_server(name="tickets",
                                                      tools=[flaky_search])},
        allowed_tools=["mcp__tickets__flaky_search"],
        system_prompt=(
            "Use the search tool. Pass any limit exactly as the user wrote it, "
            "verbatim, without converting words to digits. Report failures plainly."
        ),
    )
    # WHY this try exists, and it is the lesson of case 1 applied to itself: on a
    # limit, query() yields the ResultMessage and THEN raises. The first version
    # of this function had no try, so the raise escaped and the taxonomy verdict
    # at the end of main() never printed - the harness lost the very measurement
    # it was written to take. MEASURED 2026-08-20: subtype error_max_turns
    # arrived, then the process died with exit code 1.
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                print(f"[{label}] {message.subtype}, {message.num_turns} turns")
    except ClaudeSDKError as exc:
        print(f"[{label}] raised after the result: {type(exc).__name__}")


async def main() -> None:
    teach.banner(LESSON)

    await host_failure()

    # WHY: this is the first flaky_search call of the process, so state.search
    # raises. Deterministic, not probabilistic - restart to re-arm it.
    print("\n--- 2. ENVIRONMENT failure (first call always fails) ---")
    await _search_run("upstream", "Search the tickets for 'retry'.")

    # WHY: the backend is warm now, so any failure here has to come from the
    # argument. The weak schema types limit as a string, which is what lets a
    # word through in the first place.
    print("\n--- 3. ARGUMENTS failure (bad limit) ---")
    await _search_run("bad-arg", "Search the tickets for 'retry' with a limit of ten.")

    print("\n--- 4. REASONING failure (schema-valid, possibly wrong) ---")
    schema = {"type": "object", "required": ["parts", "total"],
              "additionalProperties": False,
              "properties": {"parts": {"type": "array", "items": {"type": "number"}},
                             "total": {"type": "number"}}}
    opts = ClaudeAgentOptions(model=MODEL, max_turns=3,
                              output_format={"type": "json_schema", "schema": schema})
    holds: bool | None = None
    # WHY the try, in the file that teaches this exact rule: case 4 sets a cap
    # like every other case, so it can raise like every other case. The first
    # version of this module was missing the same guard two functions up.
    try:
        async for message in query(
            prompt="Parts cost 12.50, 7.25 and 30.00. Return the list and their total.",
            options=opts,
        ):
            if isinstance(message, ResultMessage) and message.result:
                raw = message.result
                payload = json.loads(raw) if isinstance(raw, str) else raw
                # WHY: the schema guarantees shape, never arithmetic. This
                # invariant is the only thing between you and a confident wrong
                # number.
                expected = round(sum(payload["parts"]), 2)
                holds = expected == round(payload["total"], 2)
                print(f"payload: {payload}")
                print(f"sum invariant holds: {holds}")
    except ClaudeSDKError as exc:
        print(f"raised after the result: {type(exc).__name__}")

    print("\n--- taxonomy verdict ---")
    for query_text, bucket in OBSERVED:
        print(f"  {query_text!r:<12} -> {bucket}")
    buckets = {b for _, b in OBSERVED}
    if len(buckets) < 2:
        print("  BOTH LANDED IN THE SAME BUCKET - the taxonomy is decorative.")
    else:
        print(f"  {len(buckets)} distinct buckets: the taxonomy discriminates.")

    teach.closing(
        LESSON,
        observed=[
            "Case 1 raised a ClaudeSDKError before any token was spent. It is the "
            "only one of the four your try/except can see, and no prompt change "
            "could have helped it.",
            f"Cases 2 and 3 both came back as tool results with is_error set, "
            f"landing in {len(buckets)} distinct bucket(s): "
            f"{', '.join(sorted(b.split(':')[0] for b in buckets)) or 'none'}. "
            f"Same transport, same shape, opposite recovery.",
            f"Case 4 returned a schema-valid payload whose sum invariant "
            f"{'held' if holds else 'did NOT hold' if holds is not None else 'was not checked'}"
            f". Nothing in the type system could have told you either way.",
            "The discriminator that survived was the coded prefix in the message "
            "text. The exception CLASS did not survive - MEASURED over stdio, it "
            "does not cross the transport at all.",
        ],
        naive="The instinct is one try/except around the agent call, and it feels "
              "responsible. Count what it would have caught here: one case out of "
              "four. Worse, a catch-all converts a REASONING failure - case 4, "
              "the one that returns a confident wrong number - into a retry, and "
              "a retry reproduces the same class of answer. MEASURED here: the "
              "model also retried the ARGUMENTS failure even though the error "
              "text said in plain English that retrying unchanged would fail "
              "identically, and it burned through its turn budget doing it. An "
              "instruction not to retry is a hint, not a control.",
    )


if __name__ == "__main__":
    asyncio.run(main())
