# Nested Memory — `src/playground/`

This file exists to demonstrate memory hierarchy. The rules below apply to code
under `src/playground/` and nowhere else — but read "When this file is actually
in context" before treating any of them as guaranteed to be loaded.

## How this file relates to the root `CLAUDE.md`

Claude Code walks up from the working directory collecting `CLAUDE.md` files, so
a file deeper in the tree is read *in addition to* the root one, not instead of
it. The root sets project-wide rules (auth, line limits, docstring shape); this
file adds rules that only make sense once you are writing demo modules.

Practical consequence: do not restate root rules here. Duplicated guidance drifts
apart, and when it does, nobody knows which copy is authoritative. If a rule
belongs to the whole project, it goes in the root file and is deleted from here.

## When this file is actually in context

Confirmed against <https://code.claude.com/docs/en/memory> on 2026-08-20, and
worth knowing before you rely on anything below.

**It loads lazily.** Ancestor files "are loaded in full at launch"; files in
subdirectories "load on demand when Claude reads files in those directories". So
this file is absent from context until Claude touches something under
`src/playground/`. Ask a question about the repo before opening any file here and
the root `CLAUDE.md` answers alone.

**It does not survive compaction.** The root file does — after `/compact` Claude
re-reads it from disk and re-injects it. Nested files and path-scoped rules "are
not re-injected automatically; they reload the next time Claude reads a file in
that subdirectory". In a long session, a rule written here silently stops
applying at the compaction boundary and comes back only on the next read.

The practical consequence for this repo: nested memory is the right place for
guidance that is *cheap to re-derive from the code beside it*, and the wrong
place for a rule that must hold across a whole session. Anything in the second
category belongs in the root file, which is where the auth rule and the line
limit live. Run `/context` to see which memory files a session actually loaded.

## Rules for demo modules

- A demo prints something a reader can interpret without opening the source. A
  demo that only proves "no exception was raised" teaches nothing.
- State the model in the docstring, and pass it explicitly in `ClaudeAgentOptions`.
  Relying on the CLI default makes a demo's cost unpredictable.
- Set `max_turns` explicitly. Unset means no limit at all — that is the
  documented default, not a large number — so an open-ended prompt runs until the
  model decides to stop, which in a study repo means burning quota while you are
  reading something else.
- Prefer one clear failure over a silent fallback. These files are read to learn
  what breaks, so swallowing an error destroys the lesson.

## Registering a demo

Every module must be added to `DEMOS` in `run.py`. It is a hand-maintained dict,
so a file that is not registered is effectively invisible.
