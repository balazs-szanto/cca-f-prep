# D2 — Claude Code Configuration and Workflows

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
- `.claude/commands/drill.md` — a custom slash command, `/drill d4`.
- `src/playground/run.py` — one dispatcher so every demo has a single entry point.

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

</details>
