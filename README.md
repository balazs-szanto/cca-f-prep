# Claude Agent SDK Playground

A lab manual in two halves. **`playground/`** is eighteen demos on the Claude
Agent SDK, each isolating one architectural decision and printing what it costs.
**`examlab/`** is twelve modules on the request/response layer underneath it —
the agentic loop, `tool_choice`, prompt chaining, review criteria, structured
output, validation-retry, batching, iterative refinement, confidence
calibration and provenance — which the Agent SDK owns on your behalf and
therefore never shows you. Every
module tells you on screen what to set up, what to run, what you should see,
and what it proves, so the console teaches as much as the docs do.

The two halves share one dispatcher and one set of domain labels. What differs
is the auth rule, and that difference is deliberate — see section 7.

Every `DOMAIN` label in the repo is the official CCA-F blueprint's, as of the
relabel on 2026-08-21. Before that they were the author's own and two of the
five numbers were transposed, so anything written earlier disagrees;
[`docs/domain-map.md`](docs/domain-map.md) carries the old-to-new map. Read it
for the gap report too: which demos land in a domain the exam does not test
there, and which task statements have a written reason for having no demo.

## What this repo does, and what it does not

It does **not** authenticate anything. The Agent SDK spawns the Claude Code CLI
as a subprocess, and that CLI resolves credentials on its own — OAuth session,
API key, or a cloud provider — with no involvement from this code. What this repo
does is **check which credential the CLI will use, and tell you when it is not
the one this repo is written around**. `basics/check_auth.py` shells out to
`claude auth status --json`. It exits 1 unconditionally if `ANTHROPIC_API_KEY` is
set. If `authMethod` is anything other than `claude.ai` it explains the rule,
why the rule exists, and three ways forward — including `PLAYGROUND_ALLOW_ANY_AUTH=1`
to proceed knowingly. See section 3.

The same distinction applies to everything under `.claude/`. Those files
configure Claude Code, the interactive tool. They are **not** exercised by
`playground.run` — the hook never fires during a demo. Read them as configuration
you would ship, and test them in an interactive session.

## 1. Install

Requires Python 3.11+, [`uv`](https://docs.astral.sh/uv/), and the Claude Code
CLI, logged in with `claude auth login`.

    git clone https://github.com/balazs-szanto/cca-f-prep.git
    cd cca-f-prep
    uv sync                                        # creates .venv, installs the SDK

`uv.lock` is committed on purpose: it pins the exact dependency set every
measurement in [`docs/status.md`](docs/status.md) was taken against, so `uv sync`
reproduces the versions those numbers came from. `uv sync --upgrade` is fine to
run, but it resolves newer packages and may change measured behaviour — if a
demo then prints something the docs do not describe, that is the first thing to
suspect.

Then, from the repo root:

    uv run python -m playground.run --list         # every demo, in reading order

Use `uv run python`, not bare `python`. The demos import the `playground` and
`mockserver` packages from `.venv`; a system interpreter will fail with
`ModuleNotFoundError: No module named 'playground'`. If you would rather activate
the venv once (`.venv\Scripts\activate` on Windows), bare `python` works too and
every command below drops the `uv run` prefix.

## 2. Know what you are about to spend

`--list` marks every demo:

| Marker | Meaning |
|--------|---------|
| (blank) | **Free.** No model call at all. |
| `$` | Spends quota. The `cost` line in the demo's own banner says how much. |
| `!` | Has a declared `KNOWN_ISSUE` and will not complete in this environment. |

The markers are not maintained by hand — they are read out of each module's
`LESSON` block by `playground/lessons.py`, which parses the source with `ast`
rather than importing it, because importing a demo runs it.

**You can do most of this repo for nothing.** Fourteen of the thirty demos are
marked free, and a fifteenth — `external_mcp` — is free wherever the server
declines to attach, which is why it carries `!` rather than a blank. Free right
now:

- **All twelve `examlab` modules**, which is the whole of section 7. They make no
  model call and no network call at all, and they carry the raw loop,
  `tool_choice`, chaining, review criteria, structured output, validation-retry,
  batching, refinement, confidence calibration and provenance. If quota is your
  constraint, start there rather than here.
- `basics.check_auth` — makes no model call.
- `tools_mcp.tool_overhead` — makes no model call either, and it is the one to
  run if you only run one. It measures what a tools array costs before anything
  calls it, using control requests rather than inference, so you can rerun it as
  often as you like while you argue with it.
- `tools_mcp.external_mcp` — free *if* your setup declines to attach the server,
  because it stops before the model call. If it does attach, it costs one call.
  Run it to find out which; it tells you.
- `src/mockserver` driven by hand — a real MCP server over stdio, four lines of
  JSON-RPC, no model in the loop. See [`src/mockserver/README.md`](src/mockserver/README.md).
- Every document in `docs/`, including [`docs/lessons.md`](docs/lessons.md),
  which is the whole set of banners in one page.
- Testing the `PreToolUse` hook directly (section 6).

That leaves fifteen `$` demos, all of them under `playground/`, which together
cost a few cents against your subscription quota. They pin `claude-haiku-4-5` and
cap `max_turns`, and each one names its own cost in its banner before it runs.
If these counts ever disagree with `--list`, believe `--list`: it derives them
from each module's `LESSON` block, and this paragraph is maintained by hand. The
three numbers here — 14, 1 and 15 — were checked against `--list` on 2026-08-21
by counting its markers, which is the only way this paragraph gets checked at all.

## 3. Ground yourself

Run these five in order. They are the whole SDK in miniature.

These five are **prerequisites, not a domain.** They used to be filed under a
label of this repo's own called "D0 Foundations", and the relabel of 2026-08-21
dissolved it, because the official blueprint has no such domain and the five have
nothing in common except that everything later assumes them. They now land in
four different domains — `check_auth` in D3, `hello` in D1, `tools` in D2,
`prompt_shape` and `structured` in D4 — and they stay together here anyway, since
reading order and domain are different questions.

Two of the five are honest near-misses against the domain they landed in, and
[`docs/domain-map.md`](docs/domain-map.md) says which and why: `check_auth`'s
subject is on the guide's *out-of-scope* list, and `prompt_shape` matches none of
D4's six task statements. Both are still worth running. Neither will be examined.

| # | Run | Free? | What it teaches |
|---|-----|-------|-----------------|
| 1 | `basics.check_auth` | free | Which credential is paying, and why your code cannot control that — only refuse. |
| 2 | `basics.hello` | `$` | `query()` is an async generator over typed messages. The run *is* the loop, and `ResultMessage` is the only place its numbers exist. |
| 3 | `basics.prompt_shape` | `$` | What is instruction and what is data is a convention you construct. Also a worked null result: the comparison came out flat, twice, and says so instead of being tuned until it did not. Filed under D4 on the domain's name; its actual subject is not in the blueprint. |
| 4 | `basics.structured` | `$` | `output_format` enforces shape from outside the prompt — and *only* shape. |
| 5 | `basics.tools` | `$` | A tool is four things that must line up: schema, handler, server alias, allowlist entry. |

    uv run python -m playground.run basics.check_auth

`check_auth` is a gate, and it will refuse to continue if your session is not
what this repo is written around. That is a cost-attribution rule of the
author's, not a technical requirement — the demo explains the rule when it
refuses and gives you three ways forward, including running anyway.

### What MCP is, in one paragraph

From `basics.tools` onward this repo assumes you know. **MCP (Model Context
Protocol) is a wire protocol for offering tools to a model.** A *server* declares
some tools — each a name, a description and a JSON Schema for its arguments — and
a *client* attaches that server and passes the declarations to the model. When
the model decides to use one, the client sends the call to the server, the server
runs it, and the result comes back into the conversation. That is the whole idea:
a standard shape for "here are some functions, and here is how to call them", so
that a tool written once can be used by any client that speaks it.

The distinction that matters most for these demos is **where the code runs**, and
there are three answers, not two:

- **In-process MCP** (`create_sdk_mcp_server`) — the "server" is just Python
  objects in your own program. No pipes, no second process, no handshake. This is
  what most of the repo uses: `basics.tools`, every `tools_mcp` demo except the
  external one, and the three demos elsewhere that hold a tool —
  `orchestration.triage`, `orchestration.workflow_vs_agent` and
  `reliability.error_taxonomy`.
- **External MCP over stdio** — the server is a separate program the client
  launches and talks to over its stdin and stdout, one JSON message per line.
  Used by `tools_mcp.external_mcp`, with `src/mockserver` as the server.
- **Not MCP at all** — Claude Code's own built-in tools, which you enable through
  `ClaudeAgentOptions(tools=[...])` rather than by attaching a server. Some the
  CLI executes locally; at least one, `WebSearch`, Anthropic executes on its own
  infrastructure. `tools_mcp.where_code_runs` puts this side by side with the
  first case and finds that the SDK reports both identically.

The first two give the model exactly the same thing, and everything that differs
between them — startup cost, crash isolation, language independence, and whether
anything can decline to attach it — follows from that one choice. Section 5 lets
you watch that protocol directly, for free, which is the fastest way to make it
concrete. The third case is not a variant of the other two: nothing you write is
involved, which is the whole point of the demo that examines it.

## 4. The thirteen domain demos

Three domains: three demos, six and three. Some are controlled comparisons that
run the same task two ways and print both columns; `triage` is a worked pipeline,
`context_budget` and `tool_overhead` are instruments, and `external_mcp` is a
documented failure.
Read the domain doc first, then run it, then read the source — in that order,
because the docs pose the question the numbers answer.

**This section is D1, D2 and D5 only, and the omissions are deliberate rather
than oversights.** The five grounding demos are section 3, and they now spread
across four domains rather than sitting in a bucket. D3 is section 6, because
none of it runs through the dispatcher. 5 demos in section 3 plus 13 here is all
18. D4 has no subsection here — none of its demos is a controlled comparison
worth a table — but it does have a document now,
[`docs/d4-prompt-output.md`](docs/d4-prompt-output.md), and four modules in
section 7.

**All D-numbers in this repo are the official blueprint's**, as of the relabel on
2026-08-21. They were not before: two were transposed and one had no counterpart,
so anything written earlier — an old branch, a cached page — uses different
numbers. `docs/domain-map.md` carries the blueprint table, the old-to-new map,
and the honest report of which demos do not fit the domain they landed in.

### D1 — Agentic Architecture and Orchestration · `docs/d1-orchestration.md`

| Run | Free? | What to look for |
|-----|-------|------------------|
| `orchestration.triage` | `$` | **Read this one first.** A three-stage decomposition that works, with the reasoning written at each boundary. Watch which requests never reach the expensive stage, and which stage turned out to be the unreliable one. |
| `orchestration.workflow_vs_agent` | `$` | The same classification as a scripted workflow and as an agent. The workflow column is the **more expensive** one — reproduced across runs at roughly 3.5x the agent's cost, with identical labels. That contradicts the standard advice. Work out why before reading the closing block. |
| `orchestration.subagent` | `$` | The same summarising job inline and delegated, with a delta column. Every delta is positive: you are paying for context isolation on a task with nothing to isolate. |
| `reliability.session_resume` | `$` | The same question in a live session, a resumed session and a fresh one. Steps 2 and 3 run identical code; one string differs. Compare the token counts. Filed under D1 since 2026-08-21 — session state is task statement 1.7, not D5. |
| `reliability.session_fork` | `$` | A baseline forked twice, then the parent re-resumed. Three isolation claims tested separately: what a fork inherits, what it hides from its sibling, and whether it writes back into its parent. A fork gets a new session id; a plain resume does not; every branch turn re-pays the baseline. |

### D2 — Tool Design and MCP Integration · `docs/d2-tools-mcp.md`

| Run | Free? | What to look for |
|-----|-------|------------------|
| `tools_mcp.where_code_runs` | `$` | **Read this one first.** The same question against a tool implemented in this repo and a tool implemented nowhere in it, with every content block's class name printed. One arm really does execute on Anthropic's servers — that is documented, not guessed — and both arms still come back as `ToolUseBlock`. The client/server line the documentation is built on is real; the block stream just does not carry it. The only thing that tells them apart is whether your own handler ran. |
| `tools_mcp.schema_design` | `$` | One tool defined twice, loose and strict, and the arguments the model actually passed. Then look again at *which* keywords produced the difference — it is fewer than you think. |
| `tools_mcp.parallel_tools` | `$` | Two independent lookups against two where the second needs the first's output. A null result on how the calls were grouped, and a hundred-to-one difference on the clock. Read the GAP lines before the groupings. |
| `tools_mcp.tool_overhead` | (free) | What a tools array costs before anything calls it: about 221 tokens per tool, linear, plus what the harness's own toolset costs you unasked. Also the demo where the instrument itself reads a plausible wrong number if you ask it too early. |
| `tools_mcp.permission_gate` | `$` | Priority-1 tickets survive, the rest are deleted, and two refusals land in `permission_denials`. A gate only runs for tools **absent** from `allowed_tools`; listing one there auto-approves it and silences the callback while still reporting `success`. |
| `tools_mcp.external_mcp` | `!` | A refused server attachment, explained rather than crashed. Refusals arrive on stderr, never as an exception, and the server list simply comes back empty. Ships as a `KNOWN_ISSUE` because it could not be completed where this was written; it may well complete for you. |

### D5 — Context Management and Reliability · `docs/d5-reliability.md`

| Run | Free? | What to look for |
|-----|-------|------------------|
| `reliability.context_budget` | `$` | An instrument, not an argument: the resting cost (~12,400 tokens before you type), the threshold, and the headroom. Note that `Free space` and the real headroom are different numbers. It says out loud that compaction did **not** fire and what would be needed to make it. |
| `reliability.error_taxonomy` | `$` | Four failure classes, only one of which is a Python exception. That is why one `try/except` around the agent call is the wrong instinct. |

## 5. The mock MCP server (free)

`src/mockserver` is a real stdio MCP server with fake ticket data — genuine
transport, fabricated records. It runs standalone whether or not a client will
attach it:

    uv run python -m mockserver

[`src/mockserver/README.md`](src/mockserver/README.md) has a four-message
JSON-RPC session you can paste into a shell. Driving it by hand costs nothing and
shows more of the protocol than any agent run does — including the fact that a
raised exception reaches the client as `isError` plus text, with the exception
class gone.

## 6. D3 — Claude Code Configuration · `docs/d3-claude-code.md`

Nothing here runs through the dispatcher; these files configure Claude Code
itself. All of it is free.

1. `.claude/settings.json` — permission allow/deny lists, and the registration of
   both hooks below.
2. `.claude/hooks/block_secret_reads.py` — a `PreToolUse` hook that denies a call
   touching credentials. Test it directly:

       echo '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"cat ~/.claude/.credentials.json"}}' | uv run python .claude/hooks/block_secret_reads.py

   It prints a deny decision. A benign input prints nothing and exits 0.
3. `.claude/hooks/check_turn_cap_guard.py` — a `PostToolUse` hook, and the best
   evidence in this repo that a static check beats careful reading. It parses the
   AST for an agent loop that sets `max_turns` without a `try` around it — the
   bug where hitting the cap yields a result and *then* raises, taking everything
   after the loop with it. That bug was written, found and declared fixed three
   separate times here by someone who had documented it twice. On its first run
   it found **seven** more. Run it over the whole repo:

       uv run python .claude/hooks/check_turn_cap_guard.py

   It exits 0 with a clean report, or 1 listing each defect and the fix. Three
   advisory notes are expected and are not failures — they concern
   `receive_response()`, which is documented not to raise on a cap.
4. `src/playground/CLAUDE.md` — nested memory, and why it deliberately does not
   repeat the root file.
5. `.claude/commands/drill.md` — a custom slash command. In an interactive Claude
   Code session, `/drill d4` quizzes you from these files.

## 7. `examlab` — the layer the Agent SDK owns for you

Same dispatcher, same `--list`, one boundary line in the output:

    uv run python -m playground.run --list
    uv run python -m playground.run examlab.agentic_loop

Everything in section 4 runs through `query()`, which builds the requests, runs
the tool round trip and hands you typed messages. That is the right trade for
building an agent and the wrong one for learning what an agent *is*:
`stop_reason`, `tool_result` blocks, `tool_choice` and `custom_id` have no
`ClaudeAgentOptions` equivalent, and
[`docs/tool-surface.md`](docs/tool-surface.md) counts ten of twenty-four official
tool-use pages as out of reach for that reason. This package is those ten pages,
written as code you can run.

**All eight are free and make no network call by default.** Each one builds real
requests and validates them against the documented contract; the responses are
fabricated by this repo and labelled `SCRIPTED`, a provenance state introduced in
[`src/examlab/CLAUDE.md`](src/examlab/CLAUDE.md) precisely because a scripted
output and a measured one look identical on a console.

| Run | What to look for |
|-----|------------------|
| `agentic_loop` | **Read this one first.** The whole loop in nine lines of control flow. The first scripted response carries prose *and* a tool call in the same turn, which is the detail the next module's wrong loops all trip over. Ends by tripping a circuit breaker on purpose, to show why hitting an iteration cap must raise rather than return. |
| `loop_antipatterns` | The three termination anti-patterns the blueprint names, plus the plumbing bug that causes them, each run against the same script. Two of the four return a confident wrong answer with no error at all. Note *which* two. |
| `chaining` | The same code review as one request, a fixed chain, and a dynamic decomposition, with the request sizes each one actually built. The dynamic arm sends a **larger** request than the single pass — the prose in the file originally claimed otherwise and the numbers won. |
| `tool_choice` | The four modes, the documented per-request token cost of forcing one, and two loops identical but for one line. The one that never terminates is the one whose loop is correct. |
| `tool_errors` | Six failures against a structured tool surface and a generic one, with the recovery policy run over both. The generic column reads `guess` six times, including for a successful empty result. |
| `structured_output` | An extraction that passes the schema, passes the cross-field check, and is wrong about money. Then which layer catches what, and what none of them catch. |
| `validation_retry` | Three documents, all three reported valid by attempt two. The third validated by **inventing** a value the source never contained, after being told not to infer. |
| `batches` | The four properties, and the arithmetic that decides whether the 50% is available to you at all: your submission gap plus the 24-hour bound, against the SLA you promised. |
| `review_criteria` | Three prompts over one labelled answer key. "Be conservative" and "only report high-confidence findings" are already in the worst-scoring prompt. Precision moves 25% to 80% on the categorical list, and one false positive survives all three arms on purpose. |
| `refinement` | Examples against a prose spec on the same transformation, then the round-trip arithmetic for interacting fixes: 5 dependency edges make sequencing cost 9 against 2 batched — and the independent set inverts the recommendation, because reviewability costs more than a round trip. |
| `confidence_routing` | An aggregate accuracy hiding two independent segment failures, and a routing threshold that reviews 30% of the volume while catching none of the errors. |
| `provenance` | The same six findings through a lossy synthesis and a preserving one: 0 of 6 attributable against 5 of 6. Then two numeric disagreements that read identically in prose, one of which is just five years apart. |

**The auth rule is narrowed here, not repealed.** No module requires a
credential, none names a credential variable, and `anthropic` is an optional
extra imported lazily in one function. Going live needs two deliberate acts, not
one — installing a library must not start spending money:

    uv sync --extra live
    PLAYGROUND_EXAMLAB_LIVE=1 uv run python -m playground.run examlab.agentic_loop

Set the flag without the extra, or with it but no credential, and you get the
scripted run **plus a line saying which gate declined**. All four combinations
were exercised on 2026-08-21; the fourth gate exists because the first version of
`live()` did not have it and crashed at request time instead of falling back.

A live run bills a credential this repo does not manage, which is why no number
from one may be written into `docs/status.md`.
[`src/examlab/CLAUDE.md`](src/examlab/CLAUDE.md) states the shape of the
narrowing; `basics/check_auth.py` still refuses to run `playground/` under
anything but an interactive session.

## 8. Close the loop

- [`docs/status.md`](docs/status.md) — **read this one.** It is two things,
  and as of 2026-08-21 every one of its thirty rows was executed on that date
  after its last edit, so for the first time in the project nothing in it is
  asserting output nobody has seen since editing the file.
  First, the run inventory: every demo, whether it has actually been run, and
  what is still unverified, including which files were edited after the run that
  justifies their row. Second, and the reason to open it if you are mapping this
  onto a syllabus, the **coverage map**: a per-domain assessment saying where
  the repo is strong and where it is thin, in its own words — D2 is "thin in the
  worst way: mostly inert", D3 is "one demo, and it produced a null result". Any
  judgement about what this repo covers should come from that table rather than
  from counting demos in section 4.
- [`docs/lessons.md`](docs/lessons.md) — generated from the `LESSON` blocks.
  Regenerate with `uv run python -m playground.lessons` after editing one, and
  check that you did:

      uv run python scripts/check_lessons_fresh.py

  It regenerates into memory and compares. Exit 0 means the page matches its
  source; exit 1 prints the first differing line and points at the fix. It
  exists because that regeneration step was forgotten once and a docs page
  disagreeing with its own source reached a public remote.
- **The seven static checks**, all free, all exit 0 on a clean tree, and each one
  proven to fail on a real defect before it was trusted:

      uv run python scripts/prepublish_check.py         # nothing personal ships
      uv run python scripts/check_status_freshness.py   # rows vs file mtimes
      uv run python scripts/check_caveat_accounting.py  # status.md counts itself
      uv run python scripts/check_lessons_fresh.py      # generated file vs source
      uv run python scripts/check_conventions.py        # line cap, KNOWN ISSUE sync
      uv run python scripts/check_contract_rules.py     # every contract rule fires
      uv run python .claude/hooks/check_turn_cap_guard.py

  Every one of them exists because a rule this repo states in prose was broken
  by the person who wrote the prose. This line said "four" while listing six, so
  it was itself an instance of the class it introduces; the count is now seven.
  Hand-maintained arithmetic still unchecked: the counts in section 2, and the
  bucket totals in `docs/tool-surface.md`, which were wrong in three places until
  2026-08-21. `docs/status.md` says why neither is automated.
- [`docs/tool-surface.md`](docs/tool-surface.md) — every page of the official
  tool-use documentation set, triaged into what this repo demonstrates, what it
  can only observe, and what needs the Messages API and is therefore documented
  and never faked. Read it before concluding that the D4 demos cover tool use:
  ten of twenty-four pages are out of reach here, and it says which and why.
  One of those ten got there by being **demoted** — `web-fetch-tool` was listed
  as reachable until Claude Code's `WebFetch` turned out not to be the server
  tool of that name. A reference page that only ever gains coverage is one
  nobody is checking.
- [`docs/traps.md`](docs/traps.md) — anti-patterns the demos show on purpose,
  plus the environment traps found while building this, each with its evidence.
- [`docs/domain-map.md`](docs/domain-map.md) — the official blueprint with its
  weightings, the old-to-new label map for anything written before 2026-08-21,
  and **the part to read if you are studying**: which demos land in a domain the
  exam does not test there, and which task statements have no coverage in this
  repo at all. Two of them are large and in a 20% domain.

## Things that may differ where you run this

None of these are properties of the SDK. Each one is something that was true
where this repo was written, and each tells you how to check your own case.

- **`.claude/settings.json` may not be in effect.** Whether its entries apply
  depends on conditions outside the file, and the only signal is a line on
  stderr. Throughout the writing of this repo they were reported as ignored.
  Run once with stderr visible and read what it says before trusting a rule
  there.
- **An external MCP server may not attach.** `external_mcp.py` could not attach
  one where this was written, so it ships as a `KNOWN_ISSUE`: it prints what did
  not work and stops rather than faking a result. Everything below that point in
  the file has therefore never been executed by the author. Notably, being a
  purely local Python process was no protection — so if this affects you, do not
  expect locality to be the fix. Run it and see; if it works for you, you are
  ahead of the repo. In-process tools are a different mechanism and are
  unaffected either way, which is why `permission_gate.py` uses one.
- **Console encoding.** On a Windows console using a legacy code page, model
  output containing `×` or an em-dash renders as `?`. The demo is fine; the
  terminal is not. `chcp 65001` or a UTF-8 terminal fixes it.

## Conventions

Every **demo** module carries two things, and they are deliberately not the same
thing. The `LESSON` dict at the top is reader-facing: setup, run, cost, expect,
learn. The docstring below it is practitioner-facing:
`WHAT / WHY / DOMAIN / TRADEOFF / ALTERNATIVE`. The TRADEOFF line is the part
worth arguing with — several were wrong until the demos were actually run, and
were rewritten to match the measurement rather than the other way round.

Modules that are not demos carry the docstring and no `LESSON`, because a
`LESSON` promises something you can run and see. `playground/teach.py`,
`playground/lessons.py` and `tools_mcp/instruments.py` are in that category.
`instruments.py` is worth opening anyway: it holds the three measuring helpers
the D4 demos share, and each one documents what it does **not** answer, which is
the part that mattered. All three exist because the obvious version of the
measurement returned a confident wrong answer first.

Every claim about Claude's behaviour states its evidential standing in place:
**DOCUMENTED** (official docs, with URL and fetch date), **MEASURED** (run here,
with the output), or **INFERRED** (neither — a guess, however reasonable). Where
documentation and measurement disagree, the file says so and leaves the conflict
standing rather than picking the tidier side. An earlier version of this repo
used a `[VERIFY]` marker and a central register of open questions; both were
development scaffolding and have been retired, with everything a reader needs
moved next to the code it concerns or into [`docs/traps.md`](docs/traps.md).

Those labels are meant to move. An `INFERRED` guess about what Claude Code's
`WebSearch` actually is was later settled from documentation and turned out to be
**wrong**; the file that depended on it now carries the correction and the
citation, and `docs/tool-surface.md` records what the guess had been. A repo
where no label ever changes is one where nobody went back and checked.

## Licence

MIT — see [`LICENSE`](LICENSE). Use it, fork it, argue with it. The measurements
in `docs/status.md` were taken on one machine on one date against the pinned
`uv.lock`; if yours disagree, yours are the current ones.
