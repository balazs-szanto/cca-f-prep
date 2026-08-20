# Claude Agent SDK Playground

A lab manual. Seventeen small demos, each isolating one architectural decision and
printing what it costs. Every demo tells you on screen what to set up, what to
run, what you should see, and what it proves — so the console teaches as much as
the docs do.

This repo describes what each demo demonstrates. It does not claim what any exam
covers; mapping the demos onto a syllabus is your job, and doing that mapping is
most of the value.

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

**You can do a large part of this repo for nothing.** Free right now:

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

That leaves fourteen `$` demos, which together cost a few cents against your
subscription quota. They pin `claude-haiku-4-5` and cap `max_turns`, and each one
names its own cost in its banner before it runs. If these counts ever disagree
with `--list`, believe `--list`: it derives them from each module's `LESSON`
block, and this paragraph is maintained by hand.

## 3. Ground yourself

Run these five in order. They are the whole SDK in miniature.

| # | Run | Free? | What it teaches |
|---|-----|-------|-----------------|
| 1 | `basics.check_auth` | free | Which credential is paying, and why your code cannot control that — only refuse. |
| 2 | `basics.hello` | `$` | `query()` is an async generator over typed messages. The run *is* the loop, and `ResultMessage` is the only place its numbers exist. |
| 3 | `basics.prompt_shape` | `$` | What is instruction and what is data is a convention you construct. Also a worked null result — the comparison came out flat, twice, and says so. |
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

The only distinction that matters for these demos is **where the server runs**:

- **In-process** (`create_sdk_mcp_server`) — the "server" is just Python objects
  in your own program. No pipes, no second process, no handshake. Used by
  `basics.tools` and `tools_mcp.permission_gate`.
- **External over stdio** — the server is a separate program the client launches
  and talks to over its stdin and stdout, one JSON message per line. Used by
  `tools_mcp.external_mcp`, with `src/mockserver` as the server.

Both give the model exactly the same thing. Everything that differs — startup
cost, crash isolation, language independence, and whether anything can decline to
attach it — follows from that one choice. Section 5 lets you watch the protocol
directly, for free, which is the fastest way to make this concrete.

## 4. The twelve domain demos

Three domains: three demos, six and three. Some are controlled comparisons that
run the same task two ways and print both columns; `triage` is a worked pipeline,
`context_budget` and `tool_overhead` are instruments, and `external_mcp` is a
documented failure.
Read the domain doc first, then run it, then read the source — in that order,
because the docs pose the question the numbers answer.

### D1 — Agentic Architecture and Orchestration · `docs/d1-orchestration.md`

| Run | Free? | What to look for |
|-----|-------|------------------|
| `orchestration.triage` | `$` | **Read this one first.** A three-stage decomposition that works, with the reasoning written at each boundary. Watch which requests never reach the expensive stage, and which stage turned out to be the unreliable one. |
| `orchestration.workflow_vs_agent` | `$` | The same classification as a scripted workflow and as an agent. The workflow column is the **more expensive** one — reproduced across runs at roughly 3.5x the agent's cost, with identical labels. That contradicts the standard advice. Work out why before reading the closing block. |
| `orchestration.subagent` | `$` | The same summarising job inline and delegated, with a delta column. Every delta is positive: you are paying for context isolation on a task with nothing to isolate. |

### D4 — Tool Design and MCP Integration · `docs/d4-tools-mcp.md`

| Run | Free? | What to look for |
|-----|-------|------------------|
| `tools_mcp.where_code_runs` | `$` | **Read this one first.** The same question against a tool implemented in this repo and a tool implemented nowhere in it, with every content block's class name printed. Both come back as `ToolUseBlock`: the client/server line the documentation is built on is not visible from here. |
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
| `reliability.session_resume` | `$` | The same question in a live session, a resumed session and a fresh one. Steps 2 and 3 run identical code; one string differs. Compare the token counts. |

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

## 6. D2 — Claude Code Configuration · `docs/d2-claude-code.md`

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

## 7. Close the loop

- [`docs/status.md`](docs/status.md) — **read this one.** Every demo, whether it
  has actually been run, and what is still unverified. It is the honest inventory
  of what this repo has and has not observed.
- [`docs/lessons.md`](docs/lessons.md) — generated from the `LESSON` blocks.
  Regenerate with `uv run python -m playground.lessons` after editing one.
- [`docs/tool-surface.md`](docs/tool-surface.md) — every page of the official
  tool-use documentation set, triaged into what this repo demonstrates, what it
  can only observe, and what needs the Messages API and is therefore documented
  and never faked. Read it before concluding that the D4 demos cover tool use:
  nine of twenty-four pages are out of reach here, and it says which and why.
- [`docs/traps.md`](docs/traps.md) — anti-patterns the demos show on purpose,
  plus the environment traps found while building this, each with its evidence.
- [`docs/domain-map.md`](docs/domain-map.md) — how this repo labels its own
  domains, and why those labels are **not** verified against any official source.
  Read it before mapping any of this onto a syllabus.

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

Every module carries two things, and they are deliberately not the same thing.
The `LESSON` dict at the top is reader-facing: setup, run, cost, expect, learn.
The docstring below it is practitioner-facing:
`WHAT / WHY / DOMAIN / TRADEOFF / ALTERNATIVE`. The TRADEOFF line is the part
worth arguing with — several were wrong until the demos were actually run, and
were rewritten to match the measurement rather than the other way round.

Every claim about Claude's behaviour states its evidential standing in place:
**DOCUMENTED** (official docs, with URL and fetch date), **MEASURED** (run here,
with the output), or **INFERRED** (neither — a guess, however reasonable). Where
documentation and measurement disagree, the file says so and leaves the conflict
standing rather than picking the tidier side. An earlier version of this repo
used a `[VERIFY]` marker and a central register of open questions; both were
development scaffolding and have been retired, with everything a reader needs
moved next to the code it concerns or into [`docs/traps.md`](docs/traps.md).
