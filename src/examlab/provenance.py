"""
WHAT      Findings from two subagents carried through synthesis twice - once
          compressed into prose, once with claim-source mappings preserved - plus
          a real conflict and a fake one, and the report shape that tells them
          apart.
WHY       Attribution is lost at exactly one place: the step that summarises. Not
          in retrieval, not in the final render - in the compression between
          them, because a summariser optimising for brevity drops the fields that
          are pure overhead to it and are the entire value downstream. The second
          half is the harder case: two figures that disagree can be a genuine
          dispute or two different years, and without a date field they are
          indistinguishable, so the pipeline picks one and is confidently wrong
          half the time.
DOMAIN    D5 Context Management and Reliability (15%), task statement 5.6
TRADEOFF  Both synthesis arms are functions in this file, so what they lose or
          keep is decided by this repo rather than by a model asked to be brief.
          The arithmetic of what survives is exact and the tendency it stands in
          for is asserted. What transfers regardless is the output SHAPE - the
          field list a subagent must return, and the two report sections - and
          neither of those depends on the demonstration.
ALTERNATIVE  Give a real synthesis agent the structured findings and diff its
          output against the mappings it was handed. That measures the tendency
          properly, needs a credential, and does not change the field list.

Cost: free. Findings, sources and dates are all fabricated; the coverage and
attribution counts are computed.
"""
from __future__ import annotations

from examlab import present

LESSON = {
    "domain": "D5 Context Management and Reliability - 5.6",
    "setup": "Read FINDINGS and note which fields are not the claim itself. "
             "Those are the ones a summariser drops.",
    "run": "uv run python -m playground.run examlab.provenance",
    "cost": "free - 0 model calls",
    "expect": "Two synthesis arms over the same six findings: one keeps 0 of "
              "6 attributions, the other keeps 5 - the sixth has no source by "
              "design. Then two disagreements that look identical in prose and "
              "are not: one is a dispute, one is five years apart.",
    "learn": "Attribution dies in the summarising step, so require the mapping "
             "as a field rather than asking for it in prose. And a date field is "
             "what separates a contested finding from a stale one; without it "
             "every temporal difference reads as a contradiction.",
}

# WHY every finding carries five fields and only one of them is the claim: the
# other four are what makes the claim checkable later. `collected` is the one
# most often omitted and the one that resolves the second conflict below.
FINDINGS = [
    {
        "claim": "Streaming now accounts for 84% of recorded-music revenue",
        "excerpt": "...streaming reached 84.0% of total recorded-music revenue...",
        "source": "https://example.org/ifpi-style-report-2026",
        "publisher": "industry association annual report",
        "collected": "2026-01",
        "agent": "web_search",
    },
    {
        "claim": "Streaming accounts for 67% of recorded-music revenue",
        "excerpt": "...streaming share stood at 67% of the recorded-music market...",
        "source": "https://example.org/national-statistics-office",
        "publisher": "national statistics office",
        "collected": "2021-06",
        "agent": "web_search",
    },
    {
        "claim": "Session musician bookings fell 31% over five years",
        "excerpt": "...bookings declined 31% between 2021 and 2026...",
        "source": "musicians-union-survey-2026.pdf, p.14",
        "publisher": "trade union survey, n=1,240 self-selected",
        "collected": "2026-03",
        "agent": "document_analysis",
    },
    {
        "claim": "Session musician bookings fell 9% over five years",
        "excerpt": "...a 9% decline in contracted session work 2021-2026...",
        "source": "payroll-aggregator-study-2026.pdf, p.3",
        "publisher": "payroll processor, administrative data, full population",
        "collected": "2026-02",
        "agent": "document_analysis",
    },
    {
        "claim": "Two thirds of composers report using an AI tool weekly",
        "excerpt": "...66% reported at least weekly use of a generative tool...",
        "source": "https://example.org/composers-guild-poll",
        "publisher": "guild membership poll",
        "collected": "2026-05",
        "agent": "web_search",
    },
    {
        "claim": "No data was found on live-performance employment",
        "excerpt": "",
        "source": "",
        "publisher": "",
        "collected": "2026-05",
        "agent": "web_search",
    },
]

# WHY declared rather than inferred: whether two numbers are a dispute or a time
# series is a fact about the world, not something a pipeline can derive from the
# numbers. It CAN derive that the dates differ and refuse to merge them, which is
# the whole recommendation, and that is what `same_period` below models.
CONFLICTS = [
    {
        "topic": "streaming share of revenue",
        "values": ("84%", "67%"),
        "same_period": False,
        "verdict": "not a conflict - five years apart. Merging them as a "
                   "disagreement would invent a dispute; averaging them would "
                   "invent a number that was never true.",
    },
    {
        "topic": "decline in session-musician work",
        "values": ("31%", "9%"),
        "same_period": True,
        "verdict": "a real conflict - same window, both credible, different "
                   "methodologies. A self-selected survey and a full-population "
                   "payroll extract measure different things; report both with "
                   "their methods attached.",
    },
]


def synthesis_lossy(findings: list[dict]) -> list[str]:
    """Summarise for brevity. This is the default and it is where attribution dies.

    Nothing here is careless - it keeps the claim, which is what a reader asked
    for. It drops source, publisher and date because those are overhead from
    inside this step, and are the entire value from outside it.
    """
    return [f["claim"] for f in findings if f["claim"]]


def synthesis_preserving(findings: list[dict]) -> list[dict]:
    """Carry the mapping through instead of the sentence.

    The only difference from above is that the unit of work is a record rather
    than a string. That is the whole intervention, and it is a schema decision
    made upstream, not an instruction added downstream.
    """
    return [
        {"claim": f["claim"], "source": f["source"] or "(none found)",
         "publisher": f["publisher"] or "-", "collected": f["collected"]}
        for f in findings if f["claim"]
    ]


def attributable(rows: list) -> int:
    """How many synthesised items can still be traced to a source."""
    return sum(1 for r in rows if isinstance(r, dict) and r.get("source")
               and r["source"] != "(none found)")


def main() -> None:
    present.banner(
        title="Provenance through synthesis, and telling a conflict from a date",
        domain="D5 Context Management and Reliability - 5.6",
        question="After the summarising step, can you still say who said it?",
        expect="Two arms over the same six findings. One keeps nothing.",
        note=("TRANSPORT: none. Every finding, source and date below is "
              "fabricated, and both synthesis arms are functions in this file "
              "rather than a model asked to be brief. The counts are exact; the "
              "tendency they stand in for is asserted, not measured."),
    )
    lossy = synthesis_lossy(FINDINGS)
    kept = synthesis_preserving(FINDINGS)

    present.rule("arm 1: summarise for brevity")
    for line in lossy:
        print(f"    - {line}")
    print(f"\n  {attributable(lossy)} of {len(lossy)} items are attributable.")
    print("  Every source, publisher and date is gone, and the output reads")
    print("  perfectly well - which is why this survives review. The loss is")
    print("  invisible in the artifact and only shows up when someone asks")
    print("  'according to whom', which is usually after publication.")

    present.rule("arm 2: carry the mapping, not the sentence")
    for row in kept:
        print(f"    - {row['claim']}")
        print(f"      {row['source']}  |  {row['publisher']}  |  {row['collected']}")
    print(f"\n  {attributable(kept)} of {len(kept)} items are attributable.")
    print("  Note the last row: a finding with no source is not dropped, it is")
    print("  carried with '(none found)'. An absent source and an unrecorded one")
    print("  must not look the same downstream - the first is a coverage gap to")
    print("  report, the second is a bug.")

    present.rule("two disagreements that look identical in prose")
    for c in CONFLICTS:
        dates = [f["collected"] for f in FINDINGS
                 if any(v.rstrip("%") in f["claim"] for v in c["values"])]
        print(f"\n  {c['topic']}: {c['values'][0]} vs {c['values'][1]}")
        print(f"    dates on the two findings : {', '.join(sorted(dates))}")
        print(f"    same period              : {c['same_period']}")
        print("    verdict                  :")
        present.paragraph(c["verdict"], indent="      ")
    print("\n  Both pairs are 'two credible sources with different numbers' in")
    print("  prose. Only the date field separates them, and it is the field a")
    print("  summariser drops first. Without it the pipeline either invents a")
    print("  dispute or averages two figures into one that was never true.")

    present.rule("the report shape that follows")
    print("  WELL-ESTABLISHED   claims with agreeing sources, each cited")
    print("  CONTESTED          same period, credible disagreement - BOTH values,")
    print("                     both methods, no averaging and no picking")
    print("  TEMPORAL           different periods - present as a series, not a")
    print("                     contradiction, and label the years")
    print("  COVERAGE GAPS      what was looked for and not found, named")
    print("\n  And render by content type rather than uniformly: the revenue")
    print("  figures as a table with years as columns, the methodology dispute")
    print("  as prose because the disagreement is about method and a table would")
    print("  strip exactly that, and the coverage gap as a plain list.")
    present.rule()
    print("  LEARN  " + LESSON["learn"])


if __name__ == "__main__":
    main()
