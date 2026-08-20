# Traps

Two kinds. The first are anti-patterns the demos demonstrate on purpose. The
second were found while building this repo, with evidence — they are here because
they cost real debugging time and every one of them failed quietly.

Where a trap depends on how a particular setup is configured, it says so and
tells you how to check rather than asserting what you will see. Some of these
will not reproduce for you, and that is information too.

## Anti-patterns the demos deliberately show

| Trap | Shown in | Domain |
|------|----------|--------|
| Free-form string parameter where the input space is closed | `tools_mcp/schema_design.py` | D4 |
| Hardcoding `allowed_tools` against an external server you do not version | `tools_mcp/external_mcp.py` | D4 |
| Treating `allowed_tools` as an argument-level security control | `tools_mcp/permission_gate.py` | D4 |
| Assuming a workflow is cheaper than an agent | `orchestration/workflow_vs_agent.py` | D1 |
| Delegating a sub-task with nothing bulky to isolate | `orchestration/subagent.py` | D1 |
| One `try/except` around the agent call | `reliability/error_taxonomy.py` | D5 |
| Trusting schema validity as correctness | `reliability/error_taxonomy.py` | D5 |
| Assuming multi-turn continuity survives a process restart | `reliability/session_resume.py` | D5 |
| Believing the context window is "my conversation" | `reliability/context_budget.py` | D5 |
| Enforcing a must-hold rule in a memory file instead of a hook | `.claude/hooks/block_secret_reads.py` | D2 |

The three worth expanding, because the code alone does not make them obvious:

**A workflow is not automatically cheaper.** `workflow_vs_agent.py` measured the
workflow as the *more* expensive shape — three calls each re-paid the fixed
per-call overhead of the harness, which dwarfed the actual work. The label was
irrelevant; batch granularity drove the bill.

**A subagent's product is a clean context window, not tidiness.** If the
sub-task has nothing large and disposable to read, delegation buys isolation you
do not need and charges a round trip plus a second system prompt for it.

**Schema validity is not correctness.** A response can satisfy every type,
enum and required field and still be arithmetically wrong. Only a host-side
invariant check sees it, and a blind retry reproduces the same class of error.

## Environment traps found while building this repo

**A settings file that exists is not a settings file that applies.** Permission
entries in `.claude/settings.json` can be ignored for reasons that have nothing
to do with the file being correct, and when that happens the only signal is a
line on stderr — the run continues normally. Observed while building this repo:
a stderr line reporting that N `permissions.allow` entries were being ignored,
on every single run, for a file that was valid. If you rely on a `deny` rule for
safety and do not read stderr, you can be unprotected and confident at the same
time. Check rather than assume: run once with stderr visible and read what it
says about your settings before trusting any rule in that file.

**`sys.stdin` in a hook uses the ANSI codepage on Windows.** The hook originally
called `json.load(sys.stdin)`. A single accented character in a tool input — an
ordinary Hungarian filename — raises `UnicodeDecodeError`, and with fail-open
error handling the guardrail silently disarms exactly when the input is unusual.
Fix: `sys.stdin.buffer.read().decode("utf-8-sig")`, and fail closed.

**Hitting `max_turns` both returns a result and raises.** This entry originally
said the SDK "raises, it does not merely cap", which was the wrong conclusion
drawn from a real observation. Now MEASURED end to end, 2026-08-20 in
`error_taxonomy.py`: `query()` yields a `ResultMessage` with
`subtype='error_max_turns'` and `num_turns=4`, and *then* raises `ResultError`.
Documented as deliberate — "The raise is intentional"
(<https://code.claude.com/docs/en/agent-sdk/agent-loop>, fetched 2026-08-20).
Inspect only the result and a truncated run looks finished; catch only the
exception and you discard the accounting. A streaming `ClaudeSDKClient` session
does not raise at all, so error handling does not transfer between the two.

**A measurement harness without that try/except loses the measurement.** Twice
now, in this repo, by the same author who had just written the entry above. The
first version of `error_taxonomy.py`'s search probe had no `try`, so the raise
escaped, the process exited 1, and the taxonomy verdict at the end of `main()` —
the entire point of the run — never printed. The failure looks like a crash in
your code, not like a documented control-flow feature, which is exactly why it
gets rediscovered.

**The model retries a non-retryable error.** MEASURED 2026-08-20: the
bad-argument probe returned `BAD_ARGUMENT: limit must be an integer, got 'ten'.
Retrying unchanged will fail identically.` The model retried anyway, and the run
ended `error_max_turns` at 4 turns. So an explicit "do not retry" in the error
text is not a control — it is a hint the model may ignore. If a retry is
genuinely pointless, the caller has to stop it, or the tool has to succeed with a
degraded answer instead of failing.

**`num_turns` can exceed `max_turns` without erroring.** MEASURED seven times on
2026-08-20, across five different files: 6 against a cap of 3 finishing
`success` (twice, in `permission_gate.py`), 3 against a cap of 2 finishing
`success` (`structured.py`), 5 against a cap of 3 finishing `success`
(`workflow_vs_agent.py`), 4 against a cap of 3 finishing `error_max_turns`
(twice), and 4 against a cap of 5 finishing `success` (`tools.py`). The counter
and the cap are not reading the same quantity, and the gap is not a constant
offset either. `num_turns` cannot tell you how close you are to the limit.
Branch on `subtype`, not on arithmetic. No documentation found while building
this repo explains the discrepancy; the best available reading is INFERRED, that
`num_turns` counts every assistant turn while the cap counts only tool-use round
trips. `basics/tools.py` carries the same warning at the line where it bites.

**A turn cap sized by house style instead of by measurement truncates the demo.**
Found in this repo on 2026-08-20, by the author, in the file least likely to hurt.
`basics/tools.py` originally set no `max_turns` at all and worked. Adding
`max_turns=3` to satisfy the repo's own cost rule broke it on the next run:
`(17 + 8) x 4` is two tool calls plus an answer, the run ended `error_max_turns`,
and — because the same file had no `try` around `query()` — the raise escaped and
took the closing explanation with it. Both halves are the general lesson. A cap
is a budget you size against the task, and any harness that measures something
needs the `try`, or it loses the measurement precisely when the run is
interesting.

**`Free space` is not space you can use.** MEASURED 2026-08-20 in
`context_budget.py`: one reading reported a `Free space` category of 185,085
tokens and an auto-compact threshold 152,141 tokens away. The difference is real
capacity that you cannot occupy without triggering a summarisation of your own
history. A category name is not a budget, and this one errs optimistic.

**`usage["input_tokens"]` excludes cached input.** A real turn reported
`input_tokens: 10` next to `cache_read_input_tokens: 11200`. Any cost comparison
that omits the cache fields is wrong by orders of magnitude, and it errs in the
flattering direction, which is why it survives review.

**A model may decline to call an in-process tool, claiming it needs
authentication.** MEASURED twice, in two unrelated demos, and intermittent rather
than reliable — identical code and prompt worked on the adjacent run both times.
The reply says the lookup "requires authentication" and directs you to authorise
the server interactively or in connector settings. There is no server to
authorise: `create_sdk_mcp_server` is a registry of Python functions inside your
own process, with no transport and no auth of any kind. INFERRED as to cause, and
the honest reading is that the model is reasoning about MCP from general
knowledge rather than about the tool in front of it. Two consequences worth
carrying: a tool being available is never a guarantee it will be used, and a
refusal of this kind arrives as an ordinary successful turn — no exception, no
`is_error`, nothing your error handling will notice. If a step must call a tool,
assert that it did. Written up at the line where it bit, in
`orchestration/triage.py`'s STAGE 3 NOTE. Unsettled: settling it would mean
capturing the system prompt and tool definitions the CLI actually sends, and
checking what the model is told about an in-process server's identity.

**A refused MCP server is not an exception.** When an attachment is declined, the
reason is written to the CLI's stderr and the server list simply comes back
empty. Without a `stderr` callback it is indistinguishable from a crashed server
process — and in the case that prompted this entry, the server binary started
fine when run standalone, so every instinct pointed at the wrong half.

## Traps found while building the mock server

**An `allowed_tools` entry silences `can_use_tool` for that tool.** This is the
worst trap in the repo, because the failure reports success. The documented
evaluation order settles why (<https://code.claude.com/docs/en/agent-sdk/permissions>,
fetched 2026-08-20): hooks → deny rules → ask rules → permission mode → **allow
rules** → `canUseTool`. An allow rule approves at step 5, so step 6 never runs.
The page says it outright: "Auto-approved tools never reach `canUseTool` … so
permission checks you put there are silently bypassed for that tool."

MEASURED 2026-08-20: the first version of `permission_gate.py` listed its
destructive tool in `allowed_tools` *and* passed a gate. Every protected record
was deleted, `permission_denials` came back `[]`, and the run ended `success`.
Removing the tool from `allowed_tools` and setting `permission_mode="default"`
fixed it — same gate, same prompt, protected records intact, both refusals
recorded.

Two details worth carrying:

- **Coverage depends on the entry's form.** A bare name like `Read` or
  `mcp__srv__tool` auto-approves every call to that tool. A scoped rule like
  `Bash(ls *)` auto-approves only matching calls, and the rest still reach the
  callback. The bug used a bare MCP name, so the shadowing was total.
- **The SDK warns about this, and the warning was thrown away.** MEASURED at
  connect time for zero tokens: the buggy config emits
  `CanUseToolShadowedWarning: can_use_tool will not be invoked for:
  mcp__p__noop`; the fixed config emits nothing. It went unseen for a full run
  because the run was piped with `2>$null` to hide unrelated workspace-trust
  noise, and Python warnings go to stderr. Suppressing a noisy channel suppresses
  the signal in it.

**A `PreToolUse` hook is *not* shadowed the same way.** Hooks are step 1, before
deny, allow and mode, and "a hook deny applies even in `bypassPermissions` mode".
So the `.claude/settings.json` in this repo — seven allow entries plus a hook on
`Read|Bash` — is the same *shape* as the bug above but not the same defect. For a
check that must run on every call, the documentation is explicit that a hook is
the mechanism and `canUseTool` is not.

**"But it is only a local server" is not a defence.** MEASURED while building
this repo: `src/mockserver`, a local Python stdio server spawned with
`sys.executable -m mockserver`, was refused exactly as the npx filesystem server
had been, with the same message. Nothing about npx, the package registry or the
network was involved. The lesson generalises past the specific setup: whatever
decides that an external MCP server may be attached does not appear to care that
the process is local, or yours, or written in the same language as the client.
In-process `create_sdk_mcp_server` tools were unaffected, which is why
`permission_gate.py` uses one — and see `d4-tools-mcp.md` for why that asymmetry
is the point rather than a loophole.

**An exception's class does not survive the MCP transport.** MEASURED 2026-08-20
by driving `src/mockserver` over stdio by hand: a tool that raises reaches the
client as `isError: true` plus a text blob, and the exception type is gone.
`UpstreamUnavailable` and `ValueError` are indistinguishable on the wire. If a
caller needs to tell "retry this" from "fix your arguments", the discriminator
has to be inside the message — `mockserver` prefixes `UPSTREAM_UNAVAILABLE:` and
`BAD_ARGUMENT:` for exactly this reason.

## Traps that official documentation settles

Unlike the sections above, each of these is documented rather than merely
observed — the URL and fetch date are given so you can check whether it still
says that.

**Unsupported JSON Schema keywords are ignored, not rejected.** `minimum`,
`maximum`, `multipleOf`, `minLength` and `maxLength` are listed as not supported
for structured outputs and strict tool use
(<https://platform.claude.com/docs/en/build-with-claude/structured-outputs>,
fetched 2026-08-20). Putting them in a schema produces no error — measured
2026-08-20 in `tools_mcp/schema_design.py`, which ran clean with all three. This
is the worse of the two possible behaviours: a schema that fails loudly teaches
you in one run, while one that silently drops half its constraints passes review
and misleads every reader afterwards. Only the declared types, `enum`, `const`,
`required`, `additionalProperties: false`, `$ref`, `default` and the named string
`format`s actually bind. `strict: true` does not widen that list — strict and
non-strict "share these limitations".

**A nested `CLAUDE.md` does not survive compaction.** The project-root file does:
"after `/compact`, Claude re-reads it from disk and re-injects it into the
session." Nested files and path-scoped rules "are not re-injected automatically;
they reload the next time Claude reads a file in that subdirectory"
(<https://code.claude.com/docs/en/memory>, fetched 2026-08-20). So a rule you put
in a subdirectory memory file stops applying at the compaction boundary and
returns only on the next read in that subtree. Combined with the fact that nested
files load lazily in the first place, a nested rule is absent more often than it
is present. Rules that must hold for a whole session belong in the root file.

**`max_turns` has no default.** Unset means no limit
(<https://code.claude.com/docs/en/agent-sdk/agent-loop>, fetched 2026-08-20), so
an agent with an open-ended prompt and no cap runs until it decides to stop.
Sources outside the official docs disagree on this; they are wrong.
