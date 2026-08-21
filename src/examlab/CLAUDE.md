# Nested Memory — `src/examlab/`

Rules for code under `src/examlab/` and nowhere else. Read the root `CLAUDE.md`
first; this file adds to it and, in exactly one place, amends it.

## Why this package exists outside `playground/`

`playground/` demonstrates the Claude Agent SDK. This package demonstrates the
layer underneath it — the Messages API request/response cycle the SDK owns on
your behalf. They are separate packages because they answer to different
constraints, and mixing them would quietly weaken the guarantee `playground/`
makes.

Nothing here imports `claude_agent_sdk`. Nothing in `playground/` imports this.
If a demo needs both, it belongs in neither and the design is wrong.

## The one amendment to the root auth rule

The root rule is: never set or reference `ANTHROPIC_API_KEY` anywhere. That rule
exists so that cost is always attributable to one interactive session, and it
stays fully in force for `playground/` — `basics/check_auth.py` still exits 1 if
the variable is set.

Here it is narrowed rather than repealed, and the narrowing has a shape:

- **No module may require a credential.** The default path of every demo runs
  against `ScriptedTransport` and makes no network call. A reader with no key
  sees the whole lesson, including its output.
- **Going live takes a deliberate act, and installing a package is not one.**
  `transport.live()` returns a transport only when `PLAYGROUND_EXAMLAB_LIVE=1`
  *and* `anthropic` is installed *and* that SDK holds a credential of its own.
  Without the flag, `uv sync --extra live` changes nothing — because a reader who
  installs a library out of curiosity must not thereby start spending money.
- **No module names a credential variable.** The client is asked what it
  resolved, through its own attributes; this package reads no key, documents no
  key variable, and cannot be the place one gets committed. `LIVE_FLAG` is this
  repo's own switch and holds no secret.

  This rule used to be stronger — "no module names *any* environment variable" —
  and it was given up on purpose. The first `live()` had three gates and assumed
  `anthropic.Anthropic()` would raise without a credential. It does not
  (MEASURED, anthropic 1.0.0): it constructs, the banner claimed a live run, and
  the demo crashed at request time. A rule that reads well is worth less than a
  fallback that happens, so the rule moved.
- **`anthropic` is an optional dependency, never a runtime one.** It is imported
  lazily inside a `try`, in one function, in one file.
- **A declined live run says why.** `choose()` appends `live()`'s reason to the
  scripted note, because silently falling back is how a reader ends up believing
  the flag worked.

The consequence worth stating: a live run here bills a different credential from
every other measurement in this repo. That is why no number produced by a live
run in this package may be written into `docs/status.md`.

## Provenance labelling, which is stricter here

The root convention is DOCUMENTED / MEASURED / INFERRED. This package adds a
fourth state and needs it:

- **SCRIPTED** — the value came from a response this repo fabricated. It is
  evidence about the *control flow* that consumed it and evidence about nothing
  else. A scripted `stop_reason` proves your loop branches correctly; it proves
  nothing about when a model emits that stop reason.

Never label a scripted output MEASURED. That is the specific dishonesty this
package is most exposed to, because the output looks identical either way.

## Domain numbering

The whole repo uses the official CCA-F blueprint numbering, so there is nothing
special about this package's `DOMAIN` lines and no local rule to remember. See
`docs/domain-map.md` for the blueprint table.

**This section used to say the opposite, and the history is worth one paragraph.**
When this package was written, `playground/` still carried labels invented before
the official guide was reachable, and only two of the five numbers coincided. The
convention then was that a `DOMAIN` line here always said "Official" and one in
`playground/` never did — a marker that worked and that nobody should have had to
learn. The relabel on 2026-08-21 made it redundant, so the word "Official" came
out of every `DOMAIN` line in this package on the same commit. A convention whose
only job is to warn you about an inconsistency should be deleted the moment the
inconsistency is, or it starts implying one that no longer exists.

## Rules for modules here

- A module prints a transcript, not a result. The reader is learning a control
  flow, so the sequence of requests and responses *is* the output.
- State which transport produced the output, every run, unasked.
- Anti-patterns are shown as code that runs and then fails, with the failure
  printed. An anti-pattern described in a comment is a claim; one that runs and
  breaks is a demonstration.
- Register the module in `DEMOS` in **`playground/run.py`**, below the
  `BOUNDARY` key, and give its `LESSON` a `domain` field. There is one registry
  for the whole repo; this package deliberately has no dispatcher of its own, and
  `__main__.py` is a signpost that says so. An unregistered file is invisible in
  `--list` and absent from `docs/lessons.md`.
- That registry is in a package this one must not import, and does not: it
  resolves modules by name through `lessons.module_of()`, `runpy` and
  `find_spec`, none of which bind the module. If you find yourself adding
  `import examlab` to `playground/`, the design has gone wrong.
