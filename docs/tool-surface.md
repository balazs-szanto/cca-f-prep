# Tool surface

Every page in the official tool-use documentation set, what it covers, and
whether this repo can demonstrate it. A reader should be able to tell from this
page alone which features exist, which this repo shows you, and why those two
lists are not the same.

All pages under `https://platform.claude.com/docs/en/agents-and-tools/tool-use/`,
**fetched 2026-08-20**. Where a claim comes from a page and not from a run here,
it is labelled **DOCUMENTED** and is not narrated as if it had been observed.

## The boundary, stated once

This repo runs on an interactive Claude Code session over subscription OAuth,
through the Claude Agent SDK. The SDK manages the agent loop for you — it builds
the requests, runs the tool round trip, and hands you messages. In exchange it
does not expose the per-request controls the Messages API has. There is no
`tool_choice`, no `strict`, no `cache_control`, no `defer_loading`, no
`allowed_callers`, no `eager_input_streaming` anywhere in `ClaudeAgentOptions`,
in `@tool`, or in `create_sdk_mcp_server`.

That is not a gap in this repo. It is the trade the Agent SDK makes, and it is
the single most useful thing on this page: **if a feature is configured by a
field on a Messages API request or on a tool definition, you cannot reach it
from here, and no amount of SDK configuration will get you to it.**

Eleven of the twenty-four pages below are in that category — see the counts
correction under [Buckets](#buckets). They are documented here and demonstrated
against the real API nowhere, deliberately. Adding `anthropic` as a hard
dependency and an API key would reach them and would break
[the auth rule](../CLAUDE.md); writing code that cannot be run here would be
worse, because it would look tested.

The canonical shape of what is out of reach is the client round trip on the
[overview page]: `client.messages.create(...)` with `tools=[...]` and
`tool_choice={"type": "auto", "disable_parallel_tool_use": True}`, then a second
call carrying an explicit `tool_result` block back. The Agent SDK does all of
that for you and never shows you the seam.

### What `src/examlab/` changed about this, and what it did not

That seam is now written out in full in
[`examlab/agentic_loop.py`](../src/examlab/agentic_loop.py), and `tool_choice` in
[`examlab/tool_choice.py`](../src/examlab/tool_choice.py) — as runnable code,
with the request contract enforced by
[`examlab/contract.py`](../src/examlab/contract.py) rather than by an API. The
compromise it found is a third option the paragraph above did not consider: code
that runs, builds and validates real requests, and consumes **fabricated**
responses labelled `SCRIPTED`.

**No row below moves to COVERED because of it.** COVERED in this table means
"the behaviour was observed here", and a response this repo wrote is not an
observation of anything. What `examlab/` buys is the request side — which is the
half you are responsible for, and the half a live call would not have taught any
better. What it cannot buy is any claim about when a model emits a given
`stop_reason`, how often `strict` prevents a malformed input, or whether the
documented contract in `contract.py` is complete. Those stay open.

Pages whose *client-side mechanics* are now readable, with their bucket
unchanged: `overview`, `how-tool-use-works`, `define-tools` (the `tool_choice`
half), `handle-tool-calls`, `strict-tool-use` (discussed, not exercised).

## Buckets

| Bucket | Meaning |
|--------|---------|
| **COVERED** | Demonstrated here. The file is named. |
| **OBSERVABLE** | The behaviour can be watched from the Agent SDK on OAuth, even where the API-level control cannot be set. |
| **API-ONLY** | Needs the Messages API and an API key. Documented, never faked. |
| **CONCEPTUAL** | No useful demo. Documentation only. |

Counts: **6 COVERED, 2 OBSERVABLE, 11 API-ONLY, 5 CONCEPTUAL** — 24 rows.

> **Counts correction, 2026-08-21.** This line previously read "7 COVERED, 2
> OBSERVABLE, 10 API-ONLY, 5 CONCEPTUAL", and two other places on this page said
> "nine" API-ONLY pages. All three were wrong, in the direction that flatters the
> repo: one COVERED row too many, one API-ONLY row too few, and a third figure
> that matched neither. The total, 24, was right throughout, which is exactly why
> nobody noticed — the sum checked out against the page count while its parts did
> not. Counted by grep against the bucket column, not by hand. There is a script
> that stops this happening in `docs/status.md`
> (`scripts/check_caveat_accounting.py`) and none that does it for this page;
> that asymmetry is now the most likely place for the next error of this kind.

Three of the COVERED rows became so during an earlier round; before it they were
OBSERVABLE.
`web-fetch-tool` moved the other way, from OBSERVABLE to API-ONLY, once it was
established that Claude Code's `WebFetch` is not the server tool of that name —
see finding 1. A row moving toward *less* coverage is the kind of correction
this page exists to make.

## The pages

| Page | Bucket | What it covers | Where it is here, or why it is not |
|------|--------|----------------|-------------------------------------|
| `overview` | CONCEPTUAL | Map of tool use; client vs server execution; the pricing table. | Its concepts land in the rows below. Its one hard number is quoted under [Token costs](#token-costs). |
| `how-tool-use-works` | COVERED | Where tools run, the agentic loop, `stop_reason: tool_use`. | [`tools_mcp/where_code_runs.py`](../src/playground/tools_mcp/where_code_runs.py) for the execution boundary; [`basics/tools.py`](../src/playground/basics/tools.py) for the loop. |
| `define-tools` | COVERED | Tool schemas, descriptions, `tool_choice`. | [`tools_mcp/schema_design.py`](../src/playground/tools_mcp/schema_design.py). `tool_choice` and `input_examples` on that page are API-ONLY. |
| `handle-tool-calls` | COVERED | Parsing `tool_use`, formatting `tool_result`, `is_error`. | [`basics/tools.py`](../src/playground/basics/tools.py) and [`reliability/error_taxonomy.py`](../src/playground/reliability/error_taxonomy.py). The SDK owns the loop, so the raw block formatting never surfaces. |
| `parallel-tool-use` | COVERED | Several `tool_use` blocks in one turn; `disable_parallel_tool_use`. | [`tools_mcp/parallel_tools.py`](../src/playground/tools_mcp/parallel_tools.py), which returned a null result on grouping and a real one on timing. The switch is API-ONLY. |
| `tool-runner` | CONCEPTUAL | An Anthropic-SDK helper that runs the tool loop for you. | Nothing to port: the Agent SDK already runs that loop. Porting it would misrepresent both. |
| `strict-tool-use` | API-ONLY | `strict: true` constrains sampling to schema-valid tool inputs. | `strict` is a property on a Messages API tool definition. `@tool` has no slot for it. |
| `server-tools` | COVERED | `server_tool_use` blocks, `pause_turn`, mixed server/client turns. | [`tools_mcp/where_code_runs.py`](../src/playground/tools_mcp/where_code_runs.py), with the finding below. `pause_turn` is handled inside the harness and never reaches you. |
| `web-search-tool` | OBSERVABLE | Live web results with citations. | Genuinely reachable: Claude Code's `WebSearch` built-in **is** this server tool, documented as running "against Anthropic's web search backend" — see finding 1. `max_uses`, `user_location` and `response_inclusion` remain API-ONLY; `allowed_domains` and `blocked_domains` are exposed through the built-in. |
| `web-fetch-tool` | API-ONLY | Retrieves a named URL or PDF, server-side. | **Not** reachable, despite the name. Claude Code's `WebFetch` is a different, CLI-executed tool that fetches and summarises locally — see the near miss in finding 1. Reclassified from OBSERVABLE once that was established. |
| `code-execution-tool` | API-ONLY | Python and bash in an Anthropic-hosted sandbox. | `code_execution_*` is an entry in the Messages API `tools` array. No `ClaudeAgentOptions` field enables it. |
| `advisor-tool` | API-ONLY | A faster executor model consults a stronger advisor mid-generation. | Beta header `advisor-tool-2026-03-01`. Note: `"advisor"` *is* in the SDK's `ServerToolName` literal, so the block type is defined — nothing in the options turns the tool on. |
| `tool-search-tool` | API-ONLY | Search a large tool catalogue and load definitions on demand. | Driven entirely by `defer_loading` on tool definitions. Same note: the regex and bm25 names appear in `ServerToolName` and are unreachable from options. |
| `memory-tool` | API-ONLY | `/memories` file commands that **you** execute. | Do not confuse this with the Agent SDK's memory. `CLAUDE.md` and `AgentDefinition.memory` are a different mechanism with a different contract; treating them as the same thing is the error this table exists to prevent. |
| `bash-tool` | API-ONLY | Anthropic-schema `bash_20250124`, executed by your application. | Claude Code ships a `Bash` built-in that shares the concept and not the contract — the CLI executes it, and its schema is not this one. |
| `text-editor-tool` | API-ONLY | Anthropic-schema `text_editor_20250728`, executed by your application. | Same reasoning against Claude Code's Read/Edit/Write. |
| `computer-use-tool` | API-ONLY | Screenshots plus mouse and keyboard control. | Beta header plus a desktop harness this repo does not have. |
| `troubleshooting-tool-use` | CONCEPTUAL | Symptom-to-fix tables. | Two of its rows are recorded here as measurements: "Claude never calls your tool" and parameter guessing, both in [`traps.md`](traps.md). Note the URL is `troubleshooting-tool-use`, not `troubleshooting`. |
| `tool-reference` | CONCEPTUAL | Directory of tool types and optional properties. | It is the spine of the two tables below. |
| `manage-tool-context` | COVERED | Four ways to stop tool definitions eating the window. | [`tools_mcp/tool_overhead.py`](../src/playground/tools_mcp/tool_overhead.py) prices the premise. The four remedies — tool search, programmatic tool calling, prompt caching placement, context editing — are all API-ONLY. |
| `tool-combinations` | CONCEPTUAL | Recipes pairing Anthropic-provided tools. | Every pairing it names is built from API-ONLY tools. |
| `tool-use-with-prompt-caching` | OBSERVABLE | Where to put `cache_control`; what invalidates the cache. | The cache split is visible in `usage` and printed by [`basics/hello.py`](../src/playground/basics/hello.py). Placement is API-ONLY. |
| `programmatic-tool-calling` | API-ONLY | Claude writes code that calls your tools inside the sandbox. | Requires `code_execution` plus `allowed_callers`. |
| `fine-grained-tool-streaming` | API-ONLY | Stream tool input without server-side buffering or validation. | `eager_input_streaming` is a per-tool Messages API field. The SDK's `include_partial_messages` is a different mechanism and is not this. |

## Tool definition properties

**DOCUMENTED**, from `tool-reference`, fetched 2026-08-20. **None of these six is
settable from the Claude Agent SDK.** They are listed because knowing they exist
is what stops you from concluding that a schema is all a tool definition can
carry.

| Property | What it is for | Available on |
|----------|----------------|--------------|
| `cache_control` | Sets a prompt-cache breakpoint at this tool. Put it on the **last** tool in the array and the whole tool prefix caches. | All tools |
| `strict` | Guarantees the tool name and input match your JSON Schema, by constraining sampling to a grammar. Removes the validate-and-retry step. | All tools except `mcp_toolset` |
| `defer_loading` | Keeps the tool out of the system-prompt prefix until tool search returns a `tool_reference` for it. This is what makes a large catalogue affordable, and it preserves the prompt cache because the prefix is untouched. | All tools |
| `allowed_callers` | Restricts who may call the tool: `"direct"` (the model, in a `tool_use` block) or `"code_execution_20260120"` (code inside the sandbox). Defaults to `["direct"]` when omitted. | All tools except `mcp_toolset` |
| `input_examples` | Schema-valid example inputs, included in the prompt beside the schema. For tools with nested or format-sensitive parameters. Costs roughly 20–50 tokens for a simple example, 100–200 for a complex one. | User-defined and Anthropic-schema client tools. **Not** server tools |
| `eager_input_streaming` | Streams a tool's input as it is generated, with no server-side buffering or JSON validation — so you may receive partial or invalid JSON and must guard the parse. Replaces the legacy `fine-grained-tool-streaming-2025-05-14` beta header. | User-defined tools only |

Two interactions worth knowing, both DOCUMENTED:

- `defer_loading: true` and `cache_control` on the same tool is a **400**. Put
  the breakpoint on a non-deferred tool.
- `defer_loading` and `strict` compose. The grammar is built from the full
  toolset regardless of what is deferred, so no recompilation happens when a
  tool is discovered.

## Anthropic-provided tools

**DOCUMENTED**, from `tool-reference`, fetched 2026-08-20. Server tools execute
on Anthropic's infrastructure; client tools have an Anthropic-published schema
that **your** application executes.

| Tool | `type` | Execution | Status |
|------|--------|-----------|--------|
| Web search | `web_search_20260318`, `web_search_20260209`, `web_search_20250305` | Server | GA |
| Web fetch | `web_fetch_20260318`, `web_fetch_20260309`, `web_fetch_20260209`, `web_fetch_20250910` | Server | GA |
| Code execution | `code_execution_20260521`, `code_execution_20260120`, `code_execution_20250825` | Server | GA |
| Advisor | `advisor_20260301` | Server | Beta: `advisor-tool-2026-03-01` |
| Tool search | `tool_search_tool_regex_20251119`, `tool_search_tool_bm25_20251119` | Server | GA |
| MCP connector | `mcp_toolset` | Server | Beta: `mcp-client-2025-11-20` |
| Memory | `memory_20250818` | Client | GA |
| Bash | `bash_20250124` | Client | GA |
| Text editor | `text_editor_20250728`, `text_editor_20250124` | Client | GA |
| Computer use | `computer_20251124`, `computer_20250124` | Client | Beta: `computer-use-2025-11-24`, `computer-use-2025-01-24` |

## Token costs

**DOCUMENTED**, from `overview`, fetched 2026-08-20. Adding `tools` makes the API
construct a tool-use system prompt, and its size depends on `tool_choice`:

| Model | `auto` / `none` | `any` / `tool` |
|-------|-----------------|----------------|
| Claude Opus 5 | 286 | 406 |
| Claude Sonnet 5 | 354 | 474 |
| Claude Haiku 4.5 | 496 | 588 |

Forcing a tool call therefore costs roughly 120 extra tokens per turn on Opus 5,
before any of your own definitions are counted. **This cannot be reproduced
here** — `tool_choice` is a Messages API request parameter with no
`ClaudeAgentOptions` equivalent.

Also DOCUMENTED: web search is billed per search on top of tokens; web fetch adds
no charge beyond the tokens the fetched content occupies. Absolute currency
figures are deliberately not repeated in this repo, per [CLAUDE.md](../CLAUDE.md).

## What this repo measured that the documentation does not say

Four findings from this round, all **MEASURED** here on 2026-08-20 unless marked
otherwise. They are recorded because each one contradicts a reasonable reading of
the documentation.

1. **The client/server distinction is real, and it is not visible in the SDK's
   block stream.** Claude Code's `WebSearch` fetched live pages and cited
   sources, and every block arrived as `ToolUseBlock(WebSearch)` — the same class
   as an in-process MCP tool. No `ServerToolUseBlock` appeared, although the SDK
   defines that class and its `ServerToolName` literal names `web_search`.
   See [`where_code_runs.py`](../src/playground/tools_mcp/where_code_runs.py).

   **A correction, because this finding was first written up with the wrong
   explanation.** The original text inferred that `WebSearch` was probably
   implemented and executed by the CLI, which would have made both arms of that
   demo client-side and the comparison worthless. That inference is **false**,
   and the question is now DOCUMENTED. From
   <https://code.claude.com/docs/en/tools-reference>, "WebSearch tool behavior",
   fetched 2026-08-20:

   - "WebSearch runs a query against Anthropic's **web search** backend and
     returns result titles and URLs" — where "web search" links to
     `platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool`,
     the Messages API server tool.
   - "The tool may issue up to eight backend searches per call, refining the
     search internally before returning results" — the server-side loop that
     `server-tools` describes.
   - "Claude can scope results with `allowed_domains` … or `blocked_domains`.
     The two lists can't be combined in a single call" — the Messages API tool's
     own fields, with its own documented mutual-exclusion rule.
   - "Amazon Bedrock doesn't expose **the server-side web search tool**", and on
     Foundry, Azure-hosted "deployments don't support server-side tools, so the
     WebSearch call fails." That availability matrix matches the Messages API
     page exactly, which says web search is unavailable on Bedrock and needs a
     Hosted-on-Anthropic deployment on Foundry.

   So the search really did execute on Anthropic's infrastructure, and the SDK
   still reported a plain `ToolUseBlock`. The conclusion is stronger than the
   inference was: the block type does not carry the execution boundary, and the
   only thing that separates the two cases from here is whether your own handler
   was invoked.

   **The near miss.** `WebFetch` is *not* a server tool, and had the demo used it
   the framing would have collapsed. The same page describes WebFetch fetching
   the page itself, converting HTML to Markdown locally, running "a small, fast
   model" over the content so "Claude receives that model's answer, not the raw
   page", setting a `User-Agent` beginning with `Claude-User`, and caching each
   response for 15 minutes under `CLAUDE_CODE_WEBFETCH_CACHE_TTL_MS`. Two
   adjacent built-ins with near-identical names sit on opposite sides of the line
   the demo is about, and it picked the right one for the wrong reason.

   **A silent failure the same page documents**, and the reason `where_code_runs`
   asserts a tool was called at all: a session may make at most 200 `WebSearch`
   calls, and past the cap "a capped call appears in the conversation as a search
   that did nothing." No error, no exception, nothing in the block stream — the
   same shape as the declined-tool trap in [`traps.md`](traps.md).

2. **A tool definition costs about 221 tokens, resident, called or not**, plus
   about 5 tokens of fixed overhead per in-process MCP server — measured across
   1, 2, 4 and 8 tools, linear to the token, and re-measured on 2026-08-21 with
   the same result to the token.
   See [`tool_overhead.py`](../src/playground/tools_mcp/tool_overhead.py).

   **The built-in figure in this finding was wrong within a day, and the
   correction is the more useful half.** It read "roughly 11,000 tokens above a
   no-tools session" when first measured on 2026-08-20. Re-run on 2026-08-21 on
   the same machine against the same pinned `uv.lock`, the `claude_code` toolset
   rested at **16,579 total, +14,146 above baseline** — about a quarter more —
   and its breakdown now names a `Skills` category the earlier one did not.
   Nothing in this repo changed; the harness did.

   So the two halves of that demo have different shelf lives. The cost of *your*
   tool definitions was stable to the token across a version bump. The cost of
   *the platform's* moved 25% in a day. A number of the second kind is a
   measurement, not a constant, and a budget built on one needs re-measuring
   rather than citing. The *deferred* category — listed but excluded from the
   total — is still there and still the trap it was.

3. **`get_context_usage()` under-reports MCP tools until the handshake is
   forced**, and the settling is a race rather than a fixed number of steps. Read
   at connect time it returned a clean, plausible, correctly formatted number
   that omitted every MCP tool. Poll until the reading stops moving before you
   trust it. Same file.

4. **Parallel tool use produced a null result on grouping and a real one on
   timing.** No `AssistantMessage` in either arm carried two `ToolUseBlock`s, so
   on that signal the independent and dependent questions look identical. The
   clock disagreed by about a hundred to one: 15 ms of idle between the
   independent pair against 1,285 ms between the dependent pair — and a model
   round trip is not 15 ms. **INFERRED**, unsettleable here: the independent pair
   was probably requested in one response and delivered as two messages.
   See [`parallel_tools.py`](../src/playground/tools_mcp/parallel_tools.py).

## What is still not covered

Honest gaps, so that nobody reads the COVERED column as completeness:

- Everything in the API-ONLY bucket. Eleven pages, documented above,
  demonstrated against the real API nowhere. Five of them have their client-side
  mechanics readable in `src/examlab/` against a fabricated transport, which is
  not the same thing and is not counted as coverage here.
- `pause_turn` and the server-side loop. The harness handles them; this repo has
  never seen one.
- Mixed server-and-client turns, where a `server_tool_use` block arrives without
  its result and waits on your `tool_result`. Not reachable without server tools.
- `ServerToolUseBlock` itself. It has never been observed here, and finding 1
  now shows that a genuinely server-executed tool does not produce one through
  the Agent SDK, so it is unclear whether a Claude Code session can emit one at
  all. That question is open and this repo cannot settle it.

[overview page]: https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
