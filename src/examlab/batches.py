"""
WHAT      The Message Batches request shape, `custom_id` correlation, a failure
          resubmission that only resends what failed, and the submission-cadence
          arithmetic that decides whether a batch can meet an SLA at all.
WHY       Every fact about batching is easy to recall and the decision is still
          got wrong, because the recalled fact is "50% cheaper" and the deciding
          fact is "no latency guarantee". The arithmetic below is the part that
          settles it: a 24-hour processing window plus your own submission gap is
          the worst case a downstream consumer sees, and if that number exceeds
          the promise you made, the discount is not available to you at any
          price. Computing it takes one line and is almost never done.
DOMAIN    D4 Prompt Engineering and Structured Output (20%),
          task statement 4.5
TRADEOFF  Nothing here calls the batch endpoint, so the response objects are
          shaped by hand from the documentation. That means a field name could be
          stale and this file would not notice. What it cannot get wrong is the
          arithmetic, which is the part the exam asks you to do and the part a
          live call would not teach you anyway.
ALTERNATIVE  Submit a real batch of two trivial requests and poll it. Worth
          doing once for the operational feel - the polling, the `.jsonl`
          results, the ordering - and it needs a credential and a day of
          patience for the interesting case, which is the slow one.

Cost: free, 0 model calls, 0 network calls. Every number below is either
DOCUMENTED or computed here from documented inputs.
"""
from __future__ import annotations

from examlab import present

LESSON = {
    "domain": "D4 Prompt Engineering and Structured Output - 4.5",
    "setup": "None. Read PROPERTIES, then do the arithmetic in your head before "
             "you look at the table.",
    "run": "uv run python -m playground.run examlab.batches",
    "cost": "free - 0 model calls",
    "expect": "The four properties, a request array with custom_ids, a "
              "resubmission that sends 5 requests instead of 100, and a cadence "
              "table where one of four windows misses a 30-hour SLA and one "
              "meets it with exactly zero margin.",
    "learn": "Batch is a latency decision wearing a cost badge. Worst case is "
             "your submission gap PLUS the processing window, so the cadence is "
             "what you design; and no multi-turn tool calling means an agentic "
             "loop cannot be batched at all, only its individual turns.",
}

# DOCUMENTED, Message Batches API. The last row is the one that disqualifies
# batching for agent work outright, and it is the one summaries omit.
PROPERTIES = [
    ("cost", "50% of the synchronous price",
     "A ratio, so it survives a price change. Never quote the absolute figure."),
    ("processing window", "up to 24 hours",
     "An upper bound, not an estimate. Often much faster - which is not a"
     " guarantee you may design against."),
    ("latency SLA", "none",
     "This is the whole decision. 'Usually fast' cannot back a blocking check."),
    ("multi-turn tool calling", "not supported within one request",
     "You cannot execute a tool mid-request and return the result. An agentic"
     " loop is therefore not batchable; individual single-turn calls are."),
]

# WHY custom_id and not array position: results are not guaranteed to come back
# in submission order, so position is not an identifier. It is also the handle
# you resubmit by, which is why it must mean something in YOUR system - a
# document id, not a counter.
BATCH = [
    {"custom_id": "doc-0041", "params": {"model": "claude-haiku-4-5", "max_tokens": 1024,
                                         "messages": [{"role": "user", "content": "extract..."}]}},
    {"custom_id": "doc-0042", "params": {"model": "claude-haiku-4-5", "max_tokens": 1024,
                                         "messages": [{"role": "user", "content": "extract..."}]}},
]

# A fabricated result set for 100 submitted documents, shaped from the docs.
RESULTS = {
    "succeeded": 97,
    "errored": [
        ("doc-0013", "invalid_request", "prompt exceeds the context window",
         "chunk into 2 and resubmit both"),
        ("doc-0058", "invalid_request", "prompt exceeds the context window",
         "chunk into 2 and resubmit both"),
        ("doc-0091", "api_error", "transient upstream failure",
         "resubmit unchanged"),
    ],
}

PROCESSING_HOURS = 24  # DOCUMENTED upper bound
SLA_HOURS = 30         # the promise made to the consumer, in this worked example


def worst_case(window_hours: int) -> int:
    """Hours from a document arriving to its result existing, worst case.

    A document that arrives one minute after a submission waits the full
    `window_hours` for the next one, then up to the processing bound. The two
    add; nothing overlaps. This is the whole model, and forgetting the first
    term is how a 24-hour bound gets compared against a 30-hour SLA and passes.
    """
    return window_hours + PROCESSING_HOURS


def resubmission(errored: list[tuple[str, str, str, str]]) -> int:
    """How many requests the second batch carries. Not the same as failures.

    Chunking an oversized document turns one failed id into two new requests, so
    the resubmission can be larger than the failure count and is still far
    smaller than the original batch. Resending all 100 is the mistake this
    arithmetic exists to prevent.
    """
    return sum(2 if "chunk" in fix else 1 for *_, fix in errored)


def main() -> None:
    present.banner(
        title="Message Batches: the discount, and the arithmetic that revokes it",
        domain="D4 Prompt Engineering and Structured Output - 4.5",
        question="Can this workload tolerate a bound of 24 hours plus your own gap?",
        expect="Two of four cadences miss the SLA. The 50% is never the issue.",
        note=("TRANSPORT: none, and no endpoint was called. The properties are "
              "DOCUMENTED; the result set is fabricated; the arithmetic is "
              "computed here from the documented bound and is the only thing on "
              "this page that cannot be stale."),
    )
    present.rule("four properties, and which one decides")
    present.table(("property", "value", "what it means for the design"),
                  [(p[0], p[1], p[2]) for p in PROPERTIES])

    present.rule("the request array")
    for entry in BATCH:
        print(f"  {entry['custom_id']}  ->  {entry['params']['model']}, "
              f"{len(entry['params']['messages'])} message(s)")
    print("  ...98 more. Results come back keyed by custom_id and NOT")
    print("  necessarily in this order, so array position identifies nothing.")

    present.rule("handling failures: resend what failed, not the batch")
    present.table(("custom_id", "type", "reason", "correct response"),
                  [tuple(row) for row in RESULTS["errored"]])
    count = resubmission(RESULTS["errored"])
    print(f"\n  {RESULTS['succeeded']} succeeded, {len(RESULTS['errored'])} errored,")
    print(f"  and the resubmission carries {count} requests - more than the")
    print(f"  {len(RESULTS['errored'])} failures, because two of them chunk in two,")
    print(f"  and {100 - count} fewer than resending the batch.")

    present.rule(f"cadence against a {SLA_HOURS}-hour SLA")
    rows: list[tuple[str, ...]] = []
    for window in (2, 4, 6, 8):
        total = worst_case(window)
        rows.append((f"every {window}h", f"{window} + {PROCESSING_HOURS}", str(total),
                     "meets" if total <= SLA_HOURS else "MISSES",
                     f"{SLA_HOURS - total:+d}h"))
    present.table(("submission window", "arithmetic", "worst case", "verdict",
                   "margin"), rows)
    print(f"\n  The mathematical bound is a {SLA_HOURS - PROCESSING_HOURS}h window;")
    print("  4h is the answer to pick, because 6h meets the SLA with zero margin")
    print("  and leaves nothing for retrieval, the downstream write, or the")
    print("  resubmission above - which needs a whole second window.")
    print("\n  And the decision that comes before all of it: a blocking pre-merge")
    print("  check cannot use this at any discount, because a developer is")
    print("  waiting. An overnight report can. Same API, same 50%, opposite")
    print("  answers, and latency tolerance is the only input.")
    present.rule()
    print("  LEARN  " + LESSON["learn"])


if __name__ == "__main__":
    main()
