"""
WHAT      One logical tool defined twice, once with a permissive schema and once
          with a constrained one, run against the same ambiguous prompt, with
          the arguments the model actually produced printed side by side.
WHY       A tool schema is prompt engineering with a type system attached, and
          only part of it is enforced. Knowing which part is the difference
          between a schema that constrains the model and one that only looks
          like it does.
DOMAIN    D4 Tool Design and MCP Integration
TRADEOFF  A tight schema buys validated arguments and removes a parsing step,
          but every enforced constraint is a bet on the future: the enum below
          has three sensors, and the day a fourth is installed the model must
          pick a wrong value or fail, with no way to say "none of these". The
          worse trap is the unenforced constraint - `minimum`, `maximum` and
          friends are accepted in silence and do nothing, so a schema can fail
          neither loudly nor gracefully but invisibly. This file used to carry
          three of them to illustrate that; they were removed, because a demo
          that models the bad pattern in code is a demo people copy.
ALTERNATIVE  Accept a free-form string and parse it host-side. Correct when the
          input space is genuinely open, such as a search query, and a trap when
          it is closed, such as a unit, a status, or an identifier.

Model: claude-haiku-4-5, two runs, max_turns=3 each.

Which keywords actually bind, per
<https://platform.claude.com/docs/en/build-with-claude/structured-outputs>
fetched 2026-08-20: the declared types, `enum`, `const`, `required`,
`additionalProperties: false`, `$ref`, `default` and the named string `format`s.
Numerical constraints (`minimum`, `maximum`, `multipleOf`) and string
constraints (`minLength`, `maxLength`) are listed as NOT supported. Strict and
non-strict tool use "share these limitations", so `strict: true` buys enforcement
guarantees, not a larger vocabulary. Measured 2026-08-20: unsupported keywords
raise no error - they are ignored, not rejected, which is the worse outcome.

So the strong schema below is strong on exactly four counts: the declared types,
the `enum`, the `required` list, and a description that carries what the schema
cannot. That is the honest inventory, and it is still enough to beat the weak
version comprehensively.

STILL OPEN, and it decides whether "leave them in as documentation" is defensible.
"Ignored" was established; "inert" was not. An unsupported keyword could be
stripped before the model ever sees the schema, or passed through as text the
model may read as a hint. Those are very different, and one run cannot tell them
apart - a model that returns a value satisfying the constraint anyway is evidence
of nothing. The discriminating test was attempted: a `minimum`/`maximum` pair on
`celsius` contradicting what the prompt implied, so a compliant answer would have
had to come from the schema. It did not discriminate, and how it failed matters
more than the question asked. MEASURED: the model never called the tool at all,
answering in prose that the MCP server "requires authentication before it can be
used" and pointing at connector settings - for the in-process server defined in
this very file, which has no transport, credentials or server to authorise.
Ended `subtype=success`, `num_turns=2`, zero tool calls.

That is the FIRST of two occurrences in this repo; the second hit
`orchestration/triage.py`, whose STAGE 3 NOTE is the fuller write-up, and
`docs/traps.md` carries it as a trap. Two things travel with it: a tool being
available is never a guarantee it will be used, and a refusal of this kind
arrives as an ordinary successful turn - no exception, no `is_error`, nothing
your error handling notices. The `CAPTURED` dict below is exactly the assertion
that catches it: when the model does not call the tool the list stays empty and
`main()` prints "the model never called the tool" instead of implying a result.
That is the only reason this file cannot lie to you about a run.

This repo therefore removed them rather than keeping them as documentation. That
is a decision taken under uncertainty, not a resolution: with the question open,
no claim can be made that they inform the model, and a line that reads as a
constraint while enforcing nothing survives review and gets copied. `pattern` is
a further step out - it appears in neither the supported nor the unsupported
list, so filing it with the string constraints is inference this repo does not
upgrade to documented.
"""
import asyncio
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKError,
    ResultMessage,
    create_sdk_mcp_server,
    query,
    tool,
)

from playground import teach

MODEL = "claude-haiku-4-5"

LESSON = {
    "domain": "D4 Tool Design and MCP Integration",
    "setup": "basics.check_auth passed. Read PROMPT and both @tool definitions "
             "below, and decide what you think each schema will extract.",
    "run": "uv run python -m playground.run tools_mcp.schema_design",
    "cost": "2 model calls, one per schema",
    "expect": "The same ambiguous sentence sent twice, then the arguments the "
              "model actually produced: one unparsed string from the weak "
              "schema, three typed fields from the strong one.",
    "learn": "A schema is prompt engineering with a type system attached, and "
             "only part of it is attached - types, enum, required and "
             "additionalProperties bind, everything else is a suggestion the "
             "platform accepts without a word and then ignores.",
}

# WHY: deliberately vague. "about 21 and a half", "half past two" and "the roof
# sensor" each force a formatting decision that only one of the two schemas
# actually constrains. A clean prompt would hide the difference entirely, which
# is why demos with tidy inputs teach nothing about schema design.
PROMPT = (
    "Log this reading from the roof sensor: it was about 21 and a half degrees "
    "at half past two this afternoon."
)

# WHY: both handlers write here instead of returning data to main(). A tool's
# return value goes to the model, not to the caller - capturing the *arguments*
# is the only way to see what the schema actually bought you.
CAPTURED: dict[str, list[dict[str, Any]]] = {"weak": [], "strong": []}


# WHY: the shorthand form. {"reading": str} expands to a one-property object
# schema with no constraints, no description and no required list. It is the
# fastest way to define a tool and the reason so many tools end up shaped badly.
@tool("log_reading", "Log a sensor reading.", {"reading": str})
async def weak_log(args: dict[str, Any]) -> dict[str, Any]:
    CAPTURED["weak"].append(args)
    return {"content": [{"type": "text", "text": "logged"}]}


@tool(
    "log_reading",
    # WHY: the description carries the units and the format, and it is doing more
    # work than it looks. Because the numeric and string constraints below are not
    # enforced, this sentence is the ONLY thing communicating "Celsius" and
    # "24-hour HH:MM" to the model. A description that said merely "temperature"
    # would leave the schema's decorative constraints as the sole guidance, which
    # is to say none.
    "Log one sensor reading. Temperature is degrees Celsius as a number. Time is "
    "24-hour HH:MM. Sensor must be one of the listed identifiers.",
    {
        "type": "object",
        "properties": {
            # ENFORCED. enum turns an open field into a closed one, and it is the
            # single highest-leverage constraint in the supported vocabulary - the
            # one most often left out because a bare string "works".
            "sensor": {"type": "string", "enum": ["roof", "basement", "intake"]},
            # `number` is the whole constraint. This field used to carry
            # minimum/maximum; they are documented as unsupported and measured to
            # be accepted without complaint, so they were removed rather than
            # annotated - see the docstring. Plausibility ranges belong in a
            # host-side check, not in a schema slot that reads as binding.
            "celsius": {"type": "number"},
            # Likewise: `pattern` is gone. It appears in neither the supported nor
            # the unsupported list, so whether it did anything is still open - see
            # the docstring - and a keyword whose effect is unknown is the last
            # thing that belongs in the demo about knowing which constraints bind.
            # The format is carried by the description above and by the field name.
            "time_hhmm": {"type": "string"},
        },
        # WHY: without required, the model may omit a field it is unsure about -
        # which is precisely the field you most needed it to commit to.
        "required": ["sensor", "celsius", "time_hhmm"],
        "additionalProperties": False,
    },
)
async def strong_log(args: dict[str, Any]) -> dict[str, Any]:
    CAPTURED["strong"].append(args)
    return {"content": [{"type": "text", "text": "logged"}]}


async def run(label: str, fn: Any) -> None:
    # WHY: a separate server per variant. Both tools are called log_reading, so
    # putting them on one server would collide - the server alias is what keeps
    # their fully-qualified names distinct.
    server_name = f"{label}_sensors"
    options = ClaudeAgentOptions(
        model=MODEL,
        max_turns=3,
        mcp_servers={server_name: create_sdk_mcp_server(name=server_name, tools=[fn])},
        allowed_tools=[f"mcp__{server_name}__log_reading"],
        # WHY: identical system prompt for both runs. If the prompt differed, any
        # behavioural difference could be attributed to the prose rather than the
        # schema, and the comparison would prove nothing.
        system_prompt="Log the reading with the tool. Do not ask clarifying questions.",
    )
    # WHY the try: two arms run back to back, and without a guard a cap in the
    # first would mean the second never runs - leaving a comparison with one
    # column, which reads as a result rather than as a missing measurement.
    try:
        async for message in query(prompt=PROMPT, options=options):
            if isinstance(message, ResultMessage) and message.is_error:
                print(f"[{label}] run ended in error: {message.subtype}")
    except ClaudeSDKError as exc:
        print(f"[{label}] raised after the result: {type(exc).__name__}")


async def main() -> None:
    teach.banner(LESSON)

    await run("weak", weak_log)
    await run("strong", strong_log)

    print(f"\nPrompt: {PROMPT}\n")
    for label in ("weak", "strong"):
        print(f"--- {label} schema ---")
        # WHY: an empty list is a real outcome, not a bug. A model given a tool it
        # cannot map onto the request will sometimes answer in prose instead, and
        # a vague schema makes that more likely.
        if not CAPTURED[label]:
            print("  the model never called the tool")
        for call in CAPTURED[label]:
            print(f"  {call}")

    weak, strong = CAPTURED["weak"], CAPTURED["strong"]
    teach.closing(
        LESSON,
        observed=[
            f"The weak schema produced {weak} - {len(weak[0]) if weak else 0} "
            f"field(s), and whatever structure is in there is a string you still "
            f"have to parse, in a format the model chose rather than you.",
            f"The strong schema produced {strong} - typed values you can use "
            f"without a parsing step and without a format negotiation.",
            f"sensor came back as "
            f"{strong[0].get('sensor') if strong else '(no call)'}, which the "
            f"enum forced. That single keyword did more of the work than "
            f"everything else in the schema combined.",
        ],
        naive="Reading that table, the obvious conclusion is 'the strong schema "
              "is strong because it is detailed'. Look at what is actually "
              "carrying the load. Celsius and the HH:MM format are communicated "
              "by the DESCRIPTION, not the schema, because the keywords that "
              "would express them - minimum, maximum, pattern - are documented "
              "as unsupported for this purpose and were accepted here without a "
              "word of complaint. They were removed from this file for that "
              "reason. So the honest inventory is four things: the declared "
              "types, the enum, the required list, and a sentence of prose. "
              "Design the schema for what binds and write the description for "
              "everything else - which is the reverse of the usual advice.",
    )


if __name__ == "__main__":
    asyncio.run(main())
