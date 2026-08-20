"""
WHAT      A mock ticket tracker exposed as a real MCP server over stdio. Five
          tools, in-memory state, no I/O of any kind.
WHY       external_mcp.py used to reach for @modelcontextprotocol/server-filesystem
          over npx, which makes the demo depend on a package registry, a network
          and whatever governs external servers where it runs - so it was not
          reproducible. A local mock removes every one of those dependencies.
          The protocol, the handshake and the failure modes are real; only the
          backing data is invented.
DOMAIN    D4 Tool Design and MCP Integration
TRADEOFF  A separate process buys a genuine transport - real stdio framing, real
          JSON-RPC, a real crash surface - and costs process startup on every
          run plus a second place for a bug to hide. Nothing here needs its own
          process except the lesson.
ALTERNATIVE  create_sdk_mcp_server, as in basics/tools.py. Same tools, no
          subprocess, no handshake, and no way to see what a transport failure
          looks like.

Run standalone:  uv run python -m mockserver
See README.md in this directory for a hand-written initialize request.
"""
from typing import Any, Literal

from mcp.server import MCPServer

from . import state

server = MCPServer(name="tickets", version="1.0.0")

# Schema strength, stated plainly because this repo has already established that
# unsupported keywords are accepted and silently ignored:
#
#   ENFORCED here   the declared types, and `enum` (which Literal produces), and
#                   which parameters are required (those without a default).
#   NOT ENFORCED    anything expressible only in prose - ranges, formats, id
#                   shapes. Those live in descriptions and bind nothing.
#
# Two tools below are deliberately weak and three deliberately strong. The weak
# ones are marked WEAK SCHEMA and are wrong on purpose.


# WEAK SCHEMA. `status` has exactly three valid values and is typed as a bare
# string, so the model can send "Open", "pending" or "" and nothing stops it -
# the filter then silently matches zero rows. Compare update_status below, which
# expresses the same field correctly.
@server.tool()
def list_tickets(status: str = "", assignee: str = "") -> dict[str, Any]:
    """List tickets, optionally filtered.

    Args:
        status: one of open, in_progress, closed. Empty means any.
        assignee: username. Empty means any.
    """
    rows = state.find(status or None, assignee or None)
    return {"count": len(rows), "tickets": rows}


# STRONG for what a schema can express: one required parameter, correctly typed.
# The id format lives in the description and is therefore advisory.
@server.tool()
def get_ticket(ticket_id: str) -> dict[str, Any]:
    """Fetch one ticket by id.

    Args:
        ticket_id: identifier in the form TCK-001.
    """
    try:
        return {"found": True, "ticket": state.get(ticket_id)}
    except KeyError:
        # WHY: a missing ticket is a normal outcome, not a failure. Returning
        # found=False lets the model correct itself; raising would end the turn
        # over a question that has a perfectly good negative answer.
        return {"found": False, "ticket": None, "reason": f"no ticket {ticket_id}"}


# STRONG. Literal produces a real enum in the input schema - measured, not
# assumed - so this is the one constraint on this server that actually binds.
@server.tool()
def update_status(
    ticket_id: str, status: Literal["open", "in_progress", "closed"]
) -> dict[str, Any]:
    """Set a ticket's status. Reversible.

    Args:
        ticket_id: identifier in the form TCK-001.
        status: the new status.
    """
    try:
        return {"updated": True, "ticket": state.set_status(ticket_id, status)}
    except KeyError:
        return {"updated": False, "ticket": None, "reason": f"no ticket {ticket_id}"}


# STRONG, and the destructive one. `confirm` is required and has no default, so
# the model has to state its intent rather than inherit it. This is the tool
# permission_gate.py refuses for protected ids.
@server.tool()
def delete_ticket(ticket_id: str, confirm: bool) -> dict[str, Any]:
    """Permanently delete one ticket. Cannot be undone.

    Args:
        ticket_id: identifier in the form TCK-001.
        confirm: must be true; the call is refused otherwise.
    """
    if not confirm:
        return {"deleted": False, "reason": "confirm was not true"}
    try:
        removed = state.delete(ticket_id)
        return {"deleted": True, "ticket": removed, "remaining": len(state.TICKETS)}
    except KeyError:
        return {"deleted": False, "reason": f"no ticket {ticket_id}"}


# WEAK SCHEMA, and on the tool most likely to be abused. `limit` is a count typed
# as a string, so the model may send "ten" or "a few" and the int() below decides
# how badly that goes. A free-text `query` is genuinely correct - the input space
# really is open - which is what makes the `limit` mistake next to it easy to miss.
@server.tool()
def flaky_search(query: str, limit: str = "10") -> dict[str, Any]:
    """Search ticket titles. The backend is unreliable on first contact.

    Args:
        query: free text matched against titles.
        limit: maximum rows to return.
    """
    # WHY raised rather than returned: raising is what sets isError on the tool
    # result, which is the signal a client can branch on. Returning a dict with
    # an "error" key would look successful at the protocol level.
    #
    # WHY the message carries a code: MEASURED over stdio, an exception reaches
    # the client as isError plus a text blob and the exception CLASS is dropped.
    # UpstreamUnavailable and ValueError are indistinguishable on the wire unless
    # the discriminator is in the string. UPSTREAM_UNAVAILABLE means retry the
    # same call; BAD_ARGUMENT means the caller must change something.
    rows = state.search(query)
    try:
        n = int(limit)
    except ValueError as exc:
        raise ValueError(
            f"{state.ARGUMENT_CODE}: limit must be an integer, got {limit!r}. "
            f"Retrying unchanged will fail identically."
        ) from exc
    return {"query": query, "count": len(rows[:n]), "tickets": rows[:n]}


def main() -> None:
    # WHY: run() blocks and owns the event loop. Anything printed to stdout here
    # would corrupt the JSON-RPC stream - stdio is the protocol channel, not a
    # log. Diagnostics belong on stderr.
    server.run(transport="stdio")
