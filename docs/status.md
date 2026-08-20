# Status

What has actually been observed, and what has not. Two states only:

- **RAN CLEAN** — executed, dated, with one line of what it printed.
- **KNOWN ISSUE** — did not complete; the `KNOWN_ISSUE` block prints at runtime
  *and* the same paragraph sits as a comment on the failing line.

Anything that is neither is listed under "Unaccounted for", which is the section
this file exists to keep honest.

Absolute currency figures are deliberately absent here and everywhere else in the
repo. Ratios reproduce across runs and price changes; absolute numbers do not,
and a stale one reads as authoritative.

## Demos

| Demo | State | Date | What it printed |
|------|-------|------|-----------------|
| `basics.check_auth` | RAN CLEAN | 2026-08-20 | Two fields — `authMethod` and `apiProvider` — then confirmation that the session matches the repo's assumption. |
| `basics.hello` | RAN CLEAN | 2026-08-20 (see caveat) | One sentence in 1 TextBlock, `[success] 1 turn(s)`, session id, and the usage split showing uncached input dwarfed by cache reads. |
| `basics.prompt_shape` | RAN CLEAN | 2026-08-20 | **Twice.** Both runs: two correct summaries, and `A resisted / B resisted` — the injected word got through neither construction. A null result, reported as one. |
| `basics.structured` | RAN CLEAN | 2026-08-20 (see caveat) | A 9-key validated JSON object, `success`, 3 turns against a cap of 2. |
| `basics.tools` | RAN CLEAN | 2026-08-20 | `(17 + 8) x 4 = 100`, two tool calls captured (`add` then `multiply`), `[success] 4 turns`. |
| `orchestration.triage` | RAN CLEAN | 2026-08-20 (see caveat) | **Twice, identical routing.** 1 request rejected by stage 1 for zero model calls, 1 settled by stage 2, 2 escalated; 5 model calls against a possible 8. One stage-3 call on the second run declined its tool — see below. |
| `orchestration.workflow_vs_agent` | RAN CLEAN | 2026-08-20 (see caveat) | Identical labels both ways; the workflow cost roughly 3.5x the agent over 3 API calls against 1. |
| `orchestration.subagent` | RAN CLEAN | 2026-08-20 (see caveat) | A four-column table with every delta positive: delegation cost more on turns, latency, output tokens and price. |
| `tools_mcp.where_code_runs` | RAN CLEAN | 2026-08-20 (see caveat) | **Twice.** Both arms answered; the census showed `ToolUseBlock(mcp__rel__lookup_release)` against `ToolUseBlock(WebSearch)` — the same class — and `ServerToolUseBlock` appeared 0 times. Our handler ran in one arm and not the other. |
| `tools_mcp.schema_design` | RAN CLEAN | 2026-08-20 (see caveat) | Weak schema returned one unparsed string; strong schema returned `sensor`/`celsius`/`time_hhmm` as typed fields. |
| `tools_mcp.parallel_tools` | RAN CLEAN | 2026-08-20 (see caveat) | Both arms `[1, 1]` in 3 turns — a null result on grouping. The gaps differed: 15 ms idle between the independent pair, 1,285 ms between the dependent pair. |
| `tools_mcp.tool_overhead` | RAN CLEAN | 2026-08-20 | Six toolsets read before any prompt. 221 tokens per tool plus 5 fixed, predicting every row to the token; `claude_code` built-ins +11,261; every MCP row read 1,316 on connect and needed 2–3 polls to settle. |
| `tools_mcp.external_mcp` | **KNOWN ISSUE** | 2026-08-20 | A refusal notice scraped from stderr, then the KNOWN ISSUE block, then exit without an agent run. |
| `tools_mcp.permission_gate` | RAN CLEAN | 2026-08-20 (see caveat) | Priority-1 tickets survived, the rest were deleted, 2 entries in `permission_denials`, `success` in 6 turns against a cap of 3. |
| `reliability.session_resume` | RAN CLEAN | 2026-08-20 (see caveat) | Step 1 recalled the fact, step 2 recalled it from the session id at a higher token count, step 3 did not know it. |
| `reliability.error_taxonomy` | RAN CLEAN | 2026-08-20 (see caveat) | `'retry' -> ENVIRONMENT`, `'retry' -> ARGUMENTS`, "2 distinct buckets: the taxonomy discriminates." |
| `reliability.context_budget` | RAN CLEAN | 2026-08-20 (see caveat) | Resting cost ~12,400 tokens of 200,000, one exchange +2,452, threshold 167,000, headroom 152,141, and "compaction did not run". |

### The caveat, stated once

**Twelve rows are marked "see caveat", and here they all are:**

`basics.hello`, `basics.structured`, `orchestration.triage`,
`orchestration.workflow_vs_agent`, `orchestration.subagent`,
`tools_mcp.where_code_runs`, `tools_mcp.schema_design`,
`tools_mcp.parallel_tools`, `tools_mcp.permission_gate`,
`reliability.session_resume`, `reliability.error_taxonomy`,
`reliability.context_budget`.

Their **behaviour** was measured with a model, on the date shown. Their **current
file version** has since been edited — every demo gained a `LESSON` and closing
block, seven gained a `try` around a capped `query()` loop, and three later
gained docstring material moved out of a retired open-questions register. Those
edits have been verified only by driving the real `main()` with a stubbed SDK,
for zero tokens. That catches a missing key, a bad index or a format bug. It
cannot catch behavioural drift, and it is not evidence about Claude.

That is a weaker claim than the other rows and is written down rather than
smoothed over. The fix is one run each, next time there is budget.

**Two of those twelve carry a stronger version of the caveat and are named
separately, because "edited after the run" understates what happened to them.**
`tools_mcp.where_code_runs` and `tools_mcp.parallel_tools` were both rewritten
*because of* what their first run showed, and the budget was gone before the
rewrite could be run. `where_code_runs` was re-run once after its first rewrite
and then trimmed again; `parallel_tools` was rewritten once and never re-run at
all, so **no model call has ever been made by the version of that file now on
disk**. Both were replayed against a stubbed SDK at the measured timings, which
proves the arithmetic and the formatting and proves nothing about Claude. The
numbers quoted in their rows above are real and were observed; the code that
would print them again has not printed them.

An earlier version of this section said "six rows" while seven were marked and
five were named. It was found by review, not by the author, which is why
`scripts/check_status_freshness.py` now exists: it compares each row's recorded
run date against the file's modification time and fails when a file is newer than
the measurement that justifies its row. Prose accounting of this kind had been
got wrong four times before it was automated.

**The five rows with no caveat**, for completeness: `basics.check_auth` (re-run
after its rewrite, and it makes no model call so re-running costs nothing),
`basics.prompt_shape` (its last edit landed between its two runs, so the current
text is what ran), `basics.tools`, `tools_mcp.tool_overhead`, and
`tools_mcp.external_mcp`, which is a KNOWN ISSUE rather than a measurement.

`tools_mcp.tool_overhead` is the one row here that is unambiguous, and it is
worth saying why: it makes **no model call at all**, so the version on disk was
simply re-run after its last edit at no cost. Every other row in this table is
an argument about whether an edit mattered. This one is not, and that is a
property of the demo rather than of anyone's diligence.

The other four have since been edited too, and `check_status_freshness.py` names
them. The edit was the same in each case: the `run` line in the `LESSON` block
gained a `uv run` prefix, and `basics.tools` also gained a docstring paragraph.
That changes what the banner prints, not what the demo does, and none of it
touches the output these rows describe — so they are not marked. That judgement
is recorded here rather than left implicit, because it is exactly the kind of
call that was got wrong four times when it lived only in someone's head.

**A limit of the check worth knowing.** `status.md` records a date and the
filesystem records a timestamp, so an edit made on the same day as the run it
invalidates cannot be ordered against it. Every row is currently in that state.
The script reports them as INDETERMINATE rather than clean — its first version
called them fresh, which would have been a fifth instance of the defect it was
written to catch.

### The one result worth reading twice

`orchestration.triage` ran twice with identical routing, and on the second run
one stage-3 call **declined to use its tool**, replying that the lookup required
authentication and should be authorised in an interactive session. The tool is
in-process: there is no server and no authentication. The same thing had already
happened once in an unrelated demo. It is written up at the line where it bit, in
`orchestration/triage.py`'s STAGE 3 NOTE, and as a trap in `traps.md`. It is the
most operationally dangerous behaviour recorded in this repo, because it arrives
as an ordinary successful turn containing a fluent, plausible, wrong explanation.
Nothing in `subtype`, `is_error` or `permission_denials` marks it.

## Unaccounted for

Neither RAN CLEAN nor covered by a declared KNOWN_ISSUE. These are gaps.

| Thing | Why it is unaccounted for | What it would take |
|-------|---------------------------|--------------------|
| The agent-run branch of `external_mcp.py` (~40 lines below the refusal check) | Never executed by the author. Its `LESSON` says INFERRED and a comment marks the boundary, but that is a label on unrun code. | An environment where the server attaches, then one run. It may already work for you. |
| `src/mockserver`'s five tools *through a model* | Hand-driven over stdio and verified message by message, twice, byte-identical. No model has ever called them over the transport. | As above. The in-process copies in `permission_gate.py`, `error_taxonomy.py` and `triage.py` are the closest substitute and are genuinely exercised. |
| `.claude/hooks/block_secret_reads.py` inside a live session | Directly tested, 7/7 cases, including the encoding bug that made it fail open. It has never fired during an actual tool call. | An environment where the settings file is in effect, then an attempted blocked read. |
| `.claude/hooks/check_turn_cap_guard.py` inside a live session | Both modes tested directly: standalone over the repo, and hook mode against a known-bad and a known-good file, exiting 2 and 0. Never fired via a real `PostToolUse` event. | Same as above. |
| `.claude/settings.json` | Its entries were reported as ignored on every run while this repo was written, so neither the permission rules nor the hook registrations have been observed taking effect. | Determine why they are ignored in your setup and correct it; the file itself is valid. |
| `$CLAUDE_PROJECT_DIR` expansion on Windows | Open question 3. Both hooks are registered using it and have only been tested by direct invocation. | Resolves itself the first time a hook fires in-session. |
| Compaction itself | `context_budget.py` measures the distance to the threshold and says outright that it never crosses it. | A deliberately long session or one very large tool result. Real quota, which is why it was not done. |
| Nine of the twenty-four official tool-use documentation pages | They configure behaviour through Messages API request fields or tool-definition properties — `strict`, `tool_choice`, `defer_loading`, `allowed_callers`, `eager_input_streaming`, `cache_control`, `input_examples` — none of which the Agent SDK exposes. Reaching them needs an API key, which the auth rule forbids. | Nothing, deliberately. They are documented page by page in `tool-surface.md` with the reason each is out of reach. Listed here so the coverage table is not read as completeness. |
| `pause_turn`, and a turn mixing a server tool with a client tool | Both are handled inside the harness. No `ServerToolUseBlock` has ever been observed here at all — see finding 1 in `tool-surface.md`. | Server tools, therefore the Messages API. |

## Coverage

The domain labels below are the author's and are **not verified against any
official source** — see `domain-map.md`, which records the attempt and why it
failed.

| Domain | Demos | Honest assessment |
|--------|-------|-------------------|
| **D0 Foundations** | `check_auth`, `hello`, `structured`, `tools` | Solid, and the label is the weakest in the repo — it is a bucket, not a domain. Missing: streaming input and interrupts. |
| **D1 Orchestration** | `triage`, `workflow_vs_agent`, `subagent` | **Materially improved this round.** It now opens with a decomposition that works and treats the two cost comparisons as refinements, rather than being three arguments against defaults with nothing to anchor them. Still missing: parallel fan-out, and any agent that plans then revises. |
| **D2 Claude Code Config** | `settings.json`, two hooks, `drill.md`, both `CLAUDE.md` files, `run.py`/`teach.py`/`lessons.py`/`prepublish_check.py` | **Thin in the worst way: mostly inert.** The settings file has never been observed taking effect, neither hook has fired in a session, and the slash command has never been invoked. The memory-hierarchy material is genuinely good and documented against official sources. Everything else is configuration nobody has watched work. |
| **D3 Prompt Engineering** | `prompt_shape` | **One demo, and it produced a null result.** That is honest but thin. Nothing on instruction placement, few-shot examples, or system-versus-user-turn — each of which was considered and rejected for this round because none produces an objectively checkable outcome as cleanly. |
| **D4 Tools and MCP** | `tools`, `where_code_runs`, `schema_design`, `parallel_tools`, `tool_overhead`, `external_mcp`, `permission_gate`, `src/mockserver` | **Materially deeper this round.** It now covers where a tool executes, what a tool costs before anyone calls it, and how calls arrive — against the official tool-use documentation set, triaged page by page in `tool-surface.md`. Two holes stay named: the external half ships as a documented failure, and nine of the twenty-four documentation pages are API-ONLY and demonstrated nowhere, deliberately. |
| **D5 Reliability** | `context_budget`, `session_resume`, `error_taxonomy` | Good depth on failure classification and context accounting. Two gaps: compaction is never triggered, and there is no demonstration of retry or backoff as a *policy* — the repo classifies failures without showing what reacts to them. |

## Reader path

Six stuck points were identified in the previous audit. Re-walked from a clean
clone's perspective:

| # | Previous finding | Now |
|---|-----------------|-----|
| 1 | `uv run python`, not bare `python` | **Fixed.** The README says so in the install section, and `--list` prints the correct form in its footer. |
| 2 | `check_auth` fails for most readers with no way forward | **Fixed.** It explains the rule, why it exists, and gives three named options including `PLAYGROUND_ALLOW_ANY_AUTH=1` to proceed knowingly. |
| 3 | Machine-specific limitations read as universal | **Fixed.** Rewritten as "Things that may differ where you run this", each with how to check. `external_mcp`'s KNOWN_ISSUE says what did not work and how to test your own case, not what caused it. |
| 4 | Nothing explains what MCP is | **Fixed.** A short section in the README, placed before the first demo that assumes it, covering the protocol and the in-process/external split. |
| 5 | `.claude/` material cannot be exercised by following the README | **Partly.** There are now two hooks and both can be run directly from the README, so more of it is testable — but the settings file and the slash command still cannot be exercised without a working interactive session. |
| 6 | Console encoding renders some characters as `?` | **Documented, not fixed.** Named as a terminal issue with the `chcp 65001` workaround. |

**Four fixed, one partly, one documented — so five remain in some form, of which
only two (5 and 6) can still block or confuse a reader, and neither is fatal.**

One new stuck point was introduced and should be named rather than discovered:
`docs/domain-map.md` tells the reader the domain labels are unverified. A reader
mapping this repo onto a syllabus will find no authoritative map here. That is
the correct state — the alternative was inventing one — but it is a gap where
previously there was an unexamined assumption.
