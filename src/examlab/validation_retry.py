"""
WHAT      A validate-then-retry loop over three failing extractions, where the
          retry request carries the document, the failed output and the specific
          errors - and one of the three cannot be fixed by retrying at all.
WHY       Retry-with-feedback works well enough that it gets applied to
          everything, including the case it cannot help: a field the source
          document does not contain. Those retries succeed at producing a value,
          which is worse than failing, because the second attempt looks like a
          correction. Telling the two apart before you spend the call is the
          skill, and it is decidable from the error, not from the document.
DOMAIN    D4 Prompt Engineering and Structured Output (20%),
          task statement 4.4
TRADEOFF  The "model" here is a function of the feedback it receives, written by
          this repo: given errors it returns the corrected extraction, except in
          the third case where it returns another fabrication no matter what.
          That makes the two outcomes deterministic and it also means this file
          demonstrates a policy, not a model tendency. How often a real retry
          fixes a format error is not measured and is not claimed.
ALTERNATIVE  Pydantic's `ValidationError.errors()`, which gives you field paths
          and messages already shaped for a retry prompt. The hand-rolled
          validator imported below produces strings instead, which is enough for
          the demo and less than you want in production.

Cost: free, 0 model calls. Reuses the schema and both validators from
`structured_output.py`, so the two files cannot disagree about what a failure is.
"""
from __future__ import annotations

from examlab import present
from examlab.structured_output import (
    EXTRACTION_TOOL,
    check_schema,
    check_semantics,
)

LESSON = {
    "domain": "D4 Prompt Engineering and Structured Output - 4.4",
    "setup": "Read structured_output.py first - this file reuses its schema and "
             "both of its validators.",
    "run": "uv run python -m playground.run examlab.validation_retry",
    "cost": "free - 0 model calls",
    "expect": "Three documents, all three reported valid by attempt 2. The "
              "third one is the lesson: it validated by inventing a value the "
              "source never contained, after being told not to infer.",
    "learn": "Retry fixes format and structure. Asked for information the "
             "source does not contain it does not fail - it fabricates, and the "
             "fabrication passes validation, because validation is the only "
             "signal the loop has. Classify the error before spending the call.",
}

MAX_ATTEMPTS = 3

CASES = {
    "format_error": {
        "source": "licence 900.00, support 240.00, total EUR 1140.00",
        "bad": {"currency": "EUR", "line_items": [{"label": "licence", "amount": 900.0},
                                                  {"label": "support", "amount": 240.0}],
                "stated_total": "1,140.00", "calculated_total": 1140.0,
                "confidence": "high"},
        "fixed": {"currency": "EUR", "line_items": [{"label": "licence", "amount": 900.0},
                                                    {"label": "support", "amount": 240.0}],
                  "stated_total": 1140.0, "calculated_total": 1140.0,
                  "confidence": "high"},
        "class": "format - a number arrived as a formatted string",
    },
    "semantic_error": {
        "source": "licence 900.00, support 240.00, VAT 216.60, total EUR 1356.60",
        "bad": {"currency": "EUR", "line_items": [{"label": "licence", "amount": 900.0},
                                                  {"label": "support", "amount": 240.0}],
                "stated_total": 1356.60, "calculated_total": 1140.0,
                "confidence": "high"},
        "fixed": {"currency": "EUR", "line_items": [{"label": "licence", "amount": 900.0},
                                                    {"label": "support", "amount": 240.0},
                                                    {"label": "VAT", "amount": 216.60}],
                  "stated_total": 1356.60, "calculated_total": 1356.60,
                  "confidence": "high"},
        "class": "structural - a line item was dropped, and the totals said so",
    },
    "absent_from_source": {
        "source": "consulting 500, paid in cash (no currency printed anywhere)",
        "bad": {"currency": "other", "line_items": [{"label": "consulting", "amount": 500.0}],
                "stated_total": 500.0, "calculated_total": 500.0, "confidence": "high"},
        # WHY there is no "fixed" entry: there is no correct extraction to
        # return. The document does not name a currency, so every attempt must
        # either fabricate one or fill currency_detail with something it read
        # nowhere. This is the row the demo exists for.
        "fixed": None,
        "class": "absent - the document never states the field",
    },
}


def validate(payload: dict) -> list[str]:
    """Both layers at once. Schema first, because a type error makes the
    semantic checks meaningless - summing a string is a different error."""
    schema_errors = check_schema(EXTRACTION_TOOL["input_schema"], payload)
    return schema_errors or check_semantics(payload)


def retry_prompt(source: str, failed: dict, errors: list[str]) -> str:
    """The three things a retry request must carry, and why each one.

    Drop any of them and the retry degrades: without the document the model
    corrects the shape and keeps the wrong values; without the failed
    extraction it starts over and reproduces the same mistake; without the
    specific errors it has to guess what you objected to.
    """
    return (
        "Your previous extraction failed validation. Correct it.\n\n"
        f"SOURCE DOCUMENT\n{source}\n\n"
        f"YOUR PREVIOUS OUTPUT\n{failed}\n\n"
        f"VALIDATION ERRORS\n" + "\n".join(f"- {e}" for e in errors) + "\n\n"
        "If a field is not stated in the source document, return null for it. "
        "Do not infer a value to make validation pass."
    )


def scripted_model(case: dict, attempt: int, fabrication: int) -> dict:
    """Stands in for the model. Returns the corrected output if one exists.

    The `fabrication` counter is what makes the third case honest: a real model
    asked again for a value that is not there does not refuse, it produces
    another plausible one. Returning the identical bad payload would understate
    the problem, because a caller could then detect the loop by comparison.
    """
    if attempt == 1 or case["fixed"] is None:
        payload = dict(case["bad"])
        if case["fixed"] is None and attempt > 1:
            payload["currency_detail"] = ["CHF", "cash (CHF)", "Swiss francs"][fabrication % 3]
        return payload
    return dict(case["fixed"])


def run(name: str, case: dict) -> tuple[str, ...]:
    """Validate, retry with feedback, and report what "valid" actually meant.

    The last branch is the one worth reading. When the fixture declares that no
    correct extraction exists (`fixed is None`), a passing validation cannot be
    a correction - so the loop reports it as a fabrication that validated. That
    distinction is available here only because the fixture knows the ground
    truth. **A real pipeline does not**, which is the finding: nothing inside a
    validate-retry loop can tell a correction from an invention, because
    validation is the only signal it has and the invention satisfies it.
    """
    present.rule(f"{name} - {case['class']}")
    print(f"  source   {case['source']}")
    payload: dict = {}
    errors: list[str] = []
    kind = case["class"].split(" - ")[0]
    for attempt in range(1, MAX_ATTEMPTS + 1):
        payload = scripted_model(case, attempt, attempt - 2)
        errors = validate(payload)
        print(f"  attempt {attempt}  " + ("valid" if not errors else errors[0][:66]))
        if not errors:
            break
        if attempt < MAX_ATTEMPTS:
            prompt = retry_prompt(case["source"], payload, errors)
            print(f"            retry prompt: {len(prompt)} chars, "
                  f"{len(errors)} error(s) quoted verbatim")
    if errors:
        return (name, kind, str(MAX_ATTEMPTS), "still invalid",
                "fix the schema, not the prompt")
    if case["fixed"] is None:
        print(f"            ...and it 'passed' by returning "
              f"currency_detail={payload.get('currency_detail')!r}, which appears")
        print("            nowhere in the source. The retry prompt even said not")
        print("            to infer. Validation cannot see the difference.")
        return (name, kind, str(attempt), "VALID BY FABRICATION",
                "nullable field; route to human")
    return (name, kind, str(attempt), "resolved", "retry was the right tool")


def main() -> None:
    present.banner(
        title="Validate, retry with feedback, and know when not to",
        domain="D4 Prompt Engineering and Structured Output - 4.4",
        question="Which validation failures does another attempt actually fix?",
        expect="Two resolved on attempt 2, one unresolvable and fabricating.",
        note=("TRANSPORT: none. The stand-in model is a function of the "
              "feedback, written by this repo. It demonstrates the retry POLICY "
              "and measures no model behaviour whatsoever."),
    )
    rows = [run(name, case) for name, case in CASES.items()]
    present.rule("which failures retry can reach")
    present.table(("case", "class", "attempts", "outcome", "correct response"), rows)
    print("\n  READ ROW THREE. It did not fail. It passed, on attempt 2, by")
    print("  inventing a currency the document never printed - and the retry")
    print("  prompt had explicitly told it not to infer. A validate-retry loop")
    print("  has exactly one signal, and the fabrication satisfies it, so the")
    print("  loop reports success. This file can label it only because the")
    print("  fixture holds the ground truth; your pipeline will not.")
    print("\n  So the classifier is the error class, decided BEFORE the retry.")
    print("  A type error or a cross-field disagreement means the information")
    print("  was present and the output was wrong - retry. A field the source")
    print("  never states means the schema asks for something that does not")
    print("  exist, and retrying does not fail, it fabricates.")
    print("\n  Two design consequences, both in the blueprint:")
    print("   - nullable fields for anything the source may omit, so 'absent'")
    print("     is a legal answer and fabrication is not the only legal move;")
    print("   - a detected_pattern field on each finding, so when a human")
    print("     dismisses one you can group the dismissals by cause instead of")
    print("     counting them.")
    present.rule()
    print("  LEARN  " + LESSON["learn"])


if __name__ == "__main__":
    main()
