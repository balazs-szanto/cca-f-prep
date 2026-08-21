"""
WHAT      Twenty labelled extractions, an aggregate that looks tolerable, the
          per-segment breakdown that shows it is not, a threshold sweep over
          self-reported confidence, and the sampling plan that keeps measuring
          after you automate.
WHY       "97% accurate, let us drop the human review" is the decision this task
          statement exists to stop, and the reason it is wrong is arithmetic
          rather than judgement: an aggregate is a weighted mean, so a quarter of
          the volume can sit at 60% while the mean still reads well above it.
          That is checkable exactly, here, for nothing. The second half is the harder
          idea - a model's own confidence is a number with no units until you
          calibrate it against labels, and the sweep below is what calibration
          actually looks like.
DOMAIN    D5 Context Management and Reliability (15%), task statement 5.5
TRADEOFF  Twenty rows is too few to calibrate anything in reality; a real sweep
          wants hundreds per segment, and the confidence intervals at n=20 are
          wide enough to swallow the effect. It is twenty so that a reader can
          check every number by hand, which is the property that matters in a
          study repo and would be the wrong trade in production.
ALTERNATIVE  Compute the same sweep over a real labelled validation set and plot
          it. Same arithmetic, better evidence, and it needs a corpus and a human
          who labelled it. The functions below take any list of the same shape.

Cost: free. Every extraction is fabricated; every statistic is computed from it.
"""
from __future__ import annotations

from examlab import present

LESSON = {
    "domain": "D5 Context Management and Reliability - 5.5",
    "setup": "None. Before the table, guess what fraction of the errors the "
             "model marked high-confidence.",
    "run": "uv run python -m playground.run examlab.confidence_routing",
    "cost": "free - 0 model calls",
    "expect": "85% aggregate accuracy, then one document type at 60% and one "
              "field at 60%. Then a sweep where routing everything below 0.90 to "
              "a human reviews 30% of the volume and catches NONE of the three "
              "errors, because two of them are above 0.95.",
    "learn": "An aggregate accuracy is a weighted mean and hides its worst "
             "segment by construction. Confidence is a number with no units "
             "until a labelled set gives it one - and the threshold you pick "
             "buys review volume, not correctness.",
}

# WHY doc_type and field are separate columns: the blueprint asks for accuracy
# "by document type AND field", and they fail independently. Here `scan` is the
# bad type and `vat_rate` is the bad field, and neither is visible in the other's
# breakdown - a repo that only segmented one way would find one of them.
#
# `confidence` is the model's own self-report. `correct` is ground truth. The
# whole subject of this file is the relationship between those two columns.
EXTRACTIONS = [
    # (id, doc_type, field, confidence, correct)
    ("e01", "invoice_pdf", "total", 0.98, True),
    ("e02", "invoice_pdf", "total", 0.97, True),
    ("e03", "invoice_pdf", "vat_rate", 0.95, True),
    ("e04", "invoice_pdf", "vat_rate", 0.93, False),
    ("e05", "invoice_pdf", "issued", 0.99, True),
    ("e06", "invoice_pdf", "issued", 0.96, True),
    ("e07", "invoice_pdf", "total", 0.94, True),
    ("e08", "invoice_pdf", "issued", 0.92, True),
    ("e09", "receipt_photo", "total", 0.91, True),
    ("e10", "receipt_photo", "total", 0.88, True),
    ("e11", "receipt_photo", "vat_rate", 0.86, True),
    ("e12", "receipt_photo", "issued", 0.90, True),
    ("e13", "receipt_photo", "issued", 0.84, True),
    ("e14", "scan", "total", 0.97, False),
    ("e15", "scan", "total", 0.89, True),
    ("e16", "scan", "vat_rate", 0.96, False),
    ("e17", "scan", "issued", 0.87, True),
    ("e18", "scan", "issued", 0.72, True),
    ("e19", "invoice_pdf", "total", 0.99, True),
    ("e20", "invoice_pdf", "vat_rate", 0.98, True),
]


def accuracy(rows: list[tuple]) -> float:
    return sum(1 for r in rows if r[4]) / len(rows) if rows else 0.0


def by(index: int) -> dict[str, list[tuple]]:
    """Group the extractions by one column, preserving first-seen order."""
    groups: dict[str, list[tuple]] = {}
    for row in EXTRACTIONS:
        groups.setdefault(row[index], []).append(row)
    return groups


def sweep(threshold: float) -> dict[str, int | float]:
    """Route everything below `threshold` to a human. What does that buy?

    Two numbers matter and they trade against each other: how many items a
    person has to look at, and how many wrong answers ship anyway. A threshold
    is a choice between those, and nothing about it makes the model better.
    """
    reviewed = [r for r in EXTRACTIONS if r[3] < threshold]
    automated = [r for r in EXTRACTIONS if r[3] >= threshold]
    caught = [r for r in reviewed if not r[4]]
    escaped = [r for r in automated if not r[4]]
    return {
        "threshold": threshold,
        "reviewed": len(reviewed),
        "caught": len(caught),
        "escaped": len(escaped),
        "review_load": len(reviewed) / len(EXTRACTIONS),
    }


def main() -> None:
    total_errors = [r for r in EXTRACTIONS if not r[4]]
    present.banner(
        title="Confidence calibration, and the aggregate that hides the problem",
        domain="D5 Context Management and Reliability - 5.5",
        question="What does 85% accuracy tell you about the next document?",
        expect="Almost nothing, until it is split by type and by field.",
        note=("TRANSPORT: none. All twenty extractions and their confidences are "
              "fabricated; every statistic below is computed from them and is "
              "exact. Nothing here measures how well a real model calibrates - "
              "that is the thing a labelled set of your own has to tell you."),
    )
    print(f"\n  Aggregate accuracy: {accuracy(EXTRACTIONS):.0%} over "
          f"{len(EXTRACTIONS)} extractions, {len(total_errors)} wrong.")
    print("  That is the number that gets taken to a meeting. Now split it.")
    print("")
    print("  A note on the level rather than the gap: 85% is not a figure")
    print("  anyone would automate on, and a realistic 97% cannot be built from")
    print("  twenty rows a reader can still check by hand. So read the DISTANCE")
    print("  between the aggregate and the worst segment below, not the absolute")
    print("  number. At production volumes the distance is what survives; the")
    print("  aggregate just looks more reassuring while it does.")

    present.rule("by document type")
    present.table(
        ("doc_type", "n", "accuracy", "errors"),
        [(k, str(len(v)), f"{accuracy(v):.0%}", str(sum(1 for r in v if not r[4])))
         for k, v in by(1).items()])

    present.rule("by field")
    present.table(
        ("field", "n", "accuracy", "errors"),
        [(k, str(len(v)), f"{accuracy(v):.0%}", str(sum(1 for r in v if not r[4])))
         for k, v in by(2).items()])

    print("\n  Two independent failures, and each is invisible in the other's")
    print("  table. `scan` is the worst type; `vat_rate` is the worst field; the")
    print("  bad segments hold two of the three errors each, and overlap in")
    print("  exactly one - so a pipeline segmented only by type would have")
    print("  shipped the vat_rate problem, and the other way round. The")
    print("  aggregate hid both by construction: it is a weighted mean, and")
    print("  the bad segments are a quarter of the volume each.")

    present.rule("what the model's own confidence was worth")
    high = [r for r in EXTRACTIONS if r[3] >= 0.95]
    high_errors = [r for r in high if not r[4]]
    print(f"  {len(high)} extractions came back at 0.95 or above, and "
          f"{len(high_errors)} of them are wrong:")
    for row in high_errors:
        print(f"    {row[0]}  {row[1]:<14} {row[2]:<9} confidence {row[3]}  WRONG")
    print(f"\n  So {len(high_errors)} of the {len(total_errors)} errors in the whole")
    print("  set are inside the band you were about to stop reviewing. Note e14")
    print("  and e16: both `scan`, both at 0.96 or better, both wrong. Confidence")
    print("  is not a probability until something calibrates it, and an")
    print("  uncalibrated one is most confident exactly where the input is worst.")

    present.rule("the threshold sweep, which is what calibration produces")
    present.table(
        ("route below", "reviewed", "caught", "escaped", "review load"),
        [(f"{s['threshold']:.2f}", str(s["reviewed"]), str(s["caught"]),
          str(s["escaped"]), f"{s['review_load']:.0%}")
         for s in (sweep(t) for t in (0.80, 0.90, 0.95, 0.98))])
    print("\n  Read the `escaped` column against `reviewed`. The 0.90 row is the one")
    print("  to sit with: it sends 30% of the volume to a human and catches ZERO")
    print("  of the three errors - the full cost of review with none of its")
    print("  benefit, which is what a plausible-sounding threshold picked")
    print("  without a labelled set buys. And no threshold here catches every")
    print("  error, because two of the three sit above 0.95.")
    print("  Reviewing 80% of the volume to catch all three is not calibration,")
    print("  it is giving up on automation - which is the honest reading when")
    print("  confidence and correctness are this weakly related.")
    print("\n  The fix is not a better threshold. It is to route on the SEGMENT")
    print("  as well: send every `scan` and every `vat_rate` to a human")
    print("  regardless of confidence, automate `invoice_pdf` totals and dates,")
    print("  and re-measure. Segment membership is known before the extraction;")
    print("  confidence is only known after, and is worth less.")

    present.rule("and after you automate, keep measuring")
    print("  Stratified random sampling, not a spot check: draw a fixed fraction")
    print("  from EACH segment of the automated stream, including the segments")
    print("  that look fine. Two reasons, and the second is the one people miss:")
    print("   - an unstratified sample is dominated by your commonest document")
    print("     type, so a rare segment can degrade for months unseen;")
    print("   - novel error patterns arrive in the high-confidence band by")
    print("     definition. If they were low-confidence, routing already caught")
    print("     them. Sampling the band you trust is the only way to find out")
    print("     that it stopped deserving it.")
    present.rule()
    print("  LEARN  " + LESSON["learn"])


if __name__ == "__main__":
    main()
