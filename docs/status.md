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
| `basics.hello` | RAN CLEAN | 2026-08-21 | One sentence in 1 TextBlock, `[success] 1 turn(s)` in 6,023 ms of API time, a session id, and the usage split showing uncached input dwarfed by cache reads. |
| `basics.prompt_shape` | RAN CLEAN | 2026-08-21 | **Three times now.** Every run: two correct summaries, and `A resisted / B resisted`. The injected word has never got through either construction. A null result, reported as one. |
| `basics.structured` | RAN CLEAN | 2026-08-21 | All 9 required keys present, host-side check clean, `success` in 3 turns against a cap of 2. |
| `basics.tools` | RAN CLEAN | 2026-08-21 | `(17 + 8) x 4 = 100`, the calculator tool called in two steps, `[success] 4 turns`. |
| `orchestration.triage` | RAN CLEAN | 2026-08-21 | **Three runs, identical routing every time.** 1 of 4 requests rejected by stage 1 for zero model calls, 1 settled by stage 2, 2 escalated; 5 model calls against the 8 an unconditional pipeline would make. And stage 3 declined its tool again - see below, it is now reproducible. |
| `orchestration.workflow_vs_agent` | RAN CLEAN | 2026-08-21 | Identical labels both ways; 3 API calls against 1, and the workflow cost **3.6x** the agent. Recorded as 3.5x from the earlier run; the ratio held direction and moved a little. |
| `orchestration.subagent` | RAN CLEAN | 2026-08-21 | Delegation was more expensive on **4 of 5** metrics - turns, api_ms, in_tokens and cost - not on all of them, which the earlier row overstated as 'every delta positive'. |
| `tools_mcp.where_code_runs` | RAN CLEAN | 2026-08-21 | **Twice, plus a re-run.** Both arms answered; the census showed `ToolUseBlock(mcp__rel__lookup_release) x1` against `ToolUseBlock(WebSearch) x2` - the same class - and `ServerToolUseBlock` appeared 0 times. Our handler ran in one arm only. |
| `tools_mcp.schema_design` | RAN CLEAN | 2026-08-21 | Weak schema returned one unparsed string, `{'reading': 'Roof sensor: 21.5 degrees at 14:30'}`; the strong schema returned `sensor`/`celsius`/`time_hhmm` as typed fields. |
| `tools_mcp.parallel_tools` | RAN CLEAN | 2026-08-21 | Both arms `[1, 1]` in 3 turns - the null result on grouping held. The gaps moved and the conclusion did not: **7 ms** idle between the independent pair against **1,612 ms** between the dependent pair, roughly 230:1 where the first run measured 86:1. |
| `tools_mcp.tool_overhead` | RAN CLEAN | 2026-08-21 | Re-run after the relabel, and **the built-in figure moved** — see below. 221 tokens per tool plus 5 fixed, predicting every unfitted row to 0 tokens' error; `claude_code` built-ins now rest at 16,579, **+14,146** against a no-tools session; every MCP row still needed 2–3 polls to settle. |
| `tools_mcp.external_mcp` | **KNOWN ISSUE** | 2026-08-21 | A refusal notice scraped from stderr, then the KNOWN ISSUE block, then exit without an agent run. Re-run after the relabel; the refusal is unchanged. |
| `tools_mcp.permission_gate` | RAN CLEAN | 2026-08-21 | Priority-1 tickets survived; `TCK-002` and `TCK-005` were deleted; 2 entries in `permission_denials` naming `TCK-003` and `TCK-010`; `success` in 6 turns against a cap of 3. |
| `reliability.session_resume` | RAN CLEAN | 2026-08-21 | In-session recall billed 14,207 then 18,772 in+cache; the resumed session recalled the fact at **19,068**; the fresh session billed **14,222** and did not know it. Resuming costs more because it replays. |
| `reliability.session_fork` | RAN CLEAN | 2026-08-21 | Fork A and fork B both recalled the baseline; fork B did not know branch A's rename; the re-resumed parent did not either. Forks got new session ids (`111b0ac0`, `fd0605d7`) while the plain resume kept `c3212f4e`. Billed 18,783 / 18,783 / 18,930 in+cache — every branch turn re-pays the baseline. |
| `reliability.error_taxonomy` | RAN CLEAN | 2026-08-21 | `'retry' -> ENVIRONMENT: retry the identical call`, `'retry' -> ARGUMENTS: the caller must change something`, then "2 distinct buckets: the taxonomy discriminates." |
| `reliability.context_budget` | RAN CLEAN | 2026-08-21 | Resting cost **16,618** tokens (8.0% of the usable window) where the earlier run read ~12,400; auto-compact threshold 167,000 unchanged; headroom **148,133**; and 32,949 of the reported 'Free space' sits past the threshold. Compaction did not run. |
| `examlab.agentic_loop` | RAN CLEAN | 2026-08-21 | Three exchanges — two `tool_use`, one `end_turn` — 6 messages in history, then the seven-row `stop_reason` table and `LoopBudgetExceeded` after 2 forced iterations. |
| `examlab.loop_antipatterns` | RAN CLEAN | 2026-08-21 | Four diagnoses. Two returned silently: the narration after 1 request, and an empty string after 2. Two raised `TransportError`: script exhaustion at request 4, and a rule 4 role violation at request 1. |
| `examlab.chaining` | RAN CLEAN | 2026-08-21 | 1 / 4 / 3 requests and largest prompts of 468 / 378 / 549 characters. The dynamic arm's largest request **exceeds** the single pass, which the file's first draft claimed the opposite of. |
| `examlab.tool_choice` | RAN CLEAN | 2026-08-21 | The four modes, the documented forcing overhead, then 6 iterations with no terminal `stop_reason` while the choice was forced, against 2 requests once it was dropped. |
| `examlab.tool_errors` | RAN CLEAN | 2026-08-21 | Six cases. The structured surface produced retry, fix-and-re-call, escalate, escalate, fix-and-re-call, report; the generic surface produced `guess` six times. |
| `examlab.refinement` | RAN CLEAN | 2026-08-21 | Three examples settle 3 of 4 edge cases and the prose spec settles none; the interacting fix set has 5 dependency edges, costing 9 sequential round trips against 2 batched, and the independent set inverts the recommendation. |
| `examlab.review_criteria` | RAN CLEAN | 2026-08-21 | Three prompts scored on one nine-item answer key: precision 25%, 80%, 83% and recall 20%, 80%, 100%. One false positive survives all three arms. |
| `examlab.structured_output` | RAN CLEAN | 2026-08-21 | Three extractions: one clean, one passing schema and cross-field checks while disagreeing with its source, one caught only by the `currency_detail` cross-field rule. |
| `examlab.validation_retry` | RAN CLEAN | 2026-08-21 | All three reported valid by attempt 2 — the third by returning `currency_detail='CHF'`, which appears nowhere in its source and passed every check. |
| `examlab.batches` | RAN CLEAN | 2026-08-21 | 5 resubmission requests from 3 failures, and a cadence table where an 8-hour window misses a 30-hour SLA by 2 hours and a 6-hour window meets it with zero margin. |
| `examlab.confidence_routing` | RAN CLEAN | 2026-08-21 | 85% aggregate accuracy over 20 extractions; `scan` at 60% and `vat_rate` at 60%; two of the three errors sit at 0.96 confidence or above, and the 0.90 routing threshold reviews 30% of the volume while catching none of them. |
| `examlab.provenance` | RAN CLEAN | 2026-08-21 | Six findings through two synthesis arms: 0 of 6 attributable after the lossy one, 5 of 6 after the preserving one. Then two numeric disagreements, one five years apart and one a genuine methodological conflict. |

### What "RAN CLEAN" means for the `examlab` rows, which is less than it looks

Those twelve rows are true and narrow. The code ran and printed what the row
says. What it consumed was fabricated, and is labelled `SCRIPTED` in place — a
fourth provenance state introduced in `src/examlab/CLAUDE.md` alongside
DOCUMENTED, MEASURED and INFERRED.

The fabrication takes two shapes, and the distinction is worth one line.
Six of the twelve consume a scripted **response** — a list of Messages API
replies this repo wrote — so what is real about them is the request their
loop built and the validator's verdict on it. The other five
(`tool_errors`, `structured_output`, `review_criteria`, `refinement`,
`confidence_routing`, `provenance`) have no transport at all: they are
arithmetic and policy over a fabricated **fixture**, so what is real about
them is every number printed, given that fixture. `refinement` is in the second
group and is the clearest case of it: its round-trip counts are a calculation
over a dependency graph, and its edge-case verdicts are this repo's judgement.

So each row is evidence about a control flow and about nothing else. That
`loop_antipatterns` returns an empty string after two requests is a fact about
that loop. It is **not** a fact about how often a model emits a bare `tool_use`
turn, and no row above should be read that way. The distinction matters because a
scripted run and a live one are indistinguishable on a console, which is why the
label is printed by the banner on every run rather than left to this page.

They carry no caveat for a different reason from the rest of the table: there is
no model behaviour behind them to drift, and re-running them costs nothing. Every
one was executed after its last edit.

### The caveat, stated once - and it is now empty

**Zero rows are marked "see caveat" as of 2026-08-21.** Every demo in the table
above was executed on that date, after its last edit, and its row records what
that execution printed. This is the first time in the project that has been
true, and it took a deliberate pass: fifteen of the thirty spend quota, and they
were run one after the other for no reason except that the table was about to be
merged and half of it was asserting output nobody had seen since editing it.

The history matters more than the current state, because the current state will
decay the moment anyone edits a demo.

**What the caveat used to say.** Fourteen rows carried it. Their behaviour had
been measured on 2026-08-20, and their files had since been edited - every demo
gained a LESSON and closing block, seven gained a `try` around a capped
`query()` loop, three gained docstring material moved out of a retired register,
and all of them were touched by the domain relabel. Those edits had been verified
only by driving the real entry point with a stubbed SDK, for zero tokens, which
catches a missing key or a format bug and cannot catch behavioural drift.

**Two of the fourteen carried a stronger version**, and it is worth recording
what it was: both had been rewritten *because of* what their first run showed,
and the budget ran out before the rewrite could be run, so no model call had ever
been made by the version on disk. That is now false for both, and the numbers in
their rows are the ones their current code produced.

**What the re-run cost, in findings.** Four numbers moved, and none of them
moved the conclusion they support:

| Row | Was | Now | Reading |
|-----|-----|-----|---------|
| `workflow_vs_agent` | 3.5x | **3.6x** | The workflow is still the expensive arm. |
| `subagent` | every delta positive | **4 of 5** | The earlier row overstated it. One metric was not worse. |
| `parallel_tools` | 15 ms vs 1,285 ms | **7 ms vs 1,612 ms** | 230:1 where it was 86:1. The clock still separates the arms and the grouping still does not. |
| `context_budget` | ~12,400 resting | **16,618 resting** | Third independent sighting of the harness growing - see below. |

The `subagent` row is the one to take seriously. "Every delta positive" is a
stronger claim than "delegation cost more", it was written from a run that
supported it, and it did not survive a second run. Overstatement in the
flattering direction is the failure this whole file exists to catch, and it got
through review once.

**The harness grew under us, and three separate instruments now say so.**
`tool_overhead` read the built-in toolset at +14,146 tokens against a no-tools
session where it had read roughly 11,000 a day earlier. `context_budget`
independently read a resting cost of 16,618 where it had read about 12,400, with
the auto-compact threshold unchanged at 167,000. And `session_resume`'s
in-session turns billed 14,207 and 18,772 where the earlier run's numbers were
lower. Same machine, same pinned lock file, nothing in this repo changed.

That is the finding worth carrying out of this round. **A cost that belongs to
the platform rather than to your code is a measurement with a date on it, not a
constant** - and the two halves of `tool_overhead` behaved completely
differently, with the per-tool figure holding to the token at 221 plus 5 fixed
while the platform figure moved a quarter. Any budget built on the second kind
needs re-measuring rather than citing.

**Why the accounting is checked by a script.** An earlier version of this
section said "six rows" while seven were marked and five were named. It was found
by review, not by the author, which is why `scripts/check_status_freshness.py`
exists: it compares each row's recorded date against the file's modification time
and fails when a file is newer than the measurement justifying it. Prose
accounting of this kind had been got wrong four times before it was automated.

`scripts/check_caveat_accounting.py` guards this section directly - stated counts
against the markers in the table, named demos against marked ones in both
directions, and every row registered in the dispatcher. It was proven against
four fixtures reproducing real defect shapes, and it failed on its own first
contact with this file because a filename has the same shape as a demo name.

**A shape that check was not designed for, now that it is being used in it.**
With the caveated set empty, the "named" list below becomes the entire table,
which is redundant prose that exists to satisfy a mechanical contract. The check
is still correct and still enforcing something real - if a row silently reacquires
a marker, the counts stop matching - so the contract stays and this paragraph
records the awkwardness rather than loosening it.

`scripts/check_conventions.py` covers the line cap declared in `CLAUDE.md` and
the `KNOWN ISSUE` comment-to-constant sync. `scripts/check_contract_rules.py`
proves each of the four request-contract rules fires, and was itself proven
against a deliberately disabled rule.

**One item is deliberately left unchecked: the counts in the README.** They are
hand-maintained and the README says so. Deriving them would mean parsing prose
for numbers written as words, which is a worse problem than the checks above
solve - each of those reads a table, an AST or a generator's own output. A second
instance of the same gap surfaced on 2026-08-21: the bucket totals in
`tool-surface.md` were stated three times and wrong in all three, and no script
reads that page.

`scripts/check_lessons_fresh.py` regenerates `docs/lessons.md` into memory and
compares. It exists because that regeneration step was missed once and a docs
file disagreeing with its own source reached a public remote.

**Two defects found by running paths rather than reading them**, both on
2026-08-21, both in code written the same day. The validator in
`examlab/contract.py` has four rules and only the fourth had ever fired; the
other three had never executed at all, so three quarters of the thing doing the
grading was unexercised. And `transport.live()` assumed the `anthropic` client
would raise without a credential - it does not, so a reader who installed the
optional extra without one got a traceback where the documentation promised a
scripted fallback. Both are fixed and both were found by running the path, which
took one command each and had not been done.

**The thirty rows with no caveat** are the whole table, and here they are:


`basics.check_auth`, `basics.hello`, `basics.prompt_shape`,
`basics.structured`, `basics.tools`, `orchestration.triage`,
`orchestration.workflow_vs_agent`, `orchestration.subagent`,
`tools_mcp.where_code_runs`, `tools_mcp.schema_design`,
`tools_mcp.parallel_tools`, `tools_mcp.tool_overhead`,
`tools_mcp.external_mcp`, `tools_mcp.permission_gate`,
`reliability.session_resume`, `reliability.session_fork`,
`reliability.error_taxonomy`, `reliability.context_budget`,
`examlab.agentic_loop`, `examlab.loop_antipatterns`, `examlab.chaining`,
`examlab.tool_choice`, `examlab.tool_errors`, `examlab.refinement`,
`examlab.review_criteria`, `examlab.structured_output`,
`examlab.validation_retry`, `examlab.batches`, `examlab.confidence_routing`,
`examlab.provenance`.

**A limit of the check worth knowing.** `status.md` records a date and the
filesystem records a timestamp, so an edit made on the same day as the run it
invalidates cannot be ordered against it. Every row is currently in that state,
which is the price of having run everything on one day. The script reports them
as INDETERMINATE rather than clean - its first version called them fresh, which
would have been a fifth instance of the defect it was written to catch.


### The `.claude/` material was observed working, twice, and that is new

**MEASURED, 2026-08-21.** `.claude/rules/generated-docs.md` was written, and on
the next edit to `docs/status.md` its full contents appeared in the session
context, unprompted. `.claude/rules/checks.md` did not, because no file matching
its globs was touched in the same window.

That is worth recording for two reasons. It is the **first configuration under
`.claude/` in this repo ever observed taking effect** — the settings file has
been reported ignored on every run, and neither hook has fired in a session, so
the D3 material had until now been entirely inert. And it settles the mechanism
rather than the intention: the `paths` front matter was matched against the file
being edited, and the rule that did not match stayed out of context, which is
exactly the token argument for path scoping and not merely its rationale.

The second observation is weaker, worth separating, and it changed while this
file was being written. Both skills under `.claude/skills/` were **discovered**
— they appeared by name and description in the session's available-skills list
shortly after being written, unasked. Some minutes later, in the same session,
**they were absent from that list again**, with both `SKILL.md` files byte-
identical and untouched on disk.

So the honest claim is narrower than the first draft of this paragraph: the
directory layout and the `name`/`description` front matter are sufficient to be
registered **at least once**, and registration was not observed to persist.
Why it dropped is unknown here and this repo cannot settle it — the plausible
causes (a re-scan, a context boundary, the same workspace-trust condition that
keeps `settings.json` inert) are not distinguishable from inside the session.
The operational consequence is the part that transfers: **a skill sitting in
the right directory is not the same as a skill being available right now**, so
anything load-bearing does not belong in one. That is the same conclusion
`d3-claude-code.md` reaches from the other direction, and it is now MEASURED
rather than argued.

Discovery is not invocation, and the distinction is the whole of what is still
unknown. Neither skill has been run, so **`context: fork` and `allowed-tools`
remain DOCUMENTED** — in particular, that `allowed-tools` actually refuses a
tool rather than merely advertising a restriction has not been seen here, and
it is the one claim in that front matter with a security-shaped consequence.

Both observations were made by the agent editing the repo, in the session that
wrote the files. That is a weaker position than a fresh session confirming
them, and is why these paragraphs say what was seen rather than what generally
happens.

### The one result worth reading twice, and it is now reproducible

`orchestration.triage` has run three times with identical routing, and on **two
of those three** a stage-3 call **declined to use its tool**. The 2026-08-21 run
produced it again, and close to verbatim: "The ticket lookup tool requires
authentication that isn't available in this session. You'll need to authorize the
claude.ai connector in your connector settings first, then I can look up TCK-003
for you."

The tool is in-process. There is no server, no connector and no authentication -
`create_sdk_mcp_server` builds it out of Python objects in the same process. The
model invented an infrastructural reason not to act, named a real product surface
to make it plausible, and offered a next step the user cannot take because the
thing it refers to is not involved.

**What changed with this run is its status, not its content.** It had been
recorded as something that happened once in `triage` and once in an unrelated
demo, which reads as an anomaly. Two occurrences in three runs of the same demo
is a rate, and the second escalated call in the same run answered normally, so
this is not a broken tool or a broken session - it is one call in one turn
choosing a fluent refusal.

It is written up at the line where it bit, in `orchestration/triage.py`'s STAGE 3
NOTE, and as a trap in `traps.md`. It remains the most operationally dangerous
behaviour recorded in this repo, because nothing marks it: `subtype` says
`success`, `is_error` is unset, `permission_denials` is empty, and the turn count
is normal. A pipeline that checks for errors sees a healthy run and forwards a
confident wrong answer.

## Unaccounted for

Neither RAN CLEAN nor covered by a declared KNOWN_ISSUE. These are gaps.

| Thing | Why it is unaccounted for | What it would take |
|-------|---------------------------|--------------------|
| The agent-run branch of `external_mcp.py` (~40 lines below the refusal check) | Never executed by the author. Its `LESSON` says INFERRED and a comment marks the boundary, but that is a label on unrun code. | An environment where the server attaches, then one run. It may already work for you. |
| `src/mockserver`'s five tools *through a model* | Hand-driven over stdio and verified message by message, twice, byte-identical. No model has ever called them over the transport. | As above. The in-process copies elsewhere in the repo are the closest substitute and are genuinely exercised. |
| Every `examlab` module against a live credential | All eight run on a fabricated script, and that is the only path whose **output** is recorded here. `transport.live()` has returned a real `LiveTransport` once — see the finding below — but no request has ever been sent through one. | `uv sync --extra live`, `PLAYGROUND_EXAMLAB_LIVE=1`, and a credential the `anthropic` SDK resolves. A live run bills a credential this repo does not manage, so its numbers may not be written into this file. |
| The four `messages`-array rules in `examlab/contract.py`, against the real API | All four now provably fire, on six fixtures, and the check is proven against a deliberately disabled rule — `scripts/check_contract_rules.py`. What is still unconfirmed is the other direction: the rules are DOCUMENTED from the tool-use pages and no real 400 has been seen, so the validator may be **stricter** than the API. | One live run that deliberately sends each malformed shape. If the API accepts one, `contract.py` is what is wrong, and it should be corrected there rather than worked around. |
| Whether the stage-3 tool refusal is bounded | It has now appeared in 2 of 3 `triage` runs and once in an unrelated demo, so it is reproducible rather than anomalous - but nothing here establishes a rate, a trigger, or whether a different model or system prompt suppresses it. | Many more runs, deliberately varied. Real quota, and the most valuable open question in this repo. |
| The two skills, **invoked** | Written 2026-08-21. Both were observed being *discovered* once and then absent from a later listing in the same session, files unchanged — see the section above. Neither has been run, so `context: fork`, `allowed-tools` and `argument-hint` are all DOCUMENTED and none is MEASURED. The claim that matters and is unverified: that `allowed-tools` refuses a tool rather than advertising a preference. | One invocation of each in an interactive session, and an attempt to use a tool the front matter excludes. Also worth settling: why registration did not persist. |
| Whether a real model responds to the three prompts in `review_criteria.py` the way the fixture says | The scores are exact arithmetic over an authored finding set, so the *direction* of the effect is asserted. The earlier decision not to demo 4.1 and 4.2 at all was wrong in one specific way — precision and recall against a labelled key are checkable for free — but that is not the same as having measured a model. | Run all three prompts live over a real diff with a hand-labelled key, three times each for variance. The prompt texts are written to be lifted straight into that. |
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
| **D1 Agentic Architecture & Orchestration** | 27% | `triage`, `workflow_vs_agent`, `subagent`, `hello`, `session_resume`, `session_fork`, and three `examlab` modules | **The strongest domain here.** A decomposition that works, two cost comparisons that both contradict standard advice, the raw loop with `stop_reason` control flow and its three named anti-patterns, chaining against dynamic decomposition, and 1.7 in full — `session_fork` tests fork inheritance, sibling isolation and parent integrity as three separate assertions and all three held. Still missing: parallel fan-out, and any agent that plans then revises. |
| **D2 Tool Design & MCP Integration** | 18% | the six `tools_mcp` demos, `tools`, `src/mockserver`, and two `examlab` modules | **Deep, with two named holes.** Covers where a tool executes, what a tool costs before anyone calls it, how calls arrive, `tool_choice` semantics and structured error responses. The holes: the external half ships as a documented failure, and eleven of the twenty-four documentation pages are API-ONLY — five of those now readable in `examlab/` against a fabricated transport, which is not the same as demonstrated. |
| **D3 Claude Code Configuration & Workflows** | 20% | `settings.json`, two hooks, two skills, two path rules, `drill.md`, both `CLAUDE.md` files, `refinement`, `check_auth`, the dispatcher and `scripts/` | **Complete on paper and the thinnest on evidence.** Every task statement now has material: skills with all three frontmatter fields (3.2), path rules in both the spans-directories and narrower-than-a-directory shapes (3.3), CI documented with its flags (3.6), and 3.5 carrying a written reason for having no demo. What has actually been *observed* is one path rule loading. The settings file has never taken effect, neither hook has fired in a session, the slash command has never been invoked and neither skill has been. So the gap moved from coverage to evidence, which is progress and is not the same as done. `check_auth` lands here and its subject is on the guide's out-of-scope list. |
| **D4 Prompt Engineering & Structured Output** | 20% | `prompt_shape`, `structured`, four `examlab` modules and `d4-prompt-output.md` | **No longer split.** The structured-output half covers schema as contract, what a schema cannot buy, validation-retry and the limit where it fabricates rather than fails, and batch appropriateness with the SLA arithmetic. The prompt-engineering half arrived with `review_criteria`, which scores three prompts against one labelled key and shows that a confidence hedge moves precision by nothing while a categorical list moves it from 25% to 80%. What is asserted rather than measured there is the model's response; the arithmetic is exact. `prompt_shape` still matches no task statement in the domain and says so. |
| **D5 Context Management & Reliability** | 15% | `context_budget`, `session_resume`, `error_taxonomy`, and three `examlab` modules | Good depth on failure classification and context accounting, and 5.5 and 5.6 are now covered: `confidence_routing` shows an aggregate hiding two independent segment failures and a plausible routing threshold catching none of the errors, `provenance` shows attribution dying in the summarising step and a date field separating a real conflict from a stale figure. Two gaps left: compaction is never triggered, and there is still no demonstration of retry or backoff as a *policy* — the repo classifies failures without showing what reacts to them on a timer. |

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
