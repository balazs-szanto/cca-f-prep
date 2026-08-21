"""
WHAT      Seed data and mutation functions for the mock ticket tracker. No I/O,
          no clock, no randomness - two runs produce byte-identical output.
WHY       Keeping state separate from transport means the tools in server.py are
          thin wrappers you can read in one pass, and this file can be exercised
          without starting a server or speaking MCP at all.
DOMAIN    D2 Tool Design and MCP Integration
TRADEOFF  Module-level mutable state is the wrong shape for anything real: it is
          per-process, so two clients get two divergent worlds, and it vanishes on
          exit. That is deliberate here - a database would add a dependency and
          teach nothing about MCP.
ALTERNATIVE  A lifespan-scoped context object passed to each tool, which MCPServer
          supports via its `lifespan` parameter. Correct for a real server,
          noise for a demo whose subject is the transport.

Determinism is a feature, not laziness: error_taxonomy.py needs a failure it can
provoke on demand, and permission_gate.py needs a delete that either happened or
did not. Neither works against data that drifts.
"""
from typing import Any, Literal

Status = Literal["open", "in_progress", "closed"]

# WHY: a literal list rather than a loop with an index. Generated seed data grows
# a pattern the model can guess at instead of looking it up, which quietly
# weakens every demo that reads from here.
_SEED: list[dict[str, Any]] = [
    {"id": "TCK-001", "title": "Checkout returns 500 on card decline",
     "status": "open", "priority": 1, "assignee": "rmoore"},
    {"id": "TCK-002", "title": "Footer typo on pricing page",
     "status": "open", "priority": 5, "assignee": "jpatel"},
    {"id": "TCK-003", "title": "Connection pool leak after 6h uptime",
     "status": "in_progress", "priority": 1, "assignee": "rmoore"},
    {"id": "TCK-004", "title": "Add pagination to /v2/orders",
     "status": "open", "priority": 3, "assignee": "lchen"},
    {"id": "TCK-005", "title": "Rotate expired staging certificate",
     "status": "closed", "priority": 2, "assignee": "jpatel"},
    {"id": "TCK-006", "title": "Search returns stale results after reindex",
     "status": "in_progress", "priority": 2, "assignee": "lchen"},
    {"id": "TCK-007", "title": "Onboarding email links to dead docs anchor",
     "status": "open", "priority": 4, "assignee": "rmoore"},
    {"id": "TCK-008", "title": "Audit log missing actor on bulk delete",
     "status": "open", "priority": 2, "assignee": "swilson"},
    {"id": "TCK-009", "title": "Dark mode contrast fails WCAG on badges",
     "status": "closed", "priority": 4, "assignee": "swilson"},
    {"id": "TCK-010", "title": "Retry storm when upstream returns 429",
     "status": "in_progress", "priority": 1, "assignee": "lchen"},
]

TICKETS: dict[str, dict[str, Any]] = {t["id"]: dict(t) for t in _SEED}

# WHY: module-level call counter. flaky_search must fail exactly once per process
# and then succeed, so the failure is reproducible rather than probabilistic -
# a randomly flaky tool cannot be used to teach a taxonomy.
_search_calls = 0


# WHY these prefixes exist: MEASURED 2026-08-20 by driving the server over stdio
# by hand - an exception raised in a tool reaches the client as
# `isError: true` plus a text blob, and the exception CLASS is not transmitted.
# So a distinct Python type buys the caller nothing across the transport, and the
# only discriminator that survives is one you put in the message yourself.
UPSTREAM_CODE = "UPSTREAM_UNAVAILABLE"
ARGUMENT_CODE = "BAD_ARGUMENT"


class UpstreamUnavailable(RuntimeError):
    """Raised by the first flaky_search call of each process.

    Distinct from ValueError on the Python side for readability only. The part
    that actually reaches a client is the UPSTREAM_UNAVAILABLE prefix.
    """


def reset() -> None:
    """Restore seed state. Used by the standalone smoke test, not by tools."""
    global _search_calls
    TICKETS.clear()
    TICKETS.update({t["id"]: dict(t) for t in _SEED})
    _search_calls = 0


def find(status: str | None = None, assignee: str | None = None) -> list[dict[str, Any]]:
    rows = list(TICKETS.values())
    if status:
        rows = [r for r in rows if r["status"] == status]
    if assignee:
        rows = [r for r in rows if r["assignee"] == assignee]
    # WHY: sorted by id, always. Dict order happens to be insertion order here,
    # but relying on that would make output order an accident of the seed literal.
    return sorted(rows, key=lambda r: r["id"])


def get(ticket_id: str) -> dict[str, Any]:
    if ticket_id not in TICKETS:
        raise KeyError(ticket_id)
    return dict(TICKETS[ticket_id])


def set_status(ticket_id: str, status: str) -> dict[str, Any]:
    if ticket_id not in TICKETS:
        raise KeyError(ticket_id)
    if status not in ("open", "in_progress", "closed"):
        raise ValueError(f"unknown status: {status}")
    TICKETS[ticket_id]["status"] = status
    return dict(TICKETS[ticket_id])


def delete(ticket_id: str) -> dict[str, Any]:
    if ticket_id not in TICKETS:
        raise KeyError(ticket_id)
    return TICKETS.pop(ticket_id)


def search(query: str) -> list[dict[str, Any]]:
    """Fail on the first call of the process, succeed on every call after."""
    global _search_calls
    _search_calls += 1
    if _search_calls == 1:
        raise UpstreamUnavailable(
            f"{UPSTREAM_CODE}: search backend unreachable on attempt 1. "
            f"The arguments are fine; retry the identical call."
        )
    needle = query.lower()
    return [r for r in find() if needle in r["title"].lower()]
