"""
WHAT      Proves that each of the four `messages`-array rules in
          `examlab/contract.py` actually fires, on a fixture built to break that
          rule and no other, and that a well-formed conversation passes.
WHY       `contract.py` is the part of `examlab/` that claims the most: the
          scripted transport is said to *grade* your loop rather than replay
          responses at it, and that claim rests entirely on the validator
          rejecting what the real API would reject. When this was written, only
          rule 4 had ever fired in any run - `loop_antipatterns` trips it - and
          rules 1, 2 and 3 had never executed at all. This repo's own standard is
          that a check which has only been seen passing has not been tested;
          three rules that had not even been seen passing is worse, and it is the
          exact shape of defect the other five scripts here exist to catch.
DOMAIN    D1 Agentic Architecture and Orchestration
TRADEOFF  Each fixture asserts on the rule NUMBER quoted in the message, not on
          the message text, so rewording an error is free and renumbering a rule
          breaks this check. That is the right way round - the numbers are
          referenced from `loop_antipatterns.py` and from the validator's own
          docstring, so they are the part that must not drift silently. The cost
          is that a rule could be reworded into meaning something else while
          still quoting its old number, and this would pass.
ALTERNATIVE  `unittest` or `pytest`, which is what this is. Rejected for
          consistency: every other verification in this repo is a `scripts/`
          entry point that exits 0 or 1 and explains itself in prose, and adding
          a test framework for one file would leave two conventions where the
          repo currently has one. If a second file ever needs this, that trade
          flips.

No model call, no network call, no `anthropic` import. Pure fixtures.

    uv run python scripts/check_contract_rules.py

Exit 0 when every rule fires on its own fixture and the clean case passes, 1
otherwise.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from examlab.contract import TransportError, tool_result, validate_conversation  # noqa: E402

USER = {"role": "user", "content": "Can I still refund order 4471?"}


def assistant(*ids: str) -> dict:
    """An assistant turn requesting one tool_use block per id given.

    Text-only when called with no ids, which is what a terminal turn looks like.
    """
    if not ids:
        return {"role": "assistant", "content": [{"type": "text", "text": "Done."}]}
    return {"role": "assistant", "content": [
        {"type": "tool_use", "id": i, "name": "get_order", "input": {"order_id": 4471}}
        for i in ids]}


def results(*ids: str) -> dict:
    """A user turn carrying one tool_result per id given."""
    return {"role": "user", "content": [tool_result(i, "{}") for i in ids]}


# WHY one fixture per rule, each breaking exactly one thing: a fixture that
# violates two rules proves only that the earlier check runs, and the earlier
# check is the one that was already covered. Rule 4 fires first in the loop, so
# every other fixture has to keep its roles alternating to reach its own rule.
CLEAN = [USER, assistant("toolu_01"), results("toolu_01"), assistant()]

FIXTURES: list[tuple[str, int, list[dict]]] = [
    (
        "a tool_use turn treated as final, then the conversation continues",
        1,
        # WHY the roles still alternate: user, assistant(asks), user(says nothing
        # about it). Rule 4 is satisfied, so rule 1 is what must catch this.
        [USER, assistant("toolu_01"), USER],
    ),
    (
        "the conversation ends with an unanswered tool_use",
        1,
        [USER, assistant("toolu_01")],
    ),
    (
        "a tool_result naming an id nobody requested",
        2,
        [USER, assistant("toolu_01"), results("toolu_99")],
    ),
    (
        "two tools requested, one answered",
        3,
        [USER, assistant("toolu_01", "toolu_02"), results("toolu_01")],
    ),
    (
        "the model's own turn was never appended, so two user turns adjoin",
        4,
        [USER, results("toolu_01")],
    ),
    (
        "tool_result blocks carried by the assistant role",
        4,
        [USER, {"role": "assistant", "content": [tool_result("toolu_01", "{}")]}],
    ),
]


def main() -> int:
    problems: list[str] = []

    try:
        validate_conversation(CLEAN)
    except TransportError as exc:
        problems.append(f"the well-formed conversation was REJECTED: {exc}")

    try:
        validate_conversation([])
        problems.append("an empty messages array was accepted")
    except TransportError:
        pass

    fired: set[int] = set()
    for description, rule, messages in FIXTURES:
        try:
            validate_conversation(messages)
        except TransportError as exc:
            if f"rule {rule}" in str(exc):
                fired.add(rule)
                print(f"  rule {rule}  fired on: {description}")
            else:
                problems.append(
                    f"'{description}' raised, but not as rule {rule}: {exc}")
        else:
            problems.append(f"'{description}' was ACCEPTED; rule {rule} did not fire")

    missing = sorted({1, 2, 3, 4} - fired)
    if missing:
        problems.append(f"rule(s) {missing} never fired on any fixture - either "
                        f"the fixture is wrong or the rule is unreachable")

    if problems:
        print(f"\n{len(problems)} problem(s):\n")
        for line in problems:
            print(f"  {line}")
        print("\n  contract.py is what lets examlab's scripted transport claim it")
        print("  grades a loop rather than replaying at it. A rule that does not")
        print("  fire removes that claim for every demo that depends on it.")
        return 1

    print(f"\nclean: all 4 rules fired, {len(FIXTURES)} fixture(s), the "
          f"well-formed conversation passed and the empty one was refused.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
