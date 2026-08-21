# D1 — Agentic Architecture and Orchestration

## The concept

Orchestration is one question: who owns control flow. In a workflow your code
owns it. You decide what runs, in what order, and what happens on failure; the
model is called as a function and never sees the shape of the job. In an agent
the model owns it. You hand over a goal and a set of tools, and it decides how
many steps to take and in what order.

Most systems are neither, and the useful skill is deciding where the line falls
inside one system rather than picking a side for all of it.

## Start here: a decomposition that works

`orchestration/triage.py` is the worked example, and everything else on this page
is a refinement of it. It answers support requests in three stages:

| Stage | Question it answers | Capability it gets |
|-------|--------------------|--------------------|
| 1 | Is this well-formed and about something real? | None — a regex and a dict lookup |
| 2 | What kind of request is it? | One model call, a closed enum, **no tools** |
| 3 | What is actually true about this ticket? | One model call, **exactly one tool** |

The design rule it demonstrates:

> **Give each stage exactly the capability its question needs, and escalate only
> when the previous stage has proved the escalation necessary.**

The boundaries fall where the *kind* of question changes — decidable by rule,
decidable from the text in front of you, decidable only by going and looking —
not where the subject matter changes. That is the part worth taking away. "This
is a different topic" is not a reason to split. "This needs a different kind of
answering" always is.

Two consequences follow, and neither was designed in separately:

**Cost falls out of the shape.** MEASURED: four requests cost five model calls
where an unconditional pipeline would have made eight. Nobody optimised that. A
malformed request is rejected for nothing, and a request that stage 2 fully
answers never reaches stage 3.

**Unpredictability concentrates where the capability is.** MEASURED across two
runs: stages 1 and 2 produced identical results both times; stage 3 did not, and
once declined to use its tool at all. A regex cannot change its mind, and a
closed vocabulary bounds how far a classification can drift. The stage the
pipeline works hardest to avoid reaching is also the least reliable one — which
is the argument for the whole structure, stated by the structure itself.

## Refinement 1: the cheap side is not automatically cheap

Having split the work, the next question is how coarsely to batch it — and the
usual framing gets this backwards. It says workflows are cheap and predictable
while agents are expensive and flexible. Half of that is wrong. Predictability is
real and is the main thing you buy. Cheapness is not: every call re-pays a fixed
overhead for the system prompt, tool schemas and harness, so a workflow that fans
a small job into many calls can easily cost more than one agent call doing the
same work. `workflow_vs_agent.py` measures exactly this, reproducibly, and the
workflow loses on price while winning on control.

So the decision is not "is my system mature enough for an agent". It is: can I
write down every step in advance? If yes, write them down. If the steps depend on
what earlier steps found, you are describing an agent whether or not you call it
one. Batch granularity, not the label, drives the bill.

## Refinement 2: delegation is priced per hand-off

`subagent.py` measures the other axis. A subagent's product is a clean context
window, and on a task with nothing bulky to isolate you pay a round trip and a
second system prompt for isolation you had no use for.

## Where it lives in this repo

- `src/playground/orchestration/triage.py` — the positive reference: a three-stage
  decomposition, with the reasoning for each boundary written at the boundary.
- `src/playground/orchestration/workflow_vs_agent.py` — the same classification
  task both ways, with turns, tokens, cache, latency and cost side by side.
- `src/playground/orchestration/subagent.py` — delegation measured on a task too
  small to justify it, so the overhead is visible rather than asserted.
- `src/examlab/agentic_loop.py` and `loop_antipatterns.py` — task statement 1.1,
  the loop itself. `query()` owns termination, so the Agent SDK demos above
  cannot show `stop_reason`; these do, against a fabricated transport.
- `src/examlab/chaining.py` — 1.6. A fixed chain against a plan that decides its
  own steps, with the request sizes each one actually built.
- `src/playground/reliability/session_resume.py` and `session_fork.py` — 1.7.
  They live in `reliability/` because they are one subject with each other, and
  they are D1 because the blueprint puts session state here. `session_fork`
  tests three separate isolation claims: what a fork inherits, what it hides
  from its sibling, and whether it writes back into its parent.

## Common trap

Reaching for a subagent because the task has parts. A subagent's product is a
clean context window: it reads a lot and returns a little, so the parent never
pays for the intermediate tokens. If the sub-task has nothing bulky to read, you
are paying a round trip and a second system prompt for isolation you do not
need. Delegate when the sub-task's intermediate output is both large and
disposable — a log trawl, a many-file search. Not when it is merely separate.

## Scenario questions

1. A nightly job classifies 5,000 support tickets. Someone proposes replacing the
   per-ticket loop with a single agent run that classifies all of them, citing
   the measurement in `workflow_vs_agent.py`. What do you say?

2. Your agent handles refunds. Ninety percent of requests are standard and
   fully specifiable; ten percent involve partial shipments and need judgement.
   Sketch the shape you would build and say what you gave up.

3. A team reports their subagent architecture is slower and more expensive than
   the monolith it replaced, but "it is better separated". What single measurement
   would you ask for first, and what would each outcome tell you?

<details>
<summary>Answers</summary>

**1.** The measurement does not generalise to 5,000 tickets. It shows per-call
overhead dominating when the work per call is tiny — three short tickets. At
5,000 the binding constraints are different: the context window (all tickets
cannot fit), failure isolation (one bad ticket must not poison the batch), and
retry granularity. The right answer is batching, not agent-vs-workflow: keep the
workflow, but classify N tickets per call instead of one, and tune N against the
window. That captures the overhead saving the measurement actually demonstrates
without giving up per-batch error isolation.

**2.** A workflow with an agentic escape hatch. Script the ninety percent as
deterministic steps with a structured output and a validation check. Route to an
agent only when an input fails a precondition — multiple shipments, mismatched
totals, anything the schema cannot express. What you give up is uniformity: you
now have two paths to test, two cost profiles, and a routing rule that itself can
be wrong. You also give up a single audit trail, since the two paths produce
different evidence of what happened.

**3.** Ask for the token counts of what each subagent *read* versus what it
*returned*. That ratio is the entire case for delegation. If subagents read a lot
and return a little, the architecture is sound and the slowdown is a latency
problem — parallelise the calls. If they read and return similar amounts, there
is nothing to isolate and you are paying round trips for organisational tidiness;
the separation belongs in your code, not in the agent topology.

</details>
