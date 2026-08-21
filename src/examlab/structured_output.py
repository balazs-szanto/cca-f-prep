"""
WHAT      An extraction tool whose input schema IS the output contract, a
          validator for it, and three extractions - one clean, one schema-valid
          and semantically wrong, one that fabricates a value to satisfy a
          required field.
WHY       "Use tool_use with a JSON schema" is the right answer to "how do I get
          reliable structured output", and it is routinely over-read. What a
          schema buys is that the shape is legal. What it does not buy is that
          the contents are true, that two fields agree with each other, or that
          a value the document never contained is absent - and the second
          extraction below is valid against the schema while being wrong about
          money, which is the failure that reaches production.
DOMAIN    D4 Prompt Engineering and Structured Output (20%),
          task statement 4.3
TRADEOFF  The validator here is about forty lines of stdlib rather than Pydantic
          or jsonschema. That keeps this package dependency-free and means it
          implements only the keywords the demo needs - type, required, enum,
          nullable unions, additionalProperties. Anything else in a schema is
          silently unchecked, which is a worse property than a real validator
          has and is stated here so nobody ports it.
ALTERNATIVE  Pydantic, which the blueprint names. `model_validate` gives you the
          error objects the retry loop in `validation_retry.py` wants, with
          field paths, for free. Use it in anything real; it is absent here only
          to keep the runtime dependency list at zero.

Cost: free. The extractions are SCRIPTED - fabricated tool inputs chosen to
exercise the three outcomes. Nothing here measures how often a model does this.
"""
from __future__ import annotations

from typing import Any

from examlab import present

LESSON = {
    "domain": "D4 Prompt Engineering and Structured Output - 4.3",
    "setup": "Read SCHEMA field by field and ask of each one: required or "
             "nullable, and what happens if the document is silent about it?",
    "run": "uv run python -m playground.run examlab.structured_output",
    "cost": "free - 0 model calls, extractions are fabricated",
    "expect": "Three extractions. One clean. One that passes every schema check "
              "and gets the money wrong. One that invents an invoice number "
              "because the field was required and the document had none.",
    "learn": "A schema constrains shape, and shape is not correctness. Make "
             "fields nullable when the source may be silent, and put the "
             "cross-field check in your code - the schema cannot express it.",
}

# WHY: `input_schema` on a tool the model is FORCED to call is how you guarantee
# schema-shaped output. tool_choice={"type":"tool","name":"record_invoice"}
# removes the "model answered in prose instead" failure entirely - see
# tool_choice.py for why that force must not survive into the next request.
EXTRACTION_TOOL = {
    "name": "record_invoice",
    "description": (
        "Record the fields of exactly one invoice. Call this once per document. "
        "Every field that the document does not state must be null - do not "
        "infer, calculate or carry a value over from another invoice."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            # WHY nullable rather than required: a required string with no source
            # value leaves the model one legal move, which is to invent one.
            # Extraction number three below is that move.
            "invoice_number": {"type": ["string", "null"]},
            "issued": {"type": ["string", "null"], "description": "ISO 8601 date."},
            "currency": {"type": "string", "enum": ["EUR", "USD", "GBP", "other"]},
            "currency_detail": {
                "type": ["string", "null"],
                "description": "Required when currency is 'other'; the raw string.",
            },
            "line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "amount": {"type": "number"},
                    },
                    "required": ["label", "amount"],
                    "additionalProperties": False,
                },
            },
            # WHY both: `stated_total` is what the document claims, and
            # `calculated_total` is what the line items add up to. Asking for
            # both turns a silent arithmetic error into a visible disagreement,
            # and it is the cheapest semantic guard there is.
            "stated_total": {"type": "number"},
            "calculated_total": {"type": "number"},
            "confidence": {"type": "string", "enum": ["high", "medium", "low", "unclear"]},
        },
        "required": ["currency", "line_items", "stated_total",
                     "calculated_total", "confidence"],
        "additionalProperties": False,
    },
}

EXTRACTIONS: dict[str, dict[str, Any]] = {
    "clean": {
        "invoice_number": "INV-2026-0184", "issued": "2026-07-30",
        "currency": "EUR", "currency_detail": None,
        "line_items": [{"label": "licence", "amount": 900.0},
                       {"label": "support", "amount": 240.0}],
        "stated_total": 1140.0, "calculated_total": 1140.0, "confidence": "high",
    },
    "schema_valid_wrong_money": {
        "invoice_number": "INV-2026-0185", "issued": "2026-08-02",
        "currency": "EUR", "currency_detail": None,
        "line_items": [{"label": "licence", "amount": 900.0},
                       {"label": "support", "amount": 240.0}],
        "stated_total": 1140.0, "calculated_total": 1140.0, "confidence": "high",
    },
    "fabricated_required_field": {
        "invoice_number": "INV-2026-0001",
        "issued": None, "currency": "other", "currency_detail": None,
        "line_items": [{"label": "consulting", "amount": 500.0}],
        "stated_total": 500.0, "calculated_total": 500.0, "confidence": "high",
    },
}

# WHY the second extraction's numbers look fine above: they are internally
# consistent and disagree with the SOURCE. That is the case a schema, a validator
# and a cross-field check all pass, and only comparing against the document
# catches - which is what `confidence` and human review exist for.
SOURCES = {
    "clean": "licence 900.00, support 240.00, total EUR 1140.00",
    "schema_valid_wrong_money": "licence 900.00, support 240.00, VAT 216.60, "
                                "total EUR 1356.60",
    "fabricated_required_field": "consulting 500 (no invoice number printed, "
                                 "amounts in Swiss francs)",
}


def check_schema(schema: dict, value: Any, path: str = "$") -> list[str]:
    """Validate `value` against the subset of JSON Schema this demo uses."""
    errors: list[str] = []
    types = schema.get("type")
    allowed = types if isinstance(types, list) else [types]
    actual = ("null" if value is None else
              "array" if isinstance(value, list) else
              "object" if isinstance(value, dict) else
              "boolean" if isinstance(value, bool) else
              "number" if isinstance(value, (int, float)) else
              "string" if isinstance(value, str) else "unknown")
    if actual == "integer":
        actual = "number"
    if types and actual not in allowed and not (actual == "number" and "integer" in allowed):
        return [f"{path}: expected {'|'.join(map(str, allowed))}, got {actual}"]
    if value is None:
        return errors
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in enum {schema['enum']}")
    if actual == "object":
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key}: required field missing")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in schema.get("properties", {}):
                    errors.append(f"{path}.{key}: not allowed by the schema")
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                errors.extend(check_schema(sub, value[key], f"{path}.{key}"))
    elif actual == "array" and "items" in schema:
        for index, item in enumerate(value):
            errors.extend(check_schema(schema["items"], item, f"{path}[{index}]"))
    return errors


def check_semantics(payload: dict) -> list[str]:
    """The checks a schema cannot express, because they relate fields.

    None of these is a type error and none of them would be caught by `strict`.
    They are the whole reason "tool use eliminates JSON errors" must not be read
    as "tool use eliminates errors".
    """
    errors: list[str] = []
    items = payload.get("line_items") or []
    summed = round(sum(i.get("amount", 0) for i in items), 2)
    if summed != round(payload.get("calculated_total", 0), 2):
        errors.append(f"calculated_total {payload.get('calculated_total')} is not "
                      f"the sum of the line items ({summed})")
    if round(payload.get("stated_total", 0), 2) != summed:
        errors.append(f"stated_total {payload.get('stated_total')} disagrees with "
                      f"the line items ({summed}) - a line is missing or wrong")
    if payload.get("currency") == "other" and not payload.get("currency_detail"):
        errors.append("currency is 'other' but currency_detail is null - the "
                      "escape hatch was used and not filled in")
    return errors


def main() -> None:
    present.banner(
        title="tool_use as a schema, and the three things a schema cannot buy",
        domain="D4 Prompt Engineering and Structured Output - 4.3",
        question="What is still wrong with an extraction that validates?",
        expect="One clean, one schema-valid and wrong, one fabricated value.",
        note=("TRANSPORT: none. The three extractions are SCRIPTED - written by "
              "this repo to exercise one outcome each. How often a real model "
              "produces each is not measured here and is not claimed."),
    )
    for name, payload in EXTRACTIONS.items():
        present.rule(name)
        print(f"  source     {SOURCES[name]}")
        schema_errors = check_schema(EXTRACTION_TOOL["input_schema"], payload)
        semantic_errors = check_semantics(payload)
        print(f"  schema     {'PASS' if not schema_errors else schema_errors}")
        print(f"  semantic   {'PASS' if not semantic_errors else ''}")
        for error in semantic_errors:
            print(f"             - {error}")
        if name == "schema_valid_wrong_money":
            print("  verdict    Passes both. The VAT line was dropped, so the")
            print("             extraction is self-consistent and disagrees with")
            print("             the document. No amount of schema work finds this;")
            print("             only comparison against the source does.")
        elif name == "fabricated_required_field":
            print("  verdict    invoice_number was nullable and got a plausible")
            print("             value anyway - the guard is the description, not")
            print("             the type. currency='other' with a null detail is")
            print("             the same failure caught one layer down.")

    present.rule("what each layer actually catches")
    present.table(
        ("layer", "catches", "misses"),
        [("schema / strict", "wrong types, unknown keys, bad enum",
          "everything about meaning"),
         ("cross-field check", "totals that disagree, unfilled escape hatches",
          "self-consistent extractions of the wrong numbers"),
         ("comparison to source", "dropped and invented lines",
          "nothing - but it needs the source, which downstream does not have"),
         ("human review", "the rest", "scale")])
    present.rule()
    print("  LEARN  " + LESSON["learn"])


if __name__ == "__main__":
    main()
