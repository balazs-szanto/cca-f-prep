"""
WHAT      The same code review three ways - one big request, a fixed chain of
          small ones, and a dynamic decomposition that decides its own steps -
          with the requests each one actually built, side by side.
WHY       "Prompt chaining" sounds like a variation on the agentic loop and is
          structurally its opposite, which is the confusion this file exists to
          remove. The loop is ONE conversation that grows: every tool result
          stays in the window forever. A chain is N SEPARATE single-turn
          conversations, and what crosses the boundary between them is only what
          your code chose to carry - which is why chaining is a context strategy
          before it is a quality strategy.
DOMAIN    D1 Agentic Architecture and Orchestration (27%), task
          statement 1.6; and D4 Prompt Engineering (20%), task statement 4.6
TRADEOFF  Every request here is built for real and every response is fabricated,
          so the request sizes below are facts about this code and the findings
          are not facts about anything. That makes the structural comparison
          sound and the quality comparison merely illustrative - a real chain
          finding a bug the single pass missed is the claim you would have to
          measure yourself, and this file cannot make it.
ALTERNATIVE  Run it live against three real files and diff the findings. That is
          the honest version of the quality claim and it needs a credential, a
          corpus and a rubric; the structure is what generalises, so the
          structure is what is here.

Cost: free. The character counts are real; the token counts are not computed at
all, because no tokenizer ran - see the note in the comparison table.
"""
from __future__ import annotations

from examlab import present
from examlab.contract import text_of
from examlab.transport import ScriptedTransport, response

LESSON = {
    "domain": "D1 Agentic Architecture - 1.6, and D4 - 4.6",
    "setup": "Read DIFF and the three strategy functions. Predict which one "
             "sends the largest single request before you run it.",
    "run": "uv run python -m playground.run examlab.chaining",
    "cost": "free - scripted transport, 0 model calls",
    "expect": "Three strategies, then a table of request counts and the largest "
              "prompt each one built. The chain's largest link is smaller than "
              "the single pass at three times the total - and the dynamic one's "
              "is LARGER than the single pass, which is the row to read twice.",
    "learn": "A fixed chain trades request count for request size and buys back "
             "attention; dynamic decomposition buys adaptivity and, unless you "
             "scope each subtask's input yourself, buys no context reduction at "
             "all. Choose on predictability, not on cost.",
}

MODEL = "claude-haiku-4-5"

# WHY: three files with one local defect each plus one cross-file defect that is
# invisible in any single file. That last one is the whole reason a chain needs
# an integration pass, and a fixture without it would make the integration step
# look like ceremony.
DIFF = {
    "cart.py": "def total(items):\n    return sum(i.price for i in items)\n"
               "# no rounding; returns a float with 14 decimal places\n",
    "pricing.py": "def apply_discount(total, pct):\n    return total * (1 - pct)\n"
                  "# pct arrives as 15 for 15%, not 0.15, from two of three callers\n",
    "checkout.py": "def charge(cart):\n    cents = int(total(cart) * 100)\n"
                   "    return gateway.charge(cents)\n"
                   "# int() truncates; combined with the pct bug, undercharges\n",
}

PER_FILE_PROMPT = (
    "Review this one file for local defects only. Report bugs and security "
    "issues; skip style. For each finding give location, issue, severity and a "
    "suggested fix. Do not comment on anything you cannot see in this file.\n\n"
    "FILE {name}\n{body}"
)


def ask(transport, prompt: str) -> tuple[str, int]:
    """One single-turn request. Returns (text, prompt characters sent).

    Note what is NOT here: no history, no accumulation, no `tool_result`. Each
    call to this function is a conversation that begins and ends. That is the
    definition of a chain link, and the reason a chain's window cost is flat
    while a loop's is monotonically increasing.
    """
    reply = transport.create(
        model=MODEL, max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return text_of(reply), len(prompt)


def single_pass(transport) -> tuple[list[str], list[int]]:
    """Everything in one request. The default, and the one that dilutes.

    The failure mode is not that it misses everything - it is that depth varies
    across the input. Sample-question territory: detailed feedback on some
    files, superficial on others, and the same pattern flagged in one file and
    approved in another within a single response.
    """
    body = "\n\n".join(f"FILE {n}\n{b}" for n, b in DIFF.items())
    text, size = ask(transport, "Review this pull request for bugs.\n\n" + body)
    return [text], [size]


def fixed_chain(transport) -> tuple[list[str], list[int]]:
    """One request per file, then one integration pass over the summaries.

    Four requests, known before you start, because the shape of the work is
    known before you start: N files, then one join. Nothing about the plan
    depends on what any step returns - which is the test for whether chaining
    is the right pattern at all.

    The integration request carries the *findings*, not the files. That choice is
    the chain's real content: if you forward the whole diff again you have paid
    four times for one big request instead of buying anything.
    """
    findings: list[str] = []
    sizes: list[int] = []
    for name, body in DIFF.items():
        text, size = ask(transport, PER_FILE_PROMPT.format(name=name, body=body))
        findings.append(f"{name}: {text}")
        sizes.append(size)
    joined = "\n".join(findings)
    text, size = ask(transport, (
        "Below are per-file review findings from three separate passes. Look "
        "ONLY for problems that span files: data flowing between them, unit "
        "mismatches, and any two findings that contradict each other.\n\n"
        + joined))
    findings.append(f"integration: {text}")
    sizes.append(size)
    return findings, sizes


def dynamic_decomposition(transport) -> tuple[list[str], list[int]]:
    """Ask for a plan, then follow the plan you got back.

    The request count is not knowable in advance - it is a function of what step
    one returned. That is the distinguishing property, not the prompt wording.
    Use it when you cannot name the subtasks yet: "add comprehensive tests to
    this legacy codebase" has no fixed decomposition until something has mapped
    the structure.

    Note the shape of the plan step: it returns data your code parses, not prose
    your code greps. See structured_output.py for why that has to be a schema.
    """
    plan_text, plan_size = ask(transport, (
        "You will review a pull request. Do not review it yet. First list the "
        "investigation subtasks you would run, one per line, ordered by expected "
        "yield. Name only subtasks justified by what you can see.\n\n"
        + "\n".join(f"FILE {n} ({len(b)} bytes)" for n, b in DIFF.items())))
    subtasks = [line.strip("- ").strip() for line in plan_text.splitlines() if line.strip()]
    findings = [f"plan: {len(subtasks)} subtask(s) - {'; '.join(subtasks)}"]
    sizes = [plan_size]
    for subtask in subtasks:
        text, size = ask(transport, (
            f"Subtask: {subtask}\nInvestigate only this. Report findings with "
            f"location and severity.\n\n"
            + "\n\n".join(f"FILE {n}\n{b}" for n, b in DIFF.items())))
        findings.append(f"{subtask}: {text}")
        sizes.append(size)
    return findings, sizes


def _canned(*texts: str) -> list[dict]:
    """A script of plain end_turn text responses, one per request."""
    return [response(stop_reason="end_turn",
                     content=[{"type": "text", "text": t}]) for t in texts]


SCRIPTS = {
    "single_pass": _canned(
        "cart.py returns an unrounded float. pricing.py looks fine. "
        "checkout.py truncation is acceptable."),
    "fixed_chain": _canned(
        "unrounded float total, medium",
        "pct unit is ambiguous between callers, high",
        "int() truncates instead of rounding, medium",
        "CROSS-FILE: pricing.py expects a fraction, two callers pass a whole "
        "number, and checkout.py then truncates the result - the two defects "
        "compound into a systematic undercharge. Neither file shows this alone."),
    "dynamic_decomposition": _canned(
        "- trace the money path end to end\n- check unit conventions at each boundary",
        "the money path crosses three files with two representation changes",
        "pct is a fraction in one file and a percentage in two callers"),
}

STRATEGIES = [
    (single_pass, "one request, whole diff", "fixed at 1"),
    (fixed_chain, "per-file passes plus an integration pass", "fixed at N+1"),
    (dynamic_decomposition, "plan first, then follow it", "not knowable upfront"),
]


def main() -> None:
    present.banner(
        title="Chaining: one request, a fixed chain, or a plan that decides",
        domain="D1 (1.6) and D4 (4.6)",
        question="What actually differs between these three - and what does not?",
        expect="Request counts and prompt sizes that are real; findings that are not.",
        note=("TRANSPORT: scripted for all three, and the findings are written "
              "by this repo to illustrate the shape. The request COUNTS and "
              "SIZES below are produced by the code and are real; the claim "
              "that a chain finds more is illustrative, not measured."),
    )
    rows: list[tuple[str, ...]] = []
    for function, summary, predictability in STRATEGIES:
        transport = ScriptedTransport(SCRIPTS[function.__name__])
        present.rule(f"{function.__name__} - {summary}")
        findings, sizes = function(transport)
        for finding in findings:
            print(f"    - {finding[:96]}")
        rows.append((function.__name__, str(len(sizes)), str(max(sizes)),
                     str(sum(sizes)), predictability))

    present.rule("what the three actually cost")
    present.table(
        ("strategy", "requests", "largest prompt", "total chars", "request count"),
        rows)
    print("\n  Characters, not tokens - no tokenizer ran, so calling these")
    print("  tokens would be a fabricated number dressed as a measurement.")
    print("\n  READ THE THIRD ROW AGAIN. The prose here originally said the")
    print("  single pass sends the largest prompt; the numbers say it does not.")
    print("  The chain behaves as advertised - its largest link is smaller than")
    print("  the single pass, at three times the total. Dynamic decomposition")
    print("  sends a request LARGER than the single pass, because every subtask")
    print("  re-sends the whole corpus. That is not a bug in the fixture:")
    print("  decomposing a task does nothing for context unless you also scope")
    print("  each subtask's INPUT, and nothing about planning does that for you.")
    print("\n  Adaptivity and context reduction are separate purchases. A chain")
    print("  buys the second by forwarding findings instead of sources; a plan")
    print("  buys the first and, by default, buys the second not at all.")
    print("\n  Caveat on the ratios: three toy files, so per-request instruction")
    print("  boilerplate is comparable to the payload. The ordering above is a")
    print("  property of this fixture. What generalises is the reason for it.")
    print("\n  So the choice is made on predictability, not on cost:")
    print("    predictable, multi-aspect work  -> fixed chain")
    print("    open-ended investigation        -> dynamic decomposition")
    print("    one small well-scoped question  -> single pass, and stop reading")
    present.rule()
    print("  LEARN  " + LESSON["learn"])


if __name__ == "__main__":
    main()
