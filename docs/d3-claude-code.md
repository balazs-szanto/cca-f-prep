# D3 — Claude Code Configuration and Workflows

## The concept

Configuration in Claude Code is layered, and the layers differ in what they can
promise. Memory files (`CLAUDE.md`) are advisory: they shape behaviour by
entering the context, and anything else that can put text in the context can
argue with them. Settings (`.claude/settings.json`) are declarative rules the
harness applies — permission allow and deny lists matched against tool calls.
Hooks are executable: they run as real subprocesses at lifecycle points and can
deny a call outright, so they are the only layer that is not negotiable by
prompt.

Choose by consequence. A convention you would like followed belongs in a memory
file. A rule that must hold belongs in a hook, because a hook cannot be talked
out of it. Settings sit in between: deterministic, but limited to patterns they
can match, which is why the hook in this repo catches a credential path buried
inside a Bash command string that no `Read(...)` glob would ever inspect.

There are two more layers, and both were absent from this repo until
2026-08-21. **Path-scoped rules** (`.claude/rules/*.md` with a `paths` list of
globs in their front matter) are memory that loads only when the file being
edited matches. **Skills** (`.claude/skills/<name>/SKILL.md`) are memory that
loads only when invoked, and can carry their own tool restrictions and their own
context. So the layers are better read as a grid than a ladder: advisory or
enforced on one axis, always-loaded or conditionally-loaded on the other.

| | Always in context | Loaded on a condition |
|---|---|---|
| **Advisory** | root `CLAUDE.md` | nested `CLAUDE.md`, `.claude/rules/`, skills |
| **Enforced** | settings `deny`, hooks | a skill's `allowed-tools`, while it runs |

The bottom-right cell is the one worth noticing: `allowed-tools` in skill front
matter is a real restriction, not a request, and it applies for the duration of
the skill and no longer. That makes it the only enforcement in Claude Code with a
scope narrower than the session.

Memory files nest, and the nesting is weaker than it looks. A deeper `CLAUDE.md`
adds to the root one rather than replacing it, so duplicated guidance drifts and
nobody can say which copy is authoritative. But nested files also load lazily —
only once Claude reads a file in that subdirectory — and they are not re-injected
after compaction, while the root file is. A nested rule is therefore absent more
often than present. Put anything that must hold for a whole session in the root
file, and reserve nested memory for guidance that is cheap to re-derive from the
code sitting beside it.

## Where it lives in this repo

- `CLAUDE.md` and `src/playground/CLAUDE.md` — the hierarchy, deliberately
  non-overlapping.
- `.claude/settings.json` — scoped permission allow and deny lists, plus the hook
  registration.
- `.claude/hooks/block_secret_reads.py` — a `PreToolUse` hook that denies any
  tool call touching credentials, and fails closed when it cannot parse its input.
- `.claude/hooks/check_turn_cap_guard.py` — a `PostToolUse` hook that parses the
  AST of an edited file and flags an agent loop setting `max_turns` with no `try`
  around it. It is the counter-example to everything else on this page: not a
  permission decision at all, but a correctness check, and the clearest evidence
  here that a hook is worth writing even when nothing is being guarded against an
  adversary. The bug it looks for had been written, fixed and declared gone three
  times in this repo before anyone automated the check; the automated version
  found seven live instances on its first run. Note the deliberate asymmetry with
  the hook above: this one fails **open** on a path it cannot resolve, because a
  lint that blocks edits gets switched off, whereas a secrets guard that fails
  open is worse than none. Same mechanism, opposite default, because the cost of
  being wrong runs in opposite directions.
- `.claude/skills/audit-claims/SKILL.md` — `context: fork`,
  `allowed-tools: Read, Grep, Glob`, `argument-hint`. Sweeps a path for
  behavioural claims carrying no evidential label. Read-only on purpose: an
  auditor that can write is one that can quietly fix what it found.
- `.claude/skills/new-demo/SKILL.md` — `context: fork`,
  `allowed-tools: Read, Write, Edit`, and deliberately **no `Bash`**. Scaffolds a
  demo module and its registry entry. This is the "limit to file operations to
  prevent destructive actions" case: it can create and amend, not delete or run.
- `.claude/rules/checks.md` — `paths` covering `scripts/check_*.py`,
  `scripts/prepublish_check.py` and `.claude/hooks/check_*.py`. The check-script
  conventions span two directories, which is the whole reason it is a path rule.
- `.claude/rules/generated-docs.md` — `paths` naming three specific files inside
  `docs/`, a directory whose other files share none of those rules.
- `.claude/commands/drill.md` — a custom slash command, `/drill d2`.
- `src/playground/run.py` — one dispatcher so every demo has a single entry point.

## Choosing between a skill, a path rule and a memory file

All three put text in the context. They differ in *when*, and that is the whole
decision.

| Mechanism | Loads | Pick it when |
|-----------|-------|--------------|
| root `CLAUDE.md` | always | the standard is universal and short |
| `.claude/rules/` with `paths` | when a matching file is touched | the convention is per-file-type and the files are scattered |
| nested `CLAUDE.md` | when a file in that directory is read | the convention is genuinely directory-bound |
| `.claude/skills/` | when invoked | it is a *task*, not a standard |

The rule of thumb that survives contact with a real repo: **if you would want it
applied without being asked, it is not a skill.** A skill has to be chosen, and
anything load-bearing that depends on someone choosing it will be skipped on the
day it mattered. Conversely, putting a long procedure in `CLAUDE.md` because it
"should always be available" spends context on every turn to make one turn
cheaper.

Two of this repo's own decisions read against that table. `audit-claims` is a
skill and not a rule, even though it enforces a repo-wide convention, because
what it describes is a *procedure to run against a path* rather than a constraint
on the file in front of you. The convention itself already lives in the root
`CLAUDE.md`, in one paragraph; the skill is how you go looking for violations.
And `context: fork` on both skills exists for the same reason in both cases: they
read whole files and quote them back, which the main conversation needs for
exactly as long as it takes to produce the finding.

## Path rules versus a nested `CLAUDE.md`

They look interchangeable and are not. A nested memory file is bound to a
directory; a path rule is bound to a glob. Whenever the set of files sharing a
convention is not the same as the set of files in a directory, only one of the
two can express it.

The clearest case in this repo is `.claude/rules/checks.md`. The check-script
conventions apply to seven files in **two** directories — `scripts/` and
`.claude/hooks/` — and to nothing else in either. A `scripts/CLAUDE.md` would
miss the hooks and would also catch its neighbours that are not checks;
duplicating it into `.claude/hooks/CLAUDE.md` recreates the drift problem the
hierarchy section above warns about. One glob list expresses it exactly once.

`generated-docs.md` is the second case and the sharper one: it names three files
*inside* `docs/`, a directory whose other files — `traps.md`, `domain-map.md`,
the four domain docs — share none of those rules. A `docs/CLAUDE.md` cannot be
narrower than the directory, so there is no version of it that says "never
hand-edit this one file".

The token argument is real but secondary. A path rule that does not match is not
loaded at all, so conventions for code you are not touching cost nothing. That
matters most where the rules are long, which is where the temptation to put them
all in the root file is also strongest.

## Claude Code in CI, which this repo documents and does not run

**DOCUMENTED, not MEASURED — there is no pipeline here and this has never been
executed.** Recorded because the mechanism is small and the failure mode is
memorable.

The failure is a job that hangs forever. A bare `claude "review this diff"`
starts an interactive session and waits for input that no runner will ever type.
The fix is `-p` (or `--print`): it processes the prompt, writes the result to
stdout and exits.

    claude -p "Review the staged diff for security issues" \
      --output-format json \
      --json-schema ./ci/finding.schema.json

`--output-format json` with `--json-schema` is what makes the output
machine-parseable enough to post as inline review comments, rather than prose a
script has to guess at. The schema belongs in the repo next to the workflow, for
the same reason every other contract here does.

Two things that are easy to get wrong and are not about flags:

- **`CLAUDE.md` is how a CI invocation learns the project.** Testing standards,
  fixture conventions, review criteria — a CI run has no interactive history, so
  whatever is not in a memory file is not known. This is the strongest practical
  argument for the root file being good.
- **Do not review with the session that generated.** The same session retains
  the reasoning that produced the code and is less likely to question it. An
  independent invocation with no prior context catches more. When re-running a
  review after new commits, pass the previous findings in and ask for only new or
  still-unaddressed issues, or every push re-posts the same comments.

## Iterative refinement, and why this repo has no demo of it

Task statement 3.5 — concrete input/output examples over prose, test-driven
iteration, the interview pattern, and batching interacting fixes into one message
against fixing independent ones sequentially. **There is no demo here**, and the
reason is worth stating rather than leaving as an apparent oversight: every
technique in it is a property of *how a person drives a session*, and this repo's
standard for a demo is an objectively checkable outcome printed to a console.

What can honestly be said is that the repo is itself an artifact of the pattern.
`docs/status.md` records four separate occasions where prose accounting was
wrong, each of which turned into a check script — which is test-driven iteration
with the tests written after the failure rather than before. And the most
effective corrections in this round came from runs contradicting a docstring, not
from anyone re-reading one: two files in `src/examlab/` say outright that their
first draft claimed the opposite of what the numbers showed.

## Common trap

Assuming `.claude/settings.json` is in effect because the file exists and is
valid. Whether its entries are applied depends on conditions outside the file,
and when they are not applied the only signal is a line on stderr saying so —
the run otherwise proceeds normally. That was the case throughout the writing of
this repo: every run reported its `permissions.allow` entries as ignored, and
nothing else indicated it. If you rely on a `deny` rule for safety and never read
stderr, you can believe you are protected while nothing is enforced. Run once
with stderr visible and read what it says about your settings before trusting any
rule in that file.

## Scenario questions

1. You want to guarantee an agent never runs `terraform apply`. Where do you put
   that rule, and what is wrong with each place you did not pick?

2. A teammate adds a rule to the root `CLAUDE.md` and copies it into three nested
   ones "so it definitely applies". What is the failure mode, and how does it
   actually surface months later?

3. Your `PreToolUse` hook cannot parse an event it was handed. Argue both sides
   of fail-open versus fail-closed, then commit to one for a secrets guard.

4. Your team's test files sit beside the code they test, spread through a dozen
   directories, and you want one set of testing conventions applied whenever any
   of them is edited. A colleague proposes a `CLAUDE.md` in each directory.
   What breaks, and what do you do instead?

5. A skill produces four hundred lines of codebase analysis and the main
   conversation is then useless for the next twenty turns. Which single piece of
   front matter fixes this, and what does it cost you?

6. Your CI job invokes Claude Code and hangs. After you fix that, the review
   comments are prose that your posting script cannot place on a line. Name both
   fixes, and then name the thing neither fix addresses.

<details>
<summary>Answers</summary>

**1.** A hook. It executes, sees the resolved command string, and can deny
regardless of how the call was phrased or what the model was persuaded to try.
A `CLAUDE.md` instruction is advisory — it enters the context and can be argued
with by anything else in the context, including tool output. A settings `deny`
entry is deterministic but pattern-bound: `Bash(terraform apply:*)` misses
`cd infra && terraform apply`, a shell alias, or a wrapper script. Use the deny
rule as a cheap first layer, but the guarantee comes from the hook.

**2.** The copies drift. Someone updates the root, or one nested copy, and now
four files disagree with no precedence rule that resolves it — nested files add
to the root, they do not override it, so contradictory guidance simply coexists
in context. It surfaces as inconsistent behaviour between subdirectories that
nobody can reproduce, because the difference is not in the code being edited but
in which memory files that path happened to load. Two documented mechanisms make
it worse than a plain duplication bug: nested files load only when Claude reads a
file in that subtree, and they are not re-injected after compaction. So the same
session can honour the rule, then stop honouring it, then honour it again, with
no edit to any file. Run `/context` to see what actually loaded.

**3.** Fail-open keeps the session alive: a schema change in the hook payload
does not brick every tool call, and you still have the settings deny list as a
backstop. Fail-closed refuses to guess: if you cannot parse the event you do not
know which tool is being called, so allowing it is a decision made without
information. For a secrets guard, commit to fail-closed. A guard that silently
disarms itself on malformed input is worse than no guard, because you will still
believe you have one. Make the refusal name the file that produced it so the
outage is diagnosable in seconds — `block_secret_reads.py` does this.


**4.** Twelve copies of one convention, which drift the moment anyone edits one
of them, and which load only when Claude happens to read a file in that specific
subtree — so the conventions apply inconsistently and nobody can reproduce why.
Use a single `.claude/rules/testing.md` with `paths: ["**/*.test.tsx"]`, or
whatever the pattern is. The set of files sharing the convention is defined by
name, not by location, and only a glob can say that. Directory-level memory is
the right tool only when the convention really is bound to the directory.

**5.** `context: fork`. The skill runs in an isolated sub-agent context and
returns its result, so the four hundred lines never enter the main conversation.
What it costs is continuity: the forked context is gone afterwards, so anything
the skill discovered and did not put in its output is lost, and a follow-up
question has to be answered by running it again. That makes `fork` right for
"produce a finding" and wrong for "explore with me". If you find yourself
re-invoking a forked skill three times to ask about the same analysis, its output
is too narrow, not its context.

**6.** `-p` (or `--print`) stops the hang, and `--output-format json` with
`--json-schema` makes the findings parseable. What neither addresses is
**precision**: a schema guarantees the shape of a finding and says nothing about
whether it is a real defect, and a review that posts false positives on every PR
gets muted regardless of how well-formed its JSON is. That is a prompt problem —
explicit criteria for what to report and what to skip — and it belongs to D4.

</details>
