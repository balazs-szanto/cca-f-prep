# D4 — Prompt Engineering and Structured Output

## The concept

This domain is two subjects the official blueprint deliberately joins, and the
join is the insight. **Prompt engineering** decides what the model attends to;
**structured output** decides what shape its answer arrives in. Neither
substitutes for the other, and most production failures come from expecting one
to do the other's job.

The three mechanisms, in increasing strength and decreasing generality:

1. **Instructions.** Free text. Infinitely flexible and enforced by nothing. A
   vague instruction fails silently; so does a good one, occasionally.
2. **Examples.** Still free text, and stronger than instructions for the same
   token cost, because they demonstrate a judgement rather than describing one.
   Two to four examples that show *why the alternative was rejected* generalise
   to cases you never enumerated. Ten examples of the same reasoning do not.
3. **A schema, delivered as a tool.** `tool_use` with a JSON schema, plus a
   `tool_choice` that forces that tool. This is the only mechanism here with a
   guarantee attached, and the guarantee is narrow: **the shape is legal.** It
   says nothing about whether the values are true, whether two fields agree, or
   whether a value the source never contained is absent.

The most useful way to hold the domain is a ladder of what each layer catches:

| Layer | Catches | Cannot catch |
|-------|---------|--------------|
| Vague instruction plus a confidence hedge | very little | almost everything |
| Explicit categorical criteria | out-of-scope findings, in both directions | a misreading of the input |
| Few-shot examples | cases no category named | a judgement you never demonstrated |
| Schema / `strict` | wrong types, unknown keys, bad enum values | every question of meaning |
| Cross-field validation | totals that disagree, unfilled escape hatches | a self-consistent extraction of the wrong numbers |
| Comparison against the source | dropped and invented values | nothing — but downstream rarely has the source |
| A human | the residue | scale |

Two consequences worth stating plainly, because they are the ones that get
skipped. **Retry is a layer too, and it has a failure mode nobody expects**: ask
again for information the source does not contain and the model does not refuse,
it invents something that passes every check you have. And **latency is part of
the output contract**: the Message Batches API halves the cost and gives up the
latency guarantee, which makes it correct for an overnight report and unusable
for anything a person is waiting on, at any discount.

## Where it lives in this repo

Read in this order.

| Run | What it settles |
|-----|-----------------|
| `examlab.review_criteria` | Whether "be conservative" improves precision. It does not — 25% to 80% comes from the categorical list, and the few-shot arm is the only one that reaches a defect no category named. One false positive survives all three prompts, on purpose. |
| `basics.structured` | `output_format` in the Agent SDK enforces the shape of an answer and *only* the shape. The keywords you would reach for to constrain a value are accepted and ignored. |
| `examlab.structured_output` | The same idea at request level, where the schema is a tool's `input_schema`. Includes an extraction that passes the schema, passes the cross-field check, and is wrong about money. |
| `examlab.validation_retry` | Which validation failures another attempt actually fixes, and the one where it fabricates instead of failing. |
| `examlab.batches` | The four properties of batching, and the arithmetic that decides whether the 50% is available to you at all. |
| `basics.prompt_shape` | Filed here on the domain's name. Its subject — instruction/data delimiting against injection — matches none of this domain's task statements, and the blueprint does not test it. Worth running anyway; it is a worked null result. |

Design notes that carry across all of them:

- **Nullable over required.** A required field with no source value leaves the
  model one legal move, which is to invent one. `structured_output.py` shows the
  invention happening under a field that was already nullable, which is the
  next lesson: the type permits absence, and the *description* is what asks for
  it.
- **`enum` plus an `"other"` escape hatch plus a detail string.** Extensible
  categorisation without forcing a wrong choice. And add `"unclear"` — a model
  with no way to say "I could not tell" will pick something.
- **Ask for the same number twice.** `stated_total` next to `calculated_total`
  turns a silent arithmetic error into a visible disagreement, for the cost of
  one field. It is the cheapest semantic guard in the domain.

## Common trap

Reading "tool use eliminates JSON errors" as "tool use eliminates errors". It is
true and it is much narrower than it sounds: what is eliminated is the class of
failure where the response will not parse. What remains is every failure where it
parses perfectly and says something false — line items that do not sum, a value
in the wrong field, a date read from the wrong row, a currency nobody printed.

The trap has a second half, which is that the eliminated class was the *visible*
one. Before a schema, malformed output announced itself with a parse exception at
the boundary. After a schema, the same underlying confusion arrives as a
well-formed record that flows straight into a database. The failure did not go
away; it stopped being loud. That is a good trade only if you added the semantic
checks with the same commit.

## Scenario questions

1. Your extraction pipeline reports 97% accuracy and your manager wants to drop
   the human review step. What do you compute before answering, and what would
   make you say no?

2. A reviewer bot has good precision on security findings and terrible precision
   on "unclear naming". Developers have started ignoring all of its comments.
   What do you do this week, and what do you do after?

3. You add `strict: true` to every extraction tool and the JSON parse errors go
   to zero. Two weeks later finance reports that some invoice totals are wrong.
   Explain how both facts can be true, and name the two fields you would add.

4. Your team wants to move a blocking pre-merge check and an overnight technical
   debt report to the Message Batches API for the 50% saving. What do you do with
   each, and what is the arithmetic you show for the one you keep?

<details>
<summary>Answers</summary>

**1.** Split the accuracy by document type and by field, separately, before
anything else — an aggregate is a weighted mean, so a segment that is a quarter
of the volume can sit at 60% while the mean reads well above it, and the two
segmentations fail independently. Then check where the errors sit on the
confidence distribution. `examlab.confidence_routing` is this question with the
numbers filled in: two of its three errors are at 0.96 confidence or above, so
the band you were about to stop reviewing is where the errors are. Say no if any
segment is materially worse than the aggregate, or if confidence and correctness
turn out to be weakly related — and if you do automate, route on segment as well
as confidence, because segment membership is known *before* the extraction and
confidence only after.

**2.** This week: turn the naming category off and keep the rest. The dismissals
do not stay contained to the bad category — a reviewer distrusted on one is
skimmed past on all of them, so you are losing the good security findings to
protect a category that is not working. After: rewrite the naming criterion as
something categorical rather than a confidence hedge, and add two or three
few-shot examples that show an acceptable name beside a genuinely bad one *with
the reasoning*, then re-enable it behind a comparison against the old rate. Note
what is not on the list: instructing it to "only report high-confidence naming
issues", which is the change that feels like a fix and moves nothing.

**3.** Both are true because they are claims about different things. `strict`
constrains sampling to a grammar built from your schema, so the output is always
schema-valid — that removes syntax errors and every one of them was a *visible*
failure at the parse boundary. It does not constrain meaning, so a dropped VAT
line still produces a perfectly well-formed record with a smaller total, and that
one flows into the ledger silently. The two fields: `calculated_total` alongside
the extracted `stated_total`, so the sum can be compared against the claim; and a
`conflict_detected` boolean for source documents that disagree with themselves.
Then validate the pair host-side — the schema cannot express a relationship
between two of its own fields.

**4.** Batch the overnight report; keep the pre-merge check synchronous. The
processing window is *up to 24 hours* with no latency SLA, and "usually faster"
is not something you may design a blocking check around — a developer is waiting.
The arithmetic for the one you batch is worst-case turnaround: your submission
gap plus the processing bound. With a 24-hour bound and a 30-hour promise
downstream, the mathematical limit is a 6-hour submission window, and you pick 4
so there is margin for retrieval, the downstream write, and the resubmission of
anything that failed — which needs a whole second window. Also note what
disqualifies batching for agent work entirely: no multi-turn tool calling within
a request, so a loop cannot be batched, only its individual single-turn calls.

</details>
