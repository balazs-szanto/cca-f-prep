# D5 — Context Management and Reliability

## The concept

The context window is not your conversation. Before you send a character, the
system prompt, tool schemas, skill descriptions and memory files are already
resident — MEASURED 2026-08-20 at 12,407 tokens of 200,000, with auto-compaction
armed to fire at 167,000. That resting cost is rent you pay on every turn, and it
is the number that decides how many turns you actually get.

There is a second number, and the SDK's own output invites you to read the wrong
one. In the same reading, the `Free space` category reported 185,085 tokens while
the distance to the compaction threshold was 152,141. Both are true and only the
smaller one is operational: roughly 33,000 tokens of that "free" space cannot be
used without triggering a summarisation of your own transcript. `context_budget.py`
now prints the two side by side for exactly this reason. It measures the approach
to the threshold and says plainly that it never crosses it — what happens on the
other side is documented, not observed here.

When the window fills, compaction replaces older turns with a summary. You buy
continuation and pay in verbatim detail: exact identifiers, error strings and
edge-case reasoning inside compacted turns become whatever the summariser
considered worth keeping. It is lossy, automatic, and nothing tells the model
what it used to know. Anything you cannot afford to lose should not live only in
the transcript.

Reliability has a second half: failures do not all arrive the same way, and
sorting them by *who can recover* is what makes them tractable. A host failure —
a missing binary, a dead socket — raises a Python exception and the model never
sees it; only your process can fix it. An environment failure reaches the model
as a tool result flagged `is_error`, and the right response is to retry the
identical call. An argument failure looks identical on the wire and needs the
opposite response: change the call or stop. A reasoning failure raises nothing at
all and sets no flag — the response is schema-valid and wrong, and only a
host-side invariant sees it. One try/except catches exactly one of these four.

The middle two deserve care because nothing structural separates them. MEASURED:
an exception's class does not cross an MCP transport, so `UpstreamUnavailable`
and `ValueError` arrive as the same shape. The discriminator has to be inside the
message you return — `mockserver` uses `UPSTREAM_UNAVAILABLE:` and
`BAD_ARGUMENT:` prefixes, and `error_taxonomy.py` sorts on them successfully.
Note the limit of that: MEASURED, the model retried the argument failure anyway,
despite the text saying retrying would fail identically. Classification helps
your code decide. It does not make the model obey.

A fourth shape breaks even that classification. Hitting `max_turns` or
`max_budget_usd` does both things at once: `query()` yields a `ResultMessage`
with subtype `error_max_turns`, carrying usage and session id, and then raises —
deliberately. Read only the result and a truncated run looks like a finished one;
catch only the exception and you throw the accounting away. Streaming sessions
via `ClaudeSDKClient` do not raise at all, so the handling does not transfer.

## Where it lives in this repo

- `src/playground/reliability/context_budget.py` — the resting cost, the category
  breakdown, and the auto-compaction threshold, read before and after one turn.
- `src/playground/reliability/error_taxonomy.py` — four failure classes provoked
  deliberately, three of them through a model, and sorted by who can recover. The
  environment and argument cases run `mockserver`'s `flaky_search` in-process,
  with the same failure semantics it has over stdio.

Two files in `src/playground/reliability/` are **not** D5 material and are
labelled D1: `session_resume.py` and `session_fork.py`. The blueprint puts
session state, resumption and forking in task statement **1.7**, under Agentic
Architecture, and this repo had `session_resume` filed here on the strength of
the directory name until 2026-08-21. They stay in this directory because they
are one subject with each other; see `d1-orchestration.md` for what they show.

## Common trap

Believing `usage["input_tokens"]` is your input cost. It counts only uncached
input. A real turn in this repo reported `input_tokens: 10` alongside
`cache_read_input_tokens: 11200` — read the first number alone and the turn looks
essentially free. Any cost comparison that omits `cache_read_input_tokens` and
`cache_creation_input_tokens` is off by three orders of magnitude, and it fails
in the flattering direction, which is why it survives review.

## Scenario questions

1. A long-running agent starts giving answers that contradict what it was told an
   hour earlier. No errors are logged. What is your first hypothesis, how do you
   confirm it, and what is the fix?

2. Your agent calls a pricing tool that returns an error for an unknown part.
   Should the tool raise a Python exception or return `is_error`? What changes
   about the agent's behaviour either way?

3. A service resumes user sessions by session id after a process restart. It
   works in staging and drops context in production. Name two causes that fit,
   and how you would tell them apart.

<details>
<summary>Answers</summary>

**1.** Compaction fired. The agent is not contradicting itself; the turns holding
the original instruction were replaced by a summary that dropped the detail.
Confirm with `get_context_usage()` — compare `totalTokens` against
`autoCompactThreshold` and watch whether the Messages category dropped between
readings. The fix is not a bigger window, which only postpones it: move the
durable facts out of the transcript and re-inject them each turn as a short state
block, a memory file, or a scratch file the agent re-reads.

**2.** Return `is_error`. The failure stays inside the conversation, so the model
reads it as a tool result and can choose a different part code, ask the user, or
say plainly that the lookup failed. Raising propagates out of the agent loop into
your process, ending the run for a condition the agent could have handled — and
worse, if you catch and retry blindly, you re-run the identical call. Reserve
exceptions for failures the model genuinely cannot act on, such as a missing CLI
binary.

**3.** First: compaction. Production sessions are longer, so they cross the
threshold staging never reaches, and the resumed transcript is the compacted one.
Second: a changed tool surface. Only the transcript is persisted — in-process
state, tool closures and SDK MCP server instances are rebuilt from your code, so
a resumed session running a deployment with a different tool list is a different
agent wearing the same history. Tell them apart by reading
`get_context_usage()` on the resumed session: if the Messages category is far
smaller than the transcript length implies, it is compaction. If the token counts
look right but the agent no longer uses a tool it used before, it is the tool
surface.

</details>
