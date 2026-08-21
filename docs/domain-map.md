# Domain map

Every `DOMAIN` line, every `LESSON` domain field, every `docs/dN-*.md` filename
and every table below uses the **official** CCA-F blueprint numbering. There is
no second numbering left in the repo. If you find one, it is a bug.

## The official blueprint

From the *Claude Certified Architect – Foundations Exam Guide*, version 1.0,
effective July 2026, exam code CCAR-F. Obtained **2026-08-21** as the PDF
published on the Anthropic Partner Academy certification page. Primary source; no
third-party study site was consulted, and none should be used to amend this table.

| # | Content domain | Weight | Doc |
|---|----------------|--------|-----|
| 1 | Agentic Architecture & Orchestration | 27% | `d1-orchestration.md` |
| 2 | Tool Design & MCP Integration | 18% | `d2-tools-mcp.md` |
| 3 | Claude Code Configuration & Workflows | 20% | `d3-claude-code.md` |
| 4 | Prompt Engineering & Structured Output | 20% | `d4-prompt-output.md` |
| 5 | Context Management & Reliability | 15% | `d5-reliability.md` |

Exam shape, same source: 60 items, 120 minutes, four scenarios drawn from a bank
of six, scaled score 100–1000 with a cut score of 720, credential valid twelve
months.

## What the relabel changed, 2026-08-21

The repo previously used labels invented before the guide was reachable. Two
numbers were transposed and one had no counterpart:

| Old label | Now | Files affected |
|-----------|-----|----------------|
| D0 Foundations | dissolved into D1, D2, D3 and D4 | `basics/` |
| D1 Agentic Architecture and Orchestration | D1 (unchanged) | `orchestration/` |
| D2 Claude Code Configuration and Workflows | **D3** | `.claude/`, `run.py`, `teach.py`, `lessons.py`, `scripts/` |
| D3 Prompt Engineering | **D4** | `basics/prompt_shape.py` |
| D4 Tool Design and MCP Integration | **D2** | `tools_mcp/`, `mockserver/` |
| D5 Context Management and Reliability | D5 (unchanged) | `reliability/` |

Where the four `basics/` demos went, since "D0" is gone: `check_auth` to D3,
`hello` to D1, `tools` to D2, `structured` to D4. Two doc files were renamed —
`d2-claude-code.md` to `d3-claude-code.md` and `d4-tools-mcp.md` to
`d2-tools-mcp.md` — and `src/examlab/` dropped the word "Official" from its
`DOMAIN` lines, which had existed only to mark it apart from the old numbering.

**Anything written before that date, including a cached page or an old branch,
uses the old numbers.** That is the only reason this section still exists.

## Where the repo does not fit the blueprint

Step 4 of the old recipe was "report any demo whose content does not fit the
domain it lands in". Doing it produced more than expected, and it is the most
useful thing on this page if you are studying rather than reading.

### Demos that land in a domain the exam does not test there

| Demo | Lands in | The problem |
|------|----------|-------------|
| `basics.check_auth` | D3 | Its subject is **explicitly out of scope**. The guide's out-of-scope list names "Claude API authentication, billing, or account management" and "OAuth, API key rotation, or authentication protocol details". The demo is load-bearing for this repo's cost discipline and answers no examinable question. Run it; do not revise it. |
| `basics.prompt_shape` | D4 | Filed there on the domain's *name*. Its content — instruction/data delimiting against prompt injection — matches **none** of D4's six task statements (explicit criteria, few-shot, structured output, validation-retry, batching, multi-pass review). Injection resistance is not in the blueprint at all. |
| `basics.hello` | D1 | Genuinely D1, but it teaches the **Agent SDK's** loop, where `query()` owns termination. Task statement 1.1 tests `stop_reason` control flow, which this demo cannot show. `examlab/agentic_loop.py` is the one that answers 1.1. |
| `reliability.session_resume` | D5 until 2026-08-21, now **D1** | Filed under D5 on the strength of its directory name. Session state, resumption and forking are task statement **1.7**, under Agentic Architecture. Relabelled; the file stayed in `reliability/` because it is one subject with `session_fork.py`. |
| `basics.structured` | D4 | Adjacent, not equal. `output_format` is an Agent SDK feature; task statement 4.3 tests `tool_use` with a JSON schema. Different mechanism, same goal. `examlab/structured_output.py` covers the examinable one. |

### Task statements with no coverage anywhere in this repo

Listed because a coverage table read without them overstates what is here. This
list was twice as long on the morning of 2026-08-21; what closed is recorded
below it.

- **3.5 (partial) — test-driven iteration and the interview pattern.** Two of
  the four techniques in that statement produce a transcript rather than an
  artifact, and this repo cannot score a transcript. They are written up in
  `d3-claude-code.md`. The other two — examples over prose, and batching
  against sequencing fixes — are in `examlab/refinement.py`, where the
  round-trip count turns out to be a calculation over a dependency graph.
- **Live confirmation of anything in `src/examlab/`.** Eleven modules run against
  fabricated fixtures. The control flow and the arithmetic are real; no claim
  about how a model responds is measured. `docs/status.md` lists this per row.

### What closed on 2026-08-21, and how

- **1.7 forking** — `reliability/session_fork.py`, run for real. A fork
  inherits the baseline, cannot see its sibling, and does not write back into
  its parent; all three were tested separately and all three held. A fork gets
  a new session id, a plain resume keeps the old one, and every branch turn
  re-pays the baseline (18,783 tokens against the parent's 18,930).
- **3.5, in part** — `examlab/refinement.py`.
- **3.2 skills** — `.claude/skills/audit-claims/` and `.claude/skills/new-demo/`,
  between them exercising `context: fork`, `allowed-tools` in a read-only and a
  write-limited form, and `argument-hint`. Never invoked, so the front matter is
  DOCUMENTED.
- **3.3 path rules** — `.claude/rules/checks.md` (globs spanning two
  directories) and `.claude/rules/generated-docs.md` (three named files inside a
  directory whose others share none of the rules). One of these has been
  **observed loading**; see `docs/status.md`.
- **3.6 CI/CD** — documented in `d3-claude-code.md` with the flags, the schema
  argument, and the two mistakes that are not about flags. No pipeline here.
- **4.1 explicit criteria and 4.2 few-shot** — `examlab/review_criteria.py`. The
  earlier refusal to demo these was wrong in one specific way: what cannot be
  checked for free is a model's response, and what can be checked exactly is
  precision and recall against a labelled key.
- **5.5 confidence calibration** — `examlab/confidence_routing.py`.
- **5.6 provenance** — `examlab/provenance.py`.

Rough shape of it now: every domain has material and a document, and every
task statement has either a demo or a written reason it does not. What is
thin is no longer coverage but *evidence* — the D3 configuration is almost
entirely unobserved, and everything in `examlab/` is arithmetic over
fixtures. `docs/status.md` carries the per-domain assessment; this list is
the blueprint-side view of the same thing.

## The defect this page recorded before the guide arrived, and how it turned out

There was no D3 at all in the old numbering until late in the project, and
structured output was filed under "D0 Foundations". Those facts were related:
`basics/structured.py` is about *constraining a response format*, which is a
different subject from *constructing a prompt*, and filing the first in a
general-purpose bucket is what made the absence of the second invisible. The fix
applied at the time was to separate them into two labels.

**The blueprint settles that argument the other way.** Its domain 4 is "Prompt
Engineering **& Structured Output**" — one domain, both subjects. So the two
demos belong together, and the recorded decision to keep them apart was wrong on
the official carve-up. The correction is attached rather than the decision being
quietly reversed, because being wrong about a judgement call is the normal case
and hiding it is what makes the next one harder to check.
