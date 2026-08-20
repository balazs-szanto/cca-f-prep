# Domain map — PROVISIONAL

**This repo's domain labels are not verified against an official source. Do not
rely on them.**

## What was attempted

The goal was to replace this repo's invented labels with the official exam
domains, taken from the official exam guide and nothing else. Third-party
preparation sites, unofficial study guides and blog posts were explicitly ruled
out as sources, so none of them were used, and none should be used to "fix" this
file later.

Attempted on 2026-08-20:

| Source | Result |
|--------|--------|
| Anthropic's certification announcement | Describes the Architect credential as covering "integration architecture, governance, and evaluation". No numbered domains, no weightings. |
| Claude Academy resource listing | No certification exam guide or syllabus present. |
| Anthropic's exam delivery partner page | Registration and scheduling only. No content outline. |
| The certification landing page | Redirects to an authenticated location; returns HTTP 403 without a session. |

The official exam guides are described as downloadable from the Partner Academy
certifications page, which requires membership of the Claude Partner Network and
an authenticated session. That is not reachable from here, and guessing at its
contents from secondary sources is exactly what this file exists to avoid.

**Conclusion: no official enumeration was obtained. The map below stays
provisional and no `LESSON` field or `docs/dN-*.md` filename was relabelled.**
Relabelling against an unverified map would have produced a repo that looks
authoritative and is not, which is worse than one that is visibly unlabelled.

## The labels this repo actually uses

These are the author's, not Anthropic's. They are internally consistent and
externally unverified.

| Label | Used for | Files |
|-------|----------|-------|
| D0 Foundations | Auth, the message stream, structured output, the tool mechanism | `basics/` |
| D1 Agentic Architecture and Orchestration | Who owns control flow; delegation | `orchestration/` |
| D2 Claude Code Configuration and Workflows | Memory, settings, hooks, slash commands | `.claude/`, `run.py`, `teach.py`, `lessons.py` |
| D3 Prompt Engineering | Prompt construction | `basics/prompt_shape.py` |
| D4 Tool Design and MCP Integration | Schemas, transports, permission gating | `tools_mcp/`, `src/mockserver/` |
| D5 Context Management and Reliability | Context accounting, resumption, failure classification | `reliability/` |

## Two domains have no domain doc

`docs/` carries `d1`, `d2`, `d4` and `d5`. There is **no `d0-*.md` and no
`d3-*.md`**, so for those two the module docstrings and `LESSON` blocks are the
only material. `.claude/commands/drill.md` accepts `d0` and `d3` and says the
same thing. This is a gap, not an oversight to be papered over by writing two
documents against a numbering that is itself unverified — writing `docs/d3-*.md`
would give the label an authority it has not earned.

## The known defect in this map

There was no D3 at all until this round, and structured output was filed under
"D0 Foundations". Those two facts are related: `basics/structured.py` is about
*constraining a response format*, which is a different subject from *constructing
a prompt*, and filing the first under a general-purpose bucket is what made the
absence of the second invisible.

`basics/prompt_shape.py` now occupies D3 and is genuinely about prompt
construction. `structured.py` has deliberately **not** been moved into it, for
the reason above — output shaping is not prompt engineering, and merging them
would recreate the confusion in the opposite direction.

"D0 Foundations" remains the weakest label here. It is a bucket, not a domain,
and it holds four files that have little in common beyond being read first. If an
official enumeration ever becomes available, that is the label most likely to
dissolve into two or three real ones.

## If you can reach the official guide

Do this, in order:

1. Replace the table above with the official domains verbatim, including their
   weightings.
2. Update the `domain` field in each module's `LESSON` block. That field is the
   single source of truth — `docs/lessons.md` is generated from it, so do not
   edit that file by hand.
3. Rename `docs/dN-*.md` to match, and fix the cross-references in `README.md`
   and `.claude/commands/drill.md`, which names the domains it will quiz on.
4. Report any demo whose content does not fit the domain it lands in. That
   mismatch is a finding about the repo, not about the exam.
5. Delete this warning and the attempt log above.
