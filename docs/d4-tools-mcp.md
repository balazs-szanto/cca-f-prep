# D4 — Tool Design and MCP Integration

## The concept

A tool schema is prompt engineering with a type system attached, and only part of
it is enforced. A constraint expressed as an `enum` is obeyed; the same
constraint expressed as "please use one of these values" is a suggestion. But
there is a third category worth more attention than either: keywords the schema
grammar accepts and the platform does not implement. `minimum`, `maximum`,
`multipleOf`, `minLength` and `maxLength` are documented as unsupported, and they
are ignored rather than rejected — no error, no warning. For those fields the
tool *description* is doing the work the schema appears to be doing, which
inverts the usual advice. Design the schema for what binds; write the description
for everything else.

MCP adds a second axis: where the tool runs. An in-process SDK server
(`create_sdk_mcp_server`) is a closed world you control — no transport, no
versioning, no startup cost. An external server over stdio is a contract you do
not own: a separate process, released on someone else's schedule, and — because
it is visible from outside your program — something a deployment can be
configured to refuse. That last part is not a footnote. In the environment this
repo was written in, `external_mcp.py` could not attach its server at all, which
is why it ships as a declared `KNOWN_ISSUE` rather than as a working demo. Run it
to find out which case you are in.

The architectural lesson is that your tool surface is not a constant. It can be
narrowed by an org policy, changed by a server upgrade, or restricted per call by
a permission callback. Code that hardcodes tool names assumes a stability nobody
promised. Discovery is the honest alternative.

## In-process tools versus an external server

Both give the model a tool. What differs is who owns the process it runs in, and
that single fact drives everything else.

An in-process tool (`create_sdk_mcp_server`) is a Python function in your own
program. There is no handshake, no serialisation of your state, no second
interpreter, and no startup cost. You can hold a reference to a live object and
mutate it. `basics/tools.py` and `tools_mcp/permission_gate.py` both work this
way. The price is that it exists only inside this program: no other client can
call it, it cannot be written in another language, and — the part that surprises
people — no policy layer inspects it, because from the outside there is nothing
to inspect.

An external server (`src/mockserver`, spawned by `tools_mcp/external_mcp.py`) is
a separate process reached over stdio. You get a real wire protocol, a real
handshake, language independence, and reuse: the same server can back a second
client tomorrow. You pay process startup on every run, a failure surface that
arrives as a connection status rather than an exception, a dependency on client
and server agreeing about which interpreter to use — and governability. Being a
separate, externally visible process is what makes an external server something a
deployment can decline to attach. MEASURED while writing this repo: when an
attachment is declined, being a purely local Python process is no protection —
locality is not the axis that decides it.

So the extra process is worth it when a second consumer exists, when the tools
are not Python, or when you want the failure isolation of a real boundary. It is
not worth it for tools only this program will ever call — and if your environment
declines external servers, in-process is not merely cheaper, it is the only
option that runs. Note the direction of that last point: an in-process tool is
invisible from outside your program, and that invisibility is convenient for you
for exactly the same reason it is unattractive to whoever has to govern the
tool surface.

A detail worth carrying: an exception's class does not cross the transport. A
raised error reaches the client as `isError: true` and a text blob, so
`UpstreamUnavailable` and `ValueError` look identical. In-process tools have the
same constraint for a different reason — the model reads a tool result, not a
traceback. Either way, machine-readable failure information has to be inside the
payload you return, which is why `mockserver` prefixes `UPSTREAM_UNAVAILABLE:`
and `BAD_ARGUMENT:`.

## Where it lives in this repo

- `src/playground/basics/tools.py` — the V1 starting point: one in-process tool.
- `src/playground/tools_mcp/where_code_runs.py` — the same question against a
  tool implemented here and one implemented nowhere here, with every content
  block's class name printed. Both arrive as `ToolUseBlock`, so the client and
  server sides of the section above are **not** distinguishable from the SDK's
  message stream; the only signal is whether your own handler was invoked.
- `src/playground/tools_mcp/schema_design.py` — one tool, weak schema and strong
  schema, with the arguments the model actually produced printed side by side.
- `src/playground/tools_mcp/parallel_tools.py` — two independent lookups against
  two dependent ones, grouped by assistant turn and timed. A null result on the
  grouping and a hundred-to-one difference on the clock.
- `src/playground/tools_mcp/tool_overhead.py` — what the tools array costs before
  anything calls it, for zero model calls. Also the demo in which the measuring
  instrument returns a plausible wrong number if you read it too early.
- `src/playground/tools_mcp/external_mcp.py` — spawns the mock over stdio,
  discovers its tools for zero tokens, and handles a policy block as a declared
  outcome: it prints a `KNOWN_ISSUE` block and stops, rather than crashing or
  pretending. Everything below that point in the file has never run on this
  account, and its `LESSON` says so in the word INFERRED. See `docs/status.md`.
- `src/playground/tools_mcp/permission_gate.py` — `can_use_tool` refusing a
  destructive call on a rule the schema cannot express.
- `src/mockserver/` — a real stdio MCP server with fake ticket data. Its
  `README.md` shows how to drive it by hand with four lines of JSON-RPC, which is
  the cheapest way to understand what the transport actually carries.
- `docs/tool-surface.md` — the boundary this page sits inside. It triages every
  page of the official tool-use documentation set and names the nine that need
  the Messages API and are therefore documented here rather than demonstrated.
  Read it before treating the files above as coverage of tool use.

## Common trap

Treating `allowed_tools` as a security control — and the specific way that
backfires is worse than the general point. An allow rule does not mean "this tool
is permitted", it means **auto-approve without asking**. The documented order is
hooks → deny → ask → mode → allow → `canUseTool`, so an allow rule resolves the
call one step before your callback is consulted and the callback never runs.
Listing a destructive tool in `allowed_tools` while also passing a gate does not
give you two layers of protection; it gives you none, silently. A `PreToolUse`
hook is the opposite case — step one, before everything, and a hook deny holds
even in `bypassPermissions`.

MEASURED 2026-08-20: the first version of `permission_gate.py` did exactly this.
Every protected record was deleted, `permission_denials` returned `[]`, and the
run reported `success`. Removing the tool from `allowed_tools` and setting
`permission_mode="default"` — same gate, same prompt — left the protected records
intact with both refusals recorded. The tool remained available throughout;
`mcp_servers` is what exposes a tool, and the allowlist only decides what runs
unattended.

Even with the gate wired correctly, note what it cannot see: it inspects one call
at a time, so three individually harmless deletions that together empty a table
pass every check.

## Scenario questions

1. A tool takes `{"filter": "string"}` and the model keeps passing filters your
   backend cannot parse. A colleague proposes adding three sentences to the
   system prompt explaining the syntax. What do you propose instead, and when
   would the colleague be right?

2. Your agent depends on an external MCP server. Security announces that all
   non-allowlisted MCP servers will be blocked next month. What breaks, when do
   you find out, and what would have made this a non-event?

3. You must let an agent delete records but never the two protected accounts.
   Compare enforcing this in `can_use_tool` versus inside the tool
   implementation. Which do you pick and what does the loser cost you?

<details>
<summary>Answers</summary>

**1.** Move the constraint into the schema: an enum if the filter values are
closed, or split `filter` into typed fields — `field`, `operator`, `value` — if
it is structured. The model obeys schema constraints far more reliably than
prose, and you get validation for free. The colleague is right when the input
space is genuinely open, such as a free-text search query. Then a string is
correct and the fix is host-side parsing with a clear error returned as
`is_error`, so the model can retry with better input.

**2.** Every call to that server's tools fails. You find out at runtime, in
production, on security's schedule, not yours — and if `allowed_tools` was
hardcoded the failure looks like a tool that silently does not exist rather than
a decision someone made. Two things would have made it a non-event: discovering
the tool list at startup and building the allowlist from it, so an empty result
is detected immediately; and capturing stderr, since a refusal is written there
and never raised as an exception. `external_mcp.py` does both.

**3.** Enforce it in `can_use_tool` — and then check that the tool is absent from
`allowed_tools`, or you have written a gate that never runs. With that wired
correctly the refusal reaches the model as a permission denial with a message it
can act on, it is recorded in `ResultMessage.permission_denials` for audit, and
the rule lives next to the other policy decisions rather than buried in business
logic. Enforcing inside the
tool is simpler and genuinely unbypassable, but you lose the audit record and the
model learns about the refusal as an ordinary tool result — indistinguishable
from the record not existing. The honest caveat: the gate runs in your process on
every call, so a slow or throwing callback stalls or breaks the agent loop.

</details>
