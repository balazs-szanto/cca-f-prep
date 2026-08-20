# mockserver — a fake ticket tracker behind a real MCP transport

A peer process, not part of `playground`. The demos in
`src/playground/tools_mcp/` spawn it the way any MCP client spawns any stdio
server: as a command line, over pipes, speaking JSON-RPC.

**The transport is genuine; the data is invented.** That is the entire point.
`external_mcp.py` used to reach for `@modelcontextprotocol/server-filesystem` via
`npx`, which makes a demo depend on a package registry, a network, and whatever
governs external MCP servers wherever it runs — so it could not be relied on to
complete. Nothing here needs the network, a database, a clock, or a file. Two
runs produce identical output.

## Run it standalone

    uv run python -m mockserver

It starts and waits on stdin. There is no banner, because stdout is the protocol
channel — anything printed there corrupts the stream. It looks like a hang; it is
not.

## Talk to it by hand

Four newline-delimited JSON-RPC messages: initialize, the initialized
notification, then two requests. Nothing responds before the handshake completes.

**Read this before pasting, or you will silently lose a response.** The obvious
form — `printf` all four lines straight into a pipe — does not work, and it does
not tell you so. MEASURED: the handshake and `tools/list` are answered, the
`tools/call` is not, and you get two responses to four messages with no error and
no exit code to notice. Two separate causes stack up: the server has not finished
starting when a pipe delivers its first bytes, and a `tools/call` arriving in the
same batch as `tools/list` immediately after initialization is dropped. The waits
below exist to defeat both. They are ugly and they are the point — this is what
"speaking a protocol by hand" actually costs, and it is why real clients wait for
a response before sending the next request instead of firing and hoping.

```bash
{ sleep 4
  printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"manual","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}'
  sleep 2
  printf '%s\n' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_ticket","arguments":{"ticket_id":"TCK-001"}}}'
  sleep 2
} | uv run python -m mockserver
```

You should get exactly three responses, with ids 1, 2 and 3. Fewer means a
message was dropped; lengthen the waits. Counting the responses is the only way
to notice, which is the lesson.

**There is no PowerShell equivalent here, deliberately.** This file used to carry
one, and it did not work: PowerShell does not reliably pace writes into a native
process's stdin, so `Start-Sleep` between strings in a pipeline does not separate
them the way `sleep` does between two `printf` calls in a shell brace group. Two
attempts were measured — a `& { ... } | python` pipeline returned one response of
three, and a `System.Diagnostics.Process` driver with explicit flushes returned
two. Rather than ship a third guess, the honest statement is that only the bash
form above is verified. On Windows, run it under Git Bash, or drive the server
from a short Python script that reads each response before sending the next
request — which is what a real client does, and the reason this section is
awkward in the first place.

MEASURED 2026-08-20: the first response is
`{"id":1,"result":{...,"protocolVersion":"2025-11-25","serverInfo":{"name":"tickets","version":"1.0.0"}}}`.
Sending `"protocolVersion":"2026-07-28"` also works — the server negotiates down
and answers `2025-11-25` regardless, so the client's requested version is a
ceiling, not a demand.

## Tools

| Tool | Kind | Schema |
|------|------|--------|
| `list_tickets(status, assignee)` | read | **WEAK on purpose** |
| `get_ticket(ticket_id)` | read | strong |
| `update_status(ticket_id, status)` | write, reversible | strong |
| `delete_ticket(ticket_id, confirm)` | destructive | strong |
| `flaky_search(query, limit)` | read | **WEAK on purpose** |

"Strong" here means only what a schema can actually enforce: the declared types,
`enum` (which `Literal` produces), and which parameters are required. Ranges, id
formats and the like live in descriptions and bind nothing — this repo has
already established that unsupported JSON Schema keywords are accepted and
silently ignored, so no claim is made for them.

The two weak schemas are wrong in a way that costs you nothing until it does:

- `list_tickets(status=...)` takes a bare string for a field with three legal
  values. MEASURED: `status="Open"` returns `{"count": 0, "tickets": []}` — no
  error, no warning, just a wrong answer that reads like a right one.
- `flaky_search(limit=...)` takes a count as a string. Sending `"ten"` produces
  a `BAD_ARGUMENT` failure that a correctly typed schema would have prevented.

Compare `update_status`, where `Literal[...]` becomes a real `enum`. MEASURED:
`status="bogus"` is rejected before the function body runs, with a Pydantic
`literal_error`. Note *where* that enforcement happens — in this server's own
validation layer, not in the model API. They are different layers with different
guarantees.

## flaky_search, and why it exists

It raises on the **first call of each process** and succeeds on every call after.
Deterministic, so `error_taxonomy.py` has a real environment failure to catch
rather than a described one.

MEASURED, and it changed the design: a raised exception reaches the client as
`isError: true` plus a text blob, and **the exception class is not transmitted**.
`UpstreamUnavailable` and `ValueError` are indistinguishable on the wire. So the
discriminator has to be in the message:

- `UPSTREAM_UNAVAILABLE: ...` — the arguments were fine, retry the identical call.
- `BAD_ARGUMENT: ...` — retrying unchanged will fail the same way.

Restart the process to re-arm the failure. There is no reset tool, deliberately:
a tool that repairs the demo's state is a tool the model can call by accident.

## Files

- `state.py` — seed data and mutations. No transport, so it can be exercised
  without speaking MCP.
- `server.py` — the five tools and the stdio entry point.
- `__main__.py` — makes `uv run python -m mockserver` work.
