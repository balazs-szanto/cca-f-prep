# Claude Agent SDK Playground — Root Project Memory

Study repo for the Claude Certified Architect – Foundations exam. Optimised for
reading, not for reuse. Every demo is meant to be understood, then argued with.

## Stack
- Python 3.11+, managed with `uv`
- Runtime dependency: `claude-agent-sdk` only. Everything else is the stdlib.
- `uv_build` appears in `[build-system]`; it is a build-time backend shipped with
  uv, not a runtime dependency.

## Auth rule (hard constraint)
This project is written around an **interactive Claude Code CLI session**.
- **Never** set or reference `ANTHROPIC_API_KEY` anywhere in code, docs, or `.env`.
- `basics/check_auth.py` shells out to `claude auth status --json`. It exits 1 if
  the API key variable is set, and if `authMethod` is anything else it explains
  the rule and offers `PLAYGROUND_ALLOW_ANY_AUTH=1` as a knowing override.
- It prints only `authMethod` and `apiProvider`. The same JSON carries account
  and plan identifiers; those answer a different question and are not printed.
- Run it before anything else; every other demo assumes it passed.

## Conventions
- Max 270 lines per Python file. Raised four times, and the history is the
  point. 120 left no room for the commentary that makes a demo teachable. 180
  held until every demo grew a `LESSON` block plus a closing block restating the
  lesson against the run's own numbers — about 40 lines of reader-facing text per
  file, which is content, not padding.

  At 220 the note here said a third raise would mean it was time to split the
  repo. That prediction was wrong, and it is left visible rather than quietly
  edited out. What actually happened is that the `KNOWN_ISSUE` convention
  requires its paragraph to appear twice — once as a constant the runner prints,
  once as a comment on the failing line — because the reader who runs the demo
  and the reader who only opens the file need it in different places. That is
  roughly 25 lines of deliberate duplication in one file, and splitting the file
  would not remove a single one of them. Three files sit between 220 and 240 for
  that reason and no other.

  The rule that replaced the old prediction: if a file exceeds the cap, check
  first whether the excess is duplication that serves a reader. If it is, the
  cap is the thing that is wrong. If it is not, split.

  **The fourth raise, 240 to 270, is the first one where that rule was applied
  and then found insufficient, so it is written up rather than just applied.**
  Three `tools_mcp/` files hit 240 exactly — not a coincidence, a binding
  constraint — and
  an audit found prose had been cut to fit in all three: a generalisation about
  measurement removed from a helper, a cost claim removed from a TRADEOFF, a
  section heading demoted to a footnote so its evidence stopped looking like the
  headline. All of it was restored. The rule was then applied properly and
  worked twice: `instruments.py` was split out and carries the three measuring
  helpers with the explanations they never had room for, and the citation
  apparatus behind one demo's central claim moved to `docs/tool-surface.md`,
  which is the reference document that exists for exactly that. Together those
  removed forty-odd lines from `where_code_runs.py`. It is still 263, because
  what remains is one continuous argument about one demo and any further split
  produces two files neither of which stands alone.

  So the cap moved. The reasoning, stated plainly because the next person to hit
  it deserves it: a line cap is a proxy for "is this file doing too much", and
  when the proxy and the thing it proxies for disagree, the proxy loses. In a
  repo whose product is the explanation, trimming explanation to satisfy a
  number is the one refactor that always makes the artifact worse. Split first —
  it worked twice here and it is nearly always available. Raise the cap only
  after a split has been attempted and has left the file over anyway, and say
  which split you tried.
- Every module opens with a docstring in this exact shape:
  `WHAT / WHY / DOMAIN / TRADEOFF / ALTERNATIVE`.
- Inline comments are prefixed `# WHY:` and carry the reasoning a reader cannot
  recover from the code: why this SDK construct rather than the obvious one, what
  it costs, what breaks if you change it. A comment restating the code is still a
  defect. "More comments" means more explanation, not more narration.
- Prose in English. No emoji in code or docs.
- Every claim about Claude behaviour carries its evidential state in place, in
  the file that makes the claim: **DOCUMENTED** (official docs, with the URL and
  fetch date), **MEASURED** (it was run here, with the output), or **INFERRED**
  (neither — a guess, however reasonable). This replaced an earlier `[VERIFY]`
  marker convention and a central register of open questions; both were
  development scaffolding, and a claim is more useful next to the code it governs
  than in a list nobody rereads. Where documentation and measurement disagree,
  say so and leave the conflict standing.

## Cost discipline
Model calls cost real money, so demos default to `claude-haiku-4-5` and cap
`max_turns` at 3 unless the demo needs more — and where one does, the docstring
says what was measured rather than asserting the cap was fine. Each file names
its model in the docstring and its cost in its `LESSON` block. Never quote an
absolute currency figure in the repo: ratios survive a price change and a repeat
run, absolute numbers do not.

## Layout

Domains are the **official CCA-F blueprint's** (D1–D5), as of the relabel of
2026-08-21. See `docs/domain-map.md` for the table and the old-to-new map.

**This table was the last thing in the repo still carrying the pre-relabel
labels, and it was found on 2026-08-21 by auditing counts in the README rather
than by anything systematic.** It said `D0` for `basics/` — a domain the official
blueprint does not have — `D4` for `tools_mcp/` and `D2` for `.claude/`, both of
which now mean something else. Left recorded because it is the sharpest example
of the failure this repo keeps automating against: the relabel touched every
`DOMAIN` line, every `LESSON` block, both renamed docs, `run.py`, `drill.md`,
`traps.md` and `README.md`, and missed the file whose instructions override all
of them. **A directory is not one domain**, which is the other reason this table
was wrong and the reason it now names them per demo.

| Path | Domain | Contains |
|------|--------|----------|
| `src/playground/basics/` | D1, D2, D3, D4 | auth (D3), hello (D1), prompt shape and structured output (D4), one in-process MCP tool (D2) |
| `src/playground/orchestration/` | D1 | Triage pipeline, workflow vs agent, subagent delegation |
| `src/playground/tools_mcp/` | D2 | Schema design, parallel calls, tool overhead, external MCP, permission gate, execution boundary |
| `src/playground/reliability/` | D5, and D1 for both session demos | Session resume and fork (D1, task statement 1.7), error taxonomy, context budget |
| `src/examlab/` | D1, D2, D3, D4, D5 | The request level the SDK owns for you: the loop, its anti-patterns, parallel tool use, chaining, `tool_choice`, tool errors, refinement, review criteria, structured output, validation-retry, batches, confidence routing, provenance |
| `.claude/` | D3 | Settings, two hooks, two skills, two path rules, a slash command |
| `docs/` | all | One file per domain, plus traps, the tool-surface triage, the run inventory and the blueprint map |

`src/playground/CLAUDE.md` is a nested memory file; it demonstrates hierarchy and
is deliberately narrower than this one. `src/examlab/CLAUDE.md` is the other one,
and it amends the auth rule below rather than only narrowing it — read it before
running anything in that package.

## Running
    uv sync
    uv run python -m playground.run --list
    uv run python -m playground.run basics.check_auth
