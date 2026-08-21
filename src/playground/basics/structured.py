"""
WHAT      Force the model to answer as JSON matching a schema, then validate the
          payload host-side before trusting it.
WHY       Prompt-based JSON instructions are fragile: the model can add prose,
          wrap the object in markdown fences, or drop a field. output_format
          moves the requirement out of the prompt and into the request, where it
          is enforced rather than requested.
DOMAIN    D4 Prompt Engineering and Structured Output, feeding into D5 Reliability
TRADEOFF  A schema constrains shape, never meaning. Every field can be present
          and correctly typed while the content is wrong - see
          reliability/error_taxonomy.py, where a schema-valid answer fails an
          arithmetic check. Schemas remove parsing bugs, not reasoning bugs.
ALTERNATIVE  Ask for JSON in the prompt and parse defensively. Cheaper to write,
          and you will spend the savings on stripping code fences.

Model: claude-haiku-4-5, max_turns=2. Two, not one: MEASURED 2026-08-20, an
otherwise identical call with no output_format completes at max_turns=1, so
producing the structured answer is itself what consumes the extra turn.

INFERRED, and only inferred: the likely mechanism is that structured output is
implemented as a forced tool call, which would make it a tool-use turn and
reconcile the observation with the documented "tool-use turns only". Nothing in
the documentation says this and nothing here tested it - so if you are sizing a
cap, size it against a measurement of your own call, not against this guess.

A second measurement from this file, which is the more useful one: it has
reported num_turns=3 against max_turns=2 and still finished `success`. The
counter and the cap are not measuring the same thing, so the gap between them
tells you nothing about how close you are to the limit. See traps.md.
"""
import asyncio
import json

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKError, ResultMessage, query

from playground import teach

MODEL = "claude-haiku-4-5"

LESSON = {
    "domain": "D4 Prompt Engineering and Structured Output, feeding D5 Reliability",
    "setup": "basics.check_auth passed. Read SCHEMA below before running - the "
             "prompt deliberately says nothing about JSON.",
    "run": "uv run python -m playground.run basics.structured",
    "cost": "1 model call",
    "expect": "A nine-key JSON object about Paris, pretty-printed and already "
              "parsed, followed by one summary line. No prose, no code fences, "
              "and no keys you did not ask for.",
    "learn": "output_format enforces the SHAPE of an answer from outside the "
             "prompt, and that is all it enforces - the keywords you would reach "
             "for to constrain a value are accepted and ignored, so every "
             "constraint on meaning has to be checked host-side.",
}

# WHY: this schema doubles as a cheat-sheet for the JSON Schema vocabulary, and
# every keyword in it is one the platform actually supports. It used to carry
# minimum/maximum on four fields; those are documented as NOT supported
# (platform.claude.com/docs/en/build-with-claude/structured-outputs, fetched
# 2026-08-20) and measured to be accepted and ignored rather than rejected.
#
# They were removed rather than annotated. A line that reads as a constraint but
# constrains nothing is worse than an absent one: it survives review, and the
# next person to add a field copies the pattern. If you need a range enforced,
# check it host-side after parsing - which is what the validation below is for.
SCHEMA: dict = {
    "type": "object",
    "properties": {
        "capital":               {"type": "string"},
        "country":               {"type": "string"},
        "population_millions":   {"type": "number"},
        "life_expectancy_years": {"type": "number"},
        # WHY: integer, not number - it rules out 1892.5 at the schema level
        # rather than leaving you to catch it. Negative values mean BC.
        "founded_year":          {"type": "integer"},
        "is_coastal":            {"type": "boolean"},
        # WHY: enum pins the model to a fixed vocabulary. This is the single
        # highest-leverage constraint available - see tools_mcp/schema_design.py
        # for what the same field looks like without it.
        "hemisphere":            {"type": "string", "enum": ["northern", "southern"]},
        "official_languages":    {"type": "array", "items": {"type": "string"}},
        # WHY: objects nest to any depth, and each level repeats the same three
        # keys - type, properties, required. There is no special syntax for
        # nesting; it is the same schema grammar applied again.
        "coordinates": {
            "type": "object",
            "properties": {
                # WHY no minimum/maximum here either, even though latitude has an
                # obvious one: unsupported is unsupported, and a plausible range
                # is exactly where a dead constraint is least likely to be noticed.
                "latitude":  {"type": "number"},
                "longitude": {"type": "number"},
            },
            "required": ["latitude", "longitude"],
            "additionalProperties": False,
        },
    },
    # WHY: everything is required. An optional field the model omits would sail
    # through the check below while leaving the payload unusable downstream, so
    # "optional" here would mean "silently broken later".
    "required": ["capital", "country", "population_millions", "life_expectancy_years",
                 "founded_year", "is_coastal", "hemisphere", "official_languages",
                 "coordinates"],
    # WHY: additionalProperties False makes the contract closed. Without it the
    # model may invent extra keys, which is harmless until something downstream
    # iterates the dict and meets a field nobody designed for.
    "additionalProperties": False,
}


async def main() -> None:
    teach.banner(LESSON)

    # WHY: output_format is a request-level setting, not a prompt. Note that the
    # prompt below says nothing about JSON at all - it does not need to.
    options = ClaudeAgentOptions(
        model=MODEL, max_turns=2,
        output_format={"type": "json_schema", "schema": SCHEMA},
    )

    payload: dict | None = None
    result: ResultMessage | None = None

    # WHY the try: max_turns is set, and a cap yields the result and then raises.
    # It has never fired here - but note that this file has measured num_turns=3
    # against a cap of 2 and still succeeded, so the margin is not what it looks.
    try:
        async for message in query(
            prompt="Give me facts about the capital city of France.",
            options=options,
        ):
            # WHY: structured output lands on the final ResultMessage, not in the
            # AssistantMessage text blocks. Reading the text blocks here would
            # give you the model's prose, which with output_format set is usually
            # empty.
            if isinstance(message, ResultMessage) and message.subtype == "success":
                result = message
                raw = message.result
                # WHY: result is typed str | None but arrives already-parsed in
                # some SDK versions. Normalising both cases costs one line and
                # removes a class of upgrade breakage.
                payload = json.loads(raw) if isinstance(raw, str) else raw
    except ClaudeSDKError as exc:
        print(f"raised after the result: {type(exc).__name__}")

    if payload is None:
        raise RuntimeError("Agent finished without a successful result.")

    # WHY: validate anyway. The schema is enforced upstream, but this code is the
    # last place that can fail loudly rather than propagate a bad shape onward -
    # and it is cheap insurance against the schema silently not being applied.
    missing = [k for k in SCHEMA["required"] if k not in payload]
    if missing:
        raise ValueError(f"Response is missing required keys: {missing}")

    print("Validated response:")
    print(json.dumps(payload, indent=2))
    print(f"\n{payload['capital']} - {payload['population_millions']}M people, "
          f"languages: {', '.join(payload['official_languages'])}")

    teach.closing(
        LESSON,
        observed=[
            f"All {len(SCHEMA['required'])} required keys were present and the "
            f"host-side check found nothing missing - and the prompt never used "
            f"the word JSON.",
            f"hemisphere came back {payload['hemisphere']!r}, which is one of the "
            f"two values the enum allows. That field is constrained; the enum is "
            f"one of the few keywords that genuinely binds.",
            f"latitude came back {payload['coordinates']['latitude']}. Nothing in "
            f"the schema restricted it to a real latitude - the minimum/maximum "
            f"pair that would express that is documented as unsupported, so this "
            f"number is plausible by the model's judgement alone.",
            f"The run finished in {result.num_turns} turns with subtype "
            f"{result.subtype!r}." if result else "No ResultMessage was captured.",
        ],
        naive="The natural next move after seeing a schema work is to add "
              "minimum, maximum, minLength or a pattern and assume they bind "
              "too. They do not. They are not rejected either - no error, no "
              "warning, the run looks identical. That is the worse of the two "
              "possible behaviours, because a schema that fails loudly teaches "
              "you in one run while one that silently drops half its constraints "
              "passes review and misleads every reader after you.",
    )


asyncio.run(main())
