"""
WHAT      One code review prompted three ways - vague, explicit categorical
          criteria, and criteria plus few-shot examples - scored against a
          fixture that knows which findings are real.
WHY       Task statements 4.1 and 4.2 had no demo in this repo, and the recorded
          reason was that neither produces an objectively checkable outcome. That
          reason was wrong in one specific way: what you cannot check for free is
          the MODEL's response to a prompt, and what you can check exactly is
          precision and recall of a finding set against a labelled fixture. So
          the arithmetic is real and the finding sets are authored. That buys the
          two things the blueprint actually asks for - the difference between
          "be conservative" and a categorical rule, and what few-shot examples
          add on top of criteria that are already explicit.
DOMAIN    D4 Prompt Engineering and Structured Output (20%), task statements
          4.1 and 4.2
TRADEOFF  The finding set attached to each arm is written by this repo, so the
          DIRECTION of the effect is asserted, not measured. Precision, recall
          and every count printed below are computed from the fixture and are
          exact. Read the numbers as arithmetic over an authored premise: if you
          disagree that a vague prompt produces those findings, the numbers do
          not defend the claim, and the prompts themselves are the part that
          transfers regardless.
ALTERNATIVE  Run all three prompts live over a real diff with a hand-labelled
          answer key, three times each for variance. That is the honest version
          and it needs a credential, a corpus and a rubric. The prompt texts
          below are written so they can be lifted straight into it.

Cost: free. The three PROMPTS are the artifact worth stealing; the numbers are
arithmetic over SCRIPTED findings.
"""
from __future__ import annotations

from examlab import present

LESSON = {
    "domain": "D4 Prompt Engineering and Structured Output - 4.1 and 4.2",
    "setup": "Read the three PROMPTS in full before the table. They are the "
             "point; the scores only rank them.",
    "run": "uv run python -m playground.run examlab.review_criteria",
    "cost": "free - 0 model calls, findings are fabricated per arm",
    "expect": "Three arms scored on the same nine-item answer key: 25%, 80% "
              "and 83% precision, 20%, 80% and 100% recall. The vague arm "
              "already contains two confidence hedges and still scores worst. "
              "One false positive survives all three arms.",
    "learn": "Vague instructions and confidence hedges do not move precision, "
             "because they do not tell the model what counts. Categorical "
             "criteria move it. Few-shot examples add generalisation to cases "
             "no criterion named, which is a different purchase from precision.",
}

# WHY the criteria are quoted verbatim rather than summarised: this is the
# deliverable. A reader who takes nothing else from this file should take the
# difference between PROMPTS["vague"] and PROMPTS["explicit"], which is the whole
# of task statement 4.1 in about fifteen lines.
PROMPTS = {
    "vague": (
        "Review this diff and report any problems you find. Check that the "
        "comments are accurate. Be conservative and only report high-confidence "
        "findings. Focus on quality."
    ),
    "explicit": (
        "Review this diff. Report a finding ONLY if it falls in one of these "
        "categories:\n"
        "  - CORRECTNESS: the code produces a wrong result for some input you "
        "can name. State the input.\n"
        "  - SECURITY: untrusted data reaches a sink without validation. Name "
        "the sink.\n"
        "  - COMMENT CONTRADICTION: a comment states behaviour that the code "
        "beside it does not have. Quote both.\n"
        "Do NOT report: formatting, naming, import order, a pattern that is "
        "used consistently elsewhere in this codebase, or a suggestion phrased "
        "as a preference.\n"
        "For each finding give file, line, category, severity and the smallest "
        "change that fixes it."
    ),
    "explicit_plus_fewshot": None,  # built below from EXPLICIT plus EXAMPLES
}

# WHY two examples and not ten: the blueprint says 2-4, and the reason is visible
# here. Each one has to carry the REASONING for choosing one action over a
# plausible alternative, which is what lets the model generalise instead of
# pattern-matching. Ten examples of the same reasoning add tokens and nothing.
EXAMPLES = (
    "Examples of the judgement, including why the alternative was rejected:\n\n"
    "EXAMPLE 1 — reported.\n"
    "  Code:    `# returns cents` above `return total  # float euros`\n"
    "  Finding: COMMENT CONTRADICTION, high. The comment claims cents; the "
    "expression returns euros as a float.\n"
    "  Why not skipped: this is not a stale-comment nitpick. A caller who trusts "
    "the comment is off by a factor of 100, so it is a correctness bug wearing a "
    "comment's clothes.\n\n"
    "EXAMPLE 2 — not reported.\n"
    "  Code:    `except Exception: log.warning(...)` in a retry helper, where "
    "four other helpers in the same module do the same thing.\n"
    "  Finding: none.\n"
    "  Why not reported: a broad except is a real smell AND it is the "
    "established pattern in this file. Flagging it here and not in the four "
    "neighbours is the inconsistency that destroys trust in the review. Raise "
    "the pattern once, outside the review, or not at all.\n"
)
PROMPTS["explicit_plus_fewshot"] = PROMPTS["explicit"] + "\n\n" + EXAMPLES

# The answer key. `real` is ground truth; `novel` marks the one defect no
# category above names explicitly - a comment that is accurate about the code and
# wrong about the units the CALLER uses. It is here to separate "did the criteria
# cover it" from "did the model generalise".
TRUTH = {
    "cart.py:12 float total not rounded": {"real": True, "novel": False},
    "pricing.py:8 pct is a fraction here, a percentage in two callers":
        {"real": True, "novel": False},
    "checkout.py:5 int() truncates instead of rounding": {"real": True, "novel": False},
    "checkout.py:9 order_id from the query string reaches SQL unescaped":
        {"real": True, "novel": False},
    "pricing.py:3 comment says 'ratio', code and callers disagree with each other":
        {"real": True, "novel": True},
    "cart.py:4 `items` could be named `line_items`": {"real": False, "novel": False},
    "checkout.py:1 imports are not alphabetical": {"real": False, "novel": False},
    "pricing.py:11 broad `except Exception`, as in four sibling helpers":
        {"real": False, "novel": False},
    # WHY this row exists: without it every arm below scored 100% precision and
    # 100% recall as soon as the criteria were explicit, and a fixture that
    # produces a flawless monotone improvement is a fixture that was tuned until
    # it told the better story. This is a false positive INSIDE a named category
    # - a misreading of what sum([]) does, reported as CORRECTNESS - so no
    # wording of the criteria removes it. It survives all three arms on purpose.
    "cart.py:12 sum() over an empty cart returns 0 instead of None":
        {"real": False, "novel": False},
}

# SCRIPTED. One finding set per arm, authored to show the shape of each failure:
# the vague arm reports style and misses the injection; the explicit arm gets the
# named categories and skips the novel one; few-shot reaches the novel one.
FINDINGS = {
    "vague": [
        "cart.py:12 float total not rounded",
        "cart.py:4 `items` could be named `line_items`",
        "checkout.py:1 imports are not alphabetical",
        "pricing.py:11 broad `except Exception`, as in four sibling helpers",
    ],
    "explicit": [
        "cart.py:12 float total not rounded",
        "pricing.py:8 pct is a fraction here, a percentage in two callers",
        "checkout.py:5 int() truncates instead of rounding",
        "checkout.py:9 order_id from the query string reaches SQL unescaped",
        "cart.py:12 sum() over an empty cart returns 0 instead of None",
    ],
    "explicit_plus_fewshot": [
        "cart.py:12 float total not rounded",
        "pricing.py:8 pct is a fraction here, a percentage in two callers",
        "checkout.py:5 int() truncates instead of rounding",
        "checkout.py:9 order_id from the query string reaches SQL unescaped",
        "pricing.py:3 comment says 'ratio', code and callers disagree with each other",
        "cart.py:12 sum() over an empty cart returns 0 instead of None",
    ],
}


def score(reported: list[str]) -> dict[str, float | int]:
    """Precision, recall and the novel-case flag. Exact, given the fixture."""
    real = {k for k, v in TRUTH.items() if v["real"]}
    novel = {k for k, v in TRUTH.items() if v["novel"]}
    hits = [r for r in reported if r in real]
    false_positives = [r for r in reported if r not in real]
    return {
        "reported": len(reported),
        "true": len(hits),
        "false": len(false_positives),
        "precision": len(hits) / len(reported) if reported else 0.0,
        "recall": len(hits) / len(real),
        "novel": len(novel & set(reported)),
    }


def main() -> None:
    present.banner(
        title="Explicit criteria, then few-shot: what each one actually buys",
        domain="D4 Prompt Engineering and Structured Output - 4.1 and 4.2",
        question="Does telling a reviewer to 'be conservative' improve precision?",
        expect="Three arms, one answer key, and one row that only the third arm reaches.",
        note=("TRANSPORT: none. The finding set for each arm is SCRIPTED - "
              "written by this repo to show the shape of each failure. Every "
              "score below is exact arithmetic over the answer key, and no "
              "score here is evidence about a model."),
    )
    for name, prompt in PROMPTS.items():
        present.rule(f"PROMPTS['{name}'] - {len(prompt)} characters")
        for line in prompt.split("\n"):
            print(f"  | {line}")

    present.rule("scored against the same nine-item answer key")
    rows: list[tuple[str, ...]] = []
    for name in PROMPTS:
        s = score(FINDINGS[name])
        rows.append((name, str(s["reported"]), str(s["true"]), str(s["false"]),
                     f"{s['precision']:.0%}", f"{s['recall']:.0%}",
                     "yes" if s["novel"] else "no"))
    present.table(("arm", "reported", "real", "false", "precision", "recall",
                   "novel case"), rows)

    print("\n  Nine items on the key: five real defects, three that the explicit")
    print("  prompt names as not-reportable, and one that is none of those - see")
    print("  the last block. Read the columns in this order:")
    print("\n  1. PRECISION, 25% to 80%. The vague prompt already said 'be")
    print("     conservative' and 'only report high-confidence findings', and it")
    print("     still reported three non-defects - because a hedge tells the")
    print("     reviewer how sure to be, not what counts as a finding. The")
    print("     categorical list is what moved it, and note that the list gets")
    print("     its power from the SKIP half as much as the report half.")
    print("\n  2. RECALL. The vague arm missed the SQL injection entirely while")
    print("     reporting import order. That is the failure that costs trust:")
    print("     not noise on its own, but noise crowding out the real finding.")
    print("\n  3. THE NOVEL CASE, which is 4.2's whole content. No category in")
    print("     the explicit prompt names 'a comment that is accurate about its")
    print("     own line and wrong about how callers use it'. The explicit arm")
    print("     therefore skips it, correctly by its own rules. The few-shot arm")
    print("     reports it - because EXAMPLE 1 demonstrated the JUDGEMENT that a")
    print("     units mismatch hiding behind a comment is a correctness bug,")
    print("     and that judgement generalises to a case nobody enumerated.")
    print("\n  So the two techniques buy different things and the order matters:")
    print("  criteria raise precision by defining the boundary, examples raise")
    print("  recall on cases outside every boundary you thought to draw. Adding")
    print("  examples to a vague prompt gets you neither, because there is no")
    print("  boundary for them to generalise from.")

    present.rule("the false positive that survives all three prompts")
    survivor = "cart.py:12 sum() over an empty cart returns 0 instead of None"
    print(f"  {survivor}")
    print("\n  Reported by both explicit arms, and wrong: sum([]) is 0 and that")
    print("  is the behaviour the caller wants. It sits squarely inside the")
    print("  CORRECTNESS category, phrased exactly as the prompt asks, with an")
    print("  input named. No wording of the criteria excludes it, because the")
    print("  defect is not a category error - it is a misreading of the code.")
    print("\n  This row is in the fixture on purpose. Without it every arm after")
    print("  the vague one scored 100% precision and 100% recall, and a fixture")
    print("  that produces a flawless monotone improvement is one that was tuned")
    print("  until it told the better story. Criteria and examples move the")
    print("  boundary of what gets reported. Neither makes the reviewer read")
    print("  more carefully, and that residue is what human review is for.")

    present.rule("the one thing to do when precision is the emergency")
    print("  If a category is producing false positives faster than you can fix")
    print("  the prompt, turn that category OFF and keep the rest. A reviewer")
    print("  trusted on four categories beats one distrusted on five: the")
    print("  dismissals do not stay contained to the bad category, they teach")
    print("  people to skim past all of them.")
    present.rule()
    print("  LEARN  " + LESSON["learn"])


if __name__ == "__main__":
    main()
