---
description: Quiz me on one official CCA-F domain using only the files in this repository
---

Drill me on domain: **$1**.

Valid values are `d1`, `d2`, `d3`, `d4`, `d5`, or `all`. These are the **official**
CCA-F blueprint domains, and every `DOMAIN` line and `LESSON` domain field in the
repo now uses the same numbering — see `docs/domain-map.md` for the blueprint
table and for the earlier labels these replaced.

| $1 | Weight | Read these |
|----|--------|------------|
| `d1` | 27% | `docs/d1-orchestration.md`, `src/playground/orchestration/`, `src/playground/basics/hello.py`, `src/examlab/agentic_loop.py`, `src/examlab/loop_antipatterns.py`, `src/examlab/chaining.py` |
| `d2` | 18% | `docs/d2-tools-mcp.md`, `src/playground/tools_mcp/`, `src/playground/basics/tools.py`, `src/mockserver/`, `src/examlab/tool_choice.py`, `src/examlab/tool_errors.py` |
| `d3` | 20% | `docs/d3-claude-code.md`, `.claude/`, both `CLAUDE.md` files, `src/playground/basics/check_auth.py` |
| `d4` | 20% | `src/playground/basics/prompt_shape.py`, `src/playground/basics/structured.py`, `src/examlab/structured_output.py`, `src/examlab/validation_retry.py`, `src/examlab/batches.py` |
| `d5` | 15% | `docs/d5-reliability.md`, `src/playground/reliability/` |

`d4` has no `docs/dN-*.md` file — read the module docstrings and `LESSON` blocks
directly. That gap is recorded in `docs/status.md` rather than papered over.

Rules for this drill:

1. Read the files listed for the domain. Use only what is in this repository. If
   the docs and the code disagree, say so - that disagreement is more valuable
   than a clean answer.
2. Ask me **one scenario question at a time**. Wait for my answer before asking
   the next. Do not print the answer with the question.
3. Score each answer as correct, partially correct, or wrong, and say which file
   and line range settles it so I can go read it.
4. Favour tradeoff questions over recall questions. "Which is faster" is a bad
   question; "you have a 40-turn agent that keeps losing early context, what do
   you change first and what does it cost you" is a good one.
5. After three questions, stop and give me a one-paragraph read on where my
   understanding is thin.
6. Claims in this repo are labelled DOCUMENTED, MEASURED, INFERRED or SCRIPTED in
   place. Do not quiz me on anything labelled INFERRED, or on either side of a
   conflict the repo says is unresolved - tell me it is unsettled instead. A
   SCRIPTED value is fair game as evidence about control flow and is never
   evidence about model behaviour; if a question would need the second, say so.

Do not make model calls or run any demo during the drill. This is a reading
exercise.
