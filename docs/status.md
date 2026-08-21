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

**Domain labels throughout this file are the official CCA-F blueprint's**, as of
the relabel of 2026-08-21. See `domain-map.md` for the blueprint table, the
old-to-new map, and which demos land in a domain the exam does not test there.

## Demos

| Demo | State | Date | What it printed |
|------|-------|------|-----------------|
| `basics.check_auth` | RAN CLEAN | 2026-08-21 | `authMethod: claude.ai`, `apiProvider: firstParty`, then "Session matches this repo's assumption." |
| `basics.hello` | RAN CLEAN | 2026-08-20 (see caveat) | One sentence in 1 TextBlock, `[success] 1 turn(s)`, session id, and the usage split showing uncached input dwarfed by cache reads. |
| `basics.prompt_shape` | RAN CLEAN | 2026-08-20 (see caveat) | **Twice.** Both runs: two correct summaries, and `A resisted / B resisted` — the injected word got through neither construction. A null result, reported as one. |
| `basics.structured` | RAN CLEAN | 2026-08-20 (see caveat) | A 9-key validated JSON object, `success`, 3 turns against a cap of 2. |
| `basics.tools` | RAN CLEAN | 2026-08-20 (see caveat) | `(17 + 8) x 4 = 100`, two tool calls captured (`add` then `multiply`), `[success] 4 turns`. |
| `orchestration.triage` | RAN CLEAN | 2026-08-20 (see caveat) | **Twice, identical routing.** 1 request rejected by stage 1 for zero model calls, 1 settled by stage 2, 2 escalated; 5 model calls against a possible 8. One stage-3 call on the second run declined its tool — see below. |
| `orchestration.workflow_vs_agent` | RAN CLEAN | 2026-08-20 (see caveat) | Identical labels both ways; the workflow cost roughly 3.5x the agent over 3 API calls against 1. |
| `orchestration.subagent` | RAN CLEAN | 2026-08-20 (see caveat) | A four-column table with every delta positive: delegation cost more on turns, latency, output tokens and price. |
| `tools_mcp.where_code_runs` | RAN CLEAN | 2026-08-20 (see caveat) | **Twice.** Both arms answered; the census showed `ToolUseBlock(mcp__rel__lookup_release)` against `ToolUseBlock(WebSearch)` — the same class — and `ServerToolUseBlock` appeared 0 times. Our handler ran in one arm and not the other. |
| `tools_mcp.schema_design` | RAN CLEAN | 2026-08-20 (see caveat) | Weak schema returned one unparsed string; strong schema returned `sensor`/`celsius`/`time_hhmm` as typed fields. |
| `tools_mcp.parallel_tools` | RAN CLEAN | 2026-08-20 (see caveat) | Both arms `[1, 1]` in 3 turns — a null result on grouping. The gaps differed: 15 ms idle between the independent pair, 1,285 ms between the dependent pair. |
| `tools_mcp.tool_overhead` | RAN CLEAN | 2026-08-21 | Re-run after the relabel, and **the built-in figure moved** — see below. 221 tokens per tool plus 5 fixed, predicting every unfitted row to 0 tokens' error; `claude_code` built-ins now rest at 16,579, **+14,146** against a no-tools session; every MCP row still needed 2–3 polls to settle. |
| `tools_mcp.external_mcp` | **KNOWN ISSUE** | 2026-08-21 | A refusal notice scraped from stderr, then the KNOWN ISSUE block, then exit without an agent run. Re-run after the relabel; the refusal is unchanged. |
| `tools_mcp.permission_gate` | RAN CLEAN | 2026-08-20 (see caveat) | Priority-1 tickets survived, the rest were deleted, 2 entries in `permission_denials`, `success` in 6 turns against a cap of 3. |
| `reliability.session_resume` | RAN CLEAN | 2026-08-20 (see caveat) | Step 1 recalled the fact, step 2 recalled it from the session id at a higher token count, step 3 did not know it. |
| `reliability.error_taxonomy` | RAN CLEAN | 2026-08-20 (see caveat) | `'retry' -> ENVIRONMENT`, `'retry' -> ARGUMENTS`, "2 distinct buckets: the taxonomy discriminates." |
| `reliability.context_budget` | RAN CLEAN | 2026-08-20 (see caveat) | Resting cost ~12,400 tokens of 200,000, one exchange +2,452, threshold 167,000, headroom 152,141, and "compaction did not run". |
| `examlab.agentic_loop` | RAN CLEAN | 2026-08-21 | Three exchanges — two `tool_use`, one `end_turn` — 6 messages in history, then the seven-row `stop_reason` table and `LoopBudgetExceeded` after 2 forced iterations. |
| `examlab.loop_antipatterns` | RAN CLEAN | 2026-08-21 | Four diagnoses. Two returned silently: the narration after 1 request, and an empty string after 2. Two raised `TransportError`: script exhaustion at request 4, and a rule 4 role violation at request 1. |
| `examlab.chaining` | RAN CLEAN | 2026-08-21 | 1 / 4 / 3 requests and largest prompts of 468 / 378 / 549 characters. The dynamic arm's largest request **exceeds** the single pass, which the file's first draft claimed the opposite of. |
| `examlab.tool_choice` | RAN CLEAN | 2026-08-21 | The four modes, the documented forcing overhead, then 6 iterations with no terminal `stop_reason` while the choice was forced, against 2 requests once it was dropped. |
| `examlab.tool_errors` | RAN CLEAN | 2026-08-21 | Six cases. The structured surface produced retry, fix-and-re-call, escalate, escalate, fix-and-re-call, report; the generic surface produced `guess` six times. |
| `examlab.structured_output` | RAN CLEAN | 2026-08-21 | Three extractions: one clean, one passing schema and cross-field checks while disagreeing with its source, one caught only by the `currency_detail` cross-field rule. |
| `examlab.validation_retry` | RAN CLEAN | 2026-08-21 | All three reported valid by attempt 2 — the third by returning `currency_detail='CHF'`, which appears nowhere in its source and passed every check. |
| `examlab.batches` | RAN CLEAN | 2026-08-21 | 5 resubmission requests from 3 failures, and a cadence table where an 8-hour window misses a 30-hour SLA by 2 hours and a 6-hour window meets it with zero margin. |

### What "RAN CLEAN" means for the `examlab` rows, which is less than it looks

Those eight rows are true and narrow. The code ran and printed what the row says.
What it consumed was a **fabricated response script**, labelled `SCRIPTED` in
place — a fourth provenance state introduced in `src/examlab/CLAUDE.md` alongside
DOCUMENTED, MEASURED and INFERRED.

So each row is evidence about a control flow and about nothing else. That
`loop_antipatterns` returns an empty string after two requests is a fact about
that loop. It is **not** a fact about how often a model emits a bare `tool_use`
turn, and no row above should be read that way. The distinction matters because a
scripted run and a live one are indistinguishable on a console, which is why the
label is printed by the banner on every run rather than left to this page.

They carry no caveat for a different reason from the rest of the table: there is
no model behaviour behind them to drift, and re-running them costs nothing. Every
one was executed after its last edit.

### The caveat, stated once

**Fourteen rows are marked "see caveat", and here they all are:**

`basics.hello`, `basics.prompt_shape`, `basics.structured`, `basics.tools`,
`orchestration.triage`, `orchestration.workflow_vs_agent`,
`orchestration.subagent`, `tools_mcp.where_code_runs`,
`tools_mcp.schema_design`, `tools_mcp.parallel_tools`,
`tools_mcp.permission_gate`, `reliability.session_resume`,
`reliability.error_taxonomy`, `reliability.context_budget`.

**Twelve of the fourteen carry the original version of the caveat.** Their
*behaviour* was measured with a model, on the date shown. Their *current file
version* has since been edited — every demo gained a `LESSON` and closing block,
seven gained a `try` around a capped `query()` loop, three gained docstring
material moved out of a retired open-questions register, and all of them were
touched again by the relabel. Those edits have been verified only by driving the
real `main()` with a stubbed SDK, for zero tokens. That catches a missing key, a
bad index or a format bug. It cannot catch behavioural drift, and it is not
evidence about Claude. The fix is one run each, next time there is budget.

**Two rows were added to this list by the relabel, and the judgement that used to
keep them off it is now overruled.** The two are named in the list above; before
2026-08-21 they were uncaveated on an explicit argument recorded here, that their
only edits changed what the banner printed rather than what the demo did. The
relabel is the same kind of edit — a `DOMAIN` line and a `domain` field, which no
demo reads at runtime — and this time `check_status_freshness.py` proves the file
is newer than the measurement, where before the two shared a date and the
ordering was undecidable. The check does not model "this edit cannot matter",
deliberately: its own ALTERNATIVE section rejects hashing the behavioural parts,
because deciding what counts as behavioural is the judgement being automated
away. So the precedent yields to the check. Marking a row that probably did not
need it is the cheap error; the other one is not.

**Two of the fourteen carry a stronger version still, and are named separately,
because "edited after the run" understates what happened to them.**
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

`scripts/check_caveat_accounting.py` is the one that guards this section
directly. It checks that the stated counts match the `(see caveat)` markers in
the table, that the named demos are exactly the marked ones in both directions,
and that every demo with a row is registered in `run.py`. It was proven against
four fixtures reproducing real defect shapes, including the historical one where
the prose said six, the table marked seven and the list named five. It also
failed on its own first contact with this file — a filename has the same
`word.word` shape as a demo name, so it read the name of another script out of a
paragraph and reported it as a demo. That bug is fixed and written up in the
script, because a check that has only been seen passing has not been tested.

`scripts/check_conventions.py` covers two more rules that were being enforced by
memory: no Python file over the cap **declared in `CLAUDE.md`** rather than
hardcoded, and every `KNOWN ISSUE` comment block matching the constant the
runner prints. That duplication is mandated by the convention, and mandated
duplication with no sync check is how two copies of a paragraph end up
disagreeing about what went wrong.

**One item is deliberately left unchecked: the counts in the README.** They are
hand-maintained, the README says so in section 2, and that sentence is at least
honest. Deriving them would mean parsing prose for numbers written as words in
running text, which is a different and worse problem than the four checks above
solve — each of those reads a table, an AST or a generator's own output. The
counts were stale twice in one round and were caught by hand both times. A second
instance of the same gap surfaced on 2026-08-21: `tool-surface.md` states its own
bucket counts three times, all three were wrong, and no script reads that page.

`scripts/check_lessons_fresh.py` is the third such script and was written for the
same reason as the other two. `docs/lessons.md` is generated from every demo's
`LESSON` block, and regenerating it is a step a person has to remember. On
2026-08-20 that step was missed: restored prose in one `LESSON` never reached the
generated page, and a commit carrying a docs file that disagreed with its own
source was pushed to a public remote. It was found when an unrelated command
happened to run the generator, which is not a control. The script regenerates
into memory and compares, so the drift now fails loudly instead of waiting to be
noticed.

**The eleven rows with no caveat**, for completeness: `basics.check_auth`,
`tools_mcp.tool_overhead` and `tools_mcp.external_mcp`, all three re-run on
2026-08-21 after the relabel because all three are free; and the eight
`examlab.agentic_loop`, `examlab.loop_antipatterns`, `examlab.chaining`,
`examlab.tool_choice`, `examlab.tool_errors`, `examlab.structured_output`,
`examlab.validation_retry` and `examlab.batches`, for the reason given two
sections above.

**The one number that changed on re-running, and it is not a small one.** The
`tool_overhead` row previously recorded the `claude_code` built-in toolset at
roughly 11,000 tokens above a no-tools session. Re-run on 2026-08-21 it read
16,579 total and **+14,146** above baseline — about a quarter more, on the same
machine, against the same pinned `uv.lock`, and its breakdown now names a
`Skills` category the earlier run's did not. Nothing in this repo changed to
cause that; the harness did. The per-tool figure held exactly, at 221 plus 5
fixed, predicting every unfitted row to the token.

That is worth more than the number. **A cost that is a property of the harness
rather than of your code can move under you between two runs a day apart**, and
the two halves of that demo behaved completely differently: the part measuring
*your* tools was stable to the token, and the part measuring *the platform's* was
not. Any budget built on the second figure needs re-measuring, not citing.
`tool-surface.md` finding 2 carried the old number and has been corrected.

**Two defects found by running paths rather than reading them, both on
2026-08-21, both in code written the same day.**

The first was in `examlab/contract.py`. Its validator has four rules and is the
whole basis for the claim that the scripted transport *grades* a loop rather than
replaying at it — and only **rule 4** had ever fired in any run. Rules 1, 2 and 3
had never executed at all, so three quarters of the thing doing the grading was
unexercised. `scripts/check_contract_rules.py` now proves each rule fires on a
fixture built to break that rule and no other, and it was proven in turn against
a deliberately disabled rule 3, which it reported.

The second was in `examlab/transport.py`, and it broke a promise this repo makes
in three places. `live()` assumed `anthropic.Anthropic()` would raise without a
credential, so that a reader who installed the optional extra without one would
fall back to the scripted transport. **MEASURED against anthropic 1.0.0: it does
not raise.** It constructs cleanly, `live()` returned a `LiveTransport`, the
banner announced a live run, and the demo died at request time — a traceback
exactly where the documentation promised a working scripted fallback. It was
found by installing the extra and running a demo, which took one command and had
not been done.

The fix added a fourth gate (does the client actually hold a credential?) and a
first one (`PLAYGROUND_EXAMLAB_LIVE=1`), so that installing a library cannot
start spending money on its own. All four gate combinations were then exercised,
and each one now prints which gate declined and why. The cost was a documented
rule — "no module names any environment variable" — which was true, read well,
and was worth less than a fallback that actually happens.

**A limit of the check worth knowing.** `status.md` records a date and the
filesystem records a timestamp, so an edit made on the same day as the run it
invalidates cannot be ordered against it. Most rows are in that state. The script
reports them as INDETERMINATE rather than clean — its first version called them
fresh, which would have been a fifth instance of the defect it was written to
catch.

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
| `src/mockserver`'s five tools *through a model* | Hand-driven over stdio and verified message by message, twice, byte-identical. No model has ever called them over the transport. | As above. The in-process copies elsewhere in the repo are the closest substitute and are genuinely exercised. |
| Every `examlab` module against a live credential | All eight run on a fabricated script, and that is the only path whose **output** is recorded here. `transport.live()` has returned a real `LiveTransport` once — see the finding below — but no request has ever been sent through one. | `uv sync --extra live`, `PLAYGROUND_EXAMLAB_LIVE=1`, and a credential the `anthropic` SDK resolves. A live run bills a credential this repo does not manage, so its numbers may not be written into this file. |
| The four `messages`-array rules in `examlab/contract.py`, against the real API | All four now provably fire, on six fixtures, and the check is proven against a deliberately disabled rule — `scripts/check_contract_rules.py`. What is still unconfirmed is the other direction: the rules are DOCUMENTED from the tool-use pages and no real 400 has been seen, so the validator may be **stricter** than the API. | One live run that deliberately sends each malformed shape. If the API accepts one, `contract.py` is what is wrong, and it should be corrected there rather than worked around. |
| **D3: skills and path-specific rules** | There is no `.claude/skills/` and no `.claude/rules/` in this repo, so `context: fork`, `allowed-tools`, `argument-hint` and YAML `paths` frontmatter are entirely absent. Task statements 3.2 and 3.3 are untouched, and 3.5 and 3.6 with them. | Writing them. This is the largest coverage gap in the repo and it sits in a 20% domain — see `domain-map.md`. |
| **D4: explicit criteria and few-shot prompting** | Task statements 4.1 and 4.2 have no demo. `prompt_shape` is about injection resistance, which the blueprint does not test. | A demo whose output is objectively checkable. Rejected once for that reason; the reason still stands and the gap is still a gap. |
| `.claude/hooks/block_secret_reads.py` inside a live session | Directly tested, 7/7 cases, including the encoding bug that made it fail open. It has never fired during an actual tool call. | An environment where the settings file is in effect, then an attempted blocked read. |
| `.claude/hooks/check_turn_cap_guard.py` inside a live session | Both modes tested directly: standalone over the repo, and hook mode against a known-bad and a known-good file, exiting 2 and 0. Never fired via a real `PostToolUse` event. | Same as above. |
| `.claude/settings.json` | Its entries were reported as ignored on every run while this repo was written, so neither the permission rules nor the hook registrations have been observed taking effect. | Determine why they are ignored in your setup and correct it; the file itself is valid. |
| `$CLAUDE_PROJECT_DIR` expansion on Windows | Both hooks are registered using it and have only been tested by direct invocation. | Resolves itself the first time a hook fires in-session. |
| Compaction itself | `context_budget.py` measures the distance to the threshold and says outright that it never crosses it. | A deliberately long session or one very large tool result. Real quota, which is why it was not done. |
| Eleven of the twenty-four official tool-use documentation pages | They configure behaviour through Messages API request fields or tool-definition properties — `strict`, `defer_loading`, `allowed_callers`, `eager_input_streaming`, `cache_control`, `input_examples` — none of which the Agent SDK exposes. Reaching them live needs an API key. | Five of the eleven now have their client-side mechanics readable in `src/examlab/`, against a fabricated transport, which is **not** coverage and is not counted as such. The rest are documented page by page in `tool-surface.md` with the reason each is out of reach. |
| `pause_turn`, and a turn mixing a server tool with a client tool | Both are handled inside the harness. No `ServerToolUseBlock` has ever been observed here at all — see finding 1 in `tool-surface.md`. | Server tools, therefore the Messages API. |

## Coverage

Official blueprint domains and weights. The assessment is this repo's own.

| Domain | Weight | Material | Honest assessment |
|--------|--------|----------|-------------------|
| **D1 Agentic Architecture & Orchestration** | 27% | `triage`, `workflow_vs_agent`, `subagent`, `hello`, and three `examlab` modules | **The strongest domain here, and the one that improved most this round.** It opens with a decomposition that works, adds two cost comparisons that both contradict standard advice, and now covers the raw loop: `stop_reason` control flow, the three named anti-patterns, and chaining against dynamic decomposition. Still missing: parallel fan-out, `fork_session` (1.7), and any agent that plans then revises. |
| **D2 Tool Design & MCP Integration** | 18% | the six `tools_mcp` demos, `tools`, `src/mockserver`, and two `examlab` modules | **Deep, with two named holes.** Covers where a tool executes, what a tool costs before anyone calls it, how calls arrive, `tool_choice` semantics and structured error responses. The holes: the external half ships as a documented failure, and eleven of the twenty-four documentation pages are API-ONLY — five of those now readable in `examlab/` against a fabricated transport, which is not the same as demonstrated. |
| **D3 Claude Code Configuration & Workflows** | 20% | `settings.json`, two hooks, `drill.md`, both `CLAUDE.md` files, `check_auth`, the dispatcher and `scripts/` | **The weakest domain against its weight, for two separate reasons.** What exists is mostly inert: the settings file has never been observed taking effect, neither hook has fired in a session, and the slash command has never been invoked. What is missing is examinable: no `.claude/skills/` and no `.claude/rules/` at all, so 3.2 and 3.3 have zero coverage, and 3.5 and 3.6 none either. The memory-hierarchy material is genuinely good and documented against official sources. `check_auth` lands here and its subject is on the guide's out-of-scope list. |
| **D4 Prompt Engineering & Structured Output** | 20% | `prompt_shape`, `structured`, and three `examlab` modules | **Split down the middle.** The structured-output half is now well covered: schema as contract, what a schema cannot buy, validation-retry and the limit where it fabricates instead of failing, batch appropriateness and the SLA arithmetic. The prompt-engineering half is absent — nothing on explicit criteria (4.1) or few-shot prompting (4.2), and `prompt_shape` matches no task statement in the domain. |
| **D5 Context Management & Reliability** | 15% | `context_budget`, `session_resume`, `error_taxonomy`, and the propagation half of `examlab.tool_errors` | Good depth on failure classification and context accounting. Three gaps: compaction is never triggered, there is no demonstration of retry or backoff as a *policy*, and 5.5 and 5.6 — human review, confidence calibration, provenance — have nothing at all. |

## Reader path

Six stuck points were identified in an earlier audit; two more have been found
since. Re-walked from a clean clone's perspective:

| # | Previous finding | Now |
|---|-----------------|-----|
| 1 | `uv run python`, not bare `python` | **Fixed.** The README says so in the install section, and `--list` prints the correct form in its footer. |
| 2 | `check_auth` fails for most readers with no way forward | **Fixed.** It explains the rule, why it exists, and gives three named options including `PLAYGROUND_ALLOW_ANY_AUTH=1` to proceed knowingly. |
| 3 | Machine-specific limitations read as universal | **Fixed.** Rewritten as "Things that may differ where you run this", each with how to check. |
| 4 | Nothing explains what MCP is | **Fixed.** A short section in the README, placed before the first demo that assumes it. |
| 5 | `.claude/` material cannot be exercised by following the README | **Partly.** Two hooks can be run directly from the README; the settings file and the slash command still cannot be exercised without a working interactive session. |
| 6 | Console encoding renders some characters as `?` | **Documented, not fixed.** Named as a terminal issue with the `chcp 65001` workaround. |
| 7 | `domain-map.md` told the reader the labels were unverified, so no authoritative map existed here | **Fixed, 2026-08-21.** The official guide was obtained and every label in the repo changed to match it. The page now carries the blueprint, the old-to-new map, and a report of which demos do not fit where they landed. |
| 8 | The `examlab` modules were invisible to anyone who ran the documented `--list` | **Fixed, and it should not have happened.** They shipped with a second dispatcher of their own. There is one registry now, with a boundary line in the output, and `examlab/__main__.py` is a signpost. Found by a reader asking how to run them, which is not a control. |

**Six fixed, one partly, one documented.** Of the two originals still open, only 5
and 6 can confuse a reader, and neither is fatal.

One new stuck point, named rather than left to be discovered: **the repo now has
two auth rules.** `playground/` is OAuth-only and `check_auth` enforces it;
`examlab/` runs credential-free by default and will use a resolvable credential if
one exists. Both are documented — in the root `CLAUDE.md` and in
`src/examlab/CLAUDE.md` respectively — and a reader who reads only one of those
files will believe the wrong thing about half the repo.
