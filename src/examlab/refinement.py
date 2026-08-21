"""
WHAT      A prose specification against three input/output examples on the same
          transformation, then the round-trip arithmetic for fixing interacting
          defects one at a time versus all at once.
WHY       This repo argued twice, in writing, that task statement 3.5 could not be
          demonstrated, only described, because every technique in it is a
          property of how a person drives a session. That was right about three of
          the four and wrong about the fourth. Whether to batch fixes or sequence
          them is not a matter of style: it follows from whether the fixes touch
          the same lines, and a dependency graph makes the round-trip count a
          calculation. The examples-versus-prose half is still an assertion, and
          is marked as one.
DOMAIN    D3 Claude Code Configuration and Workflows (20%), task statement 3.5
TRADEOFF  Half this file is arithmetic and half is an authored comparison, which
          is an uncomfortable mix in one module. Splitting them would put four
          lines of dependency-graph code in a file of its own and separate the
          two halves of one task statement, so they stay together and each half
          says which it is. Read the SPEC block as a worked example, not evidence.
ALTERNATIVE  The rest of 3.5 - test-driven iteration and the interview pattern -
          is written up in `docs/d3-claude-code.md` rather than faked here. Both
          are session-driving habits whose outcome is a transcript, and a
          transcript is not something this repo can score.

Cost: free. No transport, no model call.
"""
from __future__ import annotations

from examlab import present

LESSON = {
    "domain": "D3 Claude Code Configuration and Workflows - 3.5",
    "setup": "Read PROSE_SPEC and EXAMPLES, then decide which of the four TRICKY "
             "inputs each one determines the answer for.",
    "run": "uv run python -m playground.run examlab.refinement",
    "cost": "free - 0 model calls",
    "expect": "The prose spec settles none of four edge cases; three examples "
              "settle three and leave a range undetermined. Then a fix graph "
              "with 5 dependency edges where sequencing costs 9 round trips "
              "against 2, and a second graph where batching is wrong.",
    "learn": "A prose spec is ambiguous exactly where you did not think to be "
             "precise, and examples are cheaper than the precision. Batch fixes "
             "that touch the same code and sequence fixes that do not - the test "
             "is the dependency, never the count.",
}

# The transformation both arms are trying to specify: normalise a free-text
# quantity into a number plus a unit. Chosen because it is small enough to hold
# in your head and still has four genuinely undetermined edges.
PROSE_SPEC = (
    "Normalise the quantity field. Convert informal measurements into a numeric "
    "value and a standard unit. Be consistent, handle edge cases sensibly, and "
    "use your judgement for ambiguous cases."
)

EXAMPLES = [
    ('"2 1/2 cups"', '{"value": 2.5, "unit": "cup"}',
     "a mixed fraction becomes a decimal; the unit is singularised"),
    ('"a pinch"', '{"value": null, "unit": "pinch"}',
     "an unquantified amount keeps its unit and takes a null value - it is not "
     "an error, and it is not 1"),
    ('"330ml (11.2 fl oz)"', '{"value": 330, "unit": "ml"}',
     "when two units are given, keep the metric one and drop the conversion "
     "rather than emitting both"),
]

# WHY these four: each is a decision the prose spec does not make. `determined`
# says whether the three examples above settle it. The fourth is the honest row -
# examples generalise, and they do not cover everything either.
TRICKY = [
    ("\"1/4 tsp\"", "fraction with no whole part", True,
     "example 1 fixes fractions and singular units"),
    ("\"to taste\"", "no quantity at all", True,
     "example 2 fixes null-with-unit for unquantified amounts"),
    ("\"2 lb (900 g)\"", "dual unit, imperial first", True,
     "example 3 fixes dual units, and says metric wins regardless of order"),
    ("\"3-4 tbsp\"", "a RANGE, not a point value", False,
     "no example shows a range. The schema has one `value` field, so the model "
     "must pick, average or fail, and nothing tells it which"),
]

# A dependency graph over fixes. Two fixes are dependent when applying one
# changes the code the other is about; that is the only test that matters and it
# is a property of the diff, not of how many fixes there are.
FIX_SETS = {
    "interacting": {
        "fixes": [
            ("F1", "change apply_discount to take a fraction, not a percentage"),
            ("F2", "update the three callers that pass a whole number"),
            ("F3", "round the total to 2dp instead of truncating"),
            ("F4", "add the regression test for the undercharge"),
        ],
        # F2 depends on F1's signature; F3 depends on F1's output scale;
        # F4 asserts on the result of all three.
        "depends": {"F2": ["F1"], "F3": ["F1"], "F4": ["F1", "F2", "F3"]},
    },
    "independent": {
        "fixes": [
            ("G1", "fix the typo in the CLI help text"),
            ("G2", "add the missing index on orders.created_at"),
            ("G3", "bump the request timeout from 5s to 30s"),
        ],
        "depends": {},
    },
}


def sequential_round_trips(fixes: list[tuple[str, str]], depends: dict) -> int:
    """One request per fix, plus one re-request for every fix a change invalidates.

    A fix applied after something it depends on has to be revisited, because the
    code it was written against moved underneath it. That rework is the cost
    sequencing pays and batching does not.
    """
    rework = sum(len(v) for v in depends.values())
    return len(fixes) + rework


def batched_round_trips(fixes: list[tuple[str, str]], depends: dict) -> int:
    """One request carrying every fix, plus one verification pass.

    Two regardless of the fix count, which is the appeal, and it is only correct
    when the fixes genuinely interact - otherwise a single message invites the
    model to conflate unrelated changes into one edit you cannot review.
    """
    return 2


def main() -> None:
    present.banner(
        title="Examples over prose, and when to batch a fix instead of sequencing it",
        domain="D3 Claude Code Configuration and Workflows - 3.5",
        question="Which half of iterative refinement is a calculation?",
        expect="The fix graph is. The prose-versus-examples half is asserted.",
        note=("TRANSPORT: none, and no model call. The edge-case verdicts are "
              "SCRIPTED - this repo's judgement about what each spec determines. "
              "The round-trip counts are computed from the dependency graph and "
              "are exact given it."),
    )

    present.rule("the prose specification")
    present.paragraph(PROSE_SPEC, indent="  | ")
    print("\n  Nothing in it is wrong. Every phrase - 'be consistent', 'handle")
    print("  edge cases sensibly', 'use your judgement' - describes the goal and")
    print("  decides nothing, which is the failure mode: it reads like a spec and")
    print("  functions as a hope.")

    present.rule("the same thing as three examples")
    for source, target, why in EXAMPLES:
        print(f"  {source:<22} -> {target}")
        print(f"  {'':<22}    {why}")

    present.rule("what each one determines, on four edge cases")
    present.table(
        ("input", "the ambiguity", "examples settle it?", "which one, or why not"),
        [(i, d, "yes" if ok else "NO", w) for i, d, ok, w in TRICKY])
    settled = sum(1 for *_, ok, _ in TRICKY if ok)
    print(f"\n  {settled} of {len(TRICKY)} settled by three examples; the prose spec")
    print("  settles none of them, because it names no case at all. And read the")
    print("  last row twice - examples generalise from the judgement they show,")
    print("  so they cover cases you did not list AND leave a hole wherever the")
    print("  judgement itself is new. A range is not a fraction, a null or a")
    print("  duplicate unit; nothing above implies an answer for it. The fix is a")
    print("  fourth example, not a longer paragraph.")

    present.rule("batch or sequence: the arithmetic")
    rows: list[tuple[str, ...]] = []
    for name, spec in FIX_SETS.items():
        seq = sequential_round_trips(spec["fixes"], spec["depends"])
        bat = batched_round_trips(spec["fixes"], spec["depends"])
        edges = sum(len(v) for v in spec["depends"].values())
        rows.append((name, str(len(spec["fixes"])), str(edges), str(seq), str(bat),
                     "batch" if edges else "sequence"))
    present.table(
        ("fix set", "fixes", "dependencies", "sequential", "batched", "correct"),
        rows)

    print("\n  The interacting set: four fixes, five dependency edges, so fixing")
    print("  them one at a time costs 9 round trips - each dependent fix has to")
    print("  be revisited once the thing it was written against moved. One")
    print("  message carrying all four costs 2, and it is also the only version")
    print("  that can be reviewed as a coherent change.")
    print("\n  The independent set: three fixes, no edges, so sequencing costs 3")
    print("  and batching costs 2 - and batching is still the wrong choice. The")
    print("  saving is one round trip; the price is a single diff mixing a typo,")
    print("  a database migration and a timeout change, which cannot be reviewed,")
    print("  reverted or bisected separately. Round trips are the cheap resource")
    print("  here and reviewability is not.")
    print("\n  So the rule is not 'batch when there are many'. It is: batch what")
    print("  interacts, because sequencing it causes rework; sequence what does")
    print("  not, because batching it destroys the reviewable unit.")

    present.rule("the two techniques this file does not demonstrate")
    print("  Test-driven iteration and the interview pattern are both in 3.5 and")
    print("  neither is here. They produce a transcript rather than an artifact,")
    print("  and this repo cannot score a transcript. They are written up in")
    print("  docs/d3-claude-code.md instead, which is the honest place for a")
    print("  technique whose evidence is 'it worked for me'.")
    present.rule()
    print("  LEARN  " + LESSON["learn"])


if __name__ == "__main__":
    main()
