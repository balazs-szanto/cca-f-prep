"""
WHAT      Spawn a real external MCP server over stdio, discover its tools for
          zero tokens, then let an agent use only what discovery returned.
WHY       In-process tools (basics/tools.py) are a closed world you control. An
          external server is a separate process speaking a wire protocol, with a
          handshake that can fail, a version that can drift, and a lifetime you
          do not own. Everything here is genuine except the data.
DOMAIN    D2 Tool Design and MCP Integration
TRADEOFF  A separate process buys isolation, language independence and reuse
          across clients. It costs startup latency on every run, a failure
          surface reported as a connection status rather than an exception, and
          a dependency on the client and server agreeing about the interpreter.
ALTERNATIVE  create_sdk_mcp_server for anything only this program will call: it
          runs in-process, needs no handshake, and gives you no way to see what a
          transport failure looks like.

Model: claude-haiku-4-5, max_turns=3. Discovery makes no model call, so the tool
listing below costs nothing to run.

WHAT THIS FILE USED TO DO. It pointed at the canonical filesystem reference
server, spawned over npx - a better illustration of "someone else's server" than
a mock is, and one that never ran in the environment this was written in. The
client declined to attach it and the demo stopped at discovery every time, so it
now points at src/mockserver instead: reproducibility bought at the price of the
"someone else's code" dimension. The refusal detection below is kept from that
version, because a refusal looks the same either way.

One thing that attempt established, and it generalises: from the client side you
cannot tell WHERE an attachment was refused. Ruling out local configuration does
not localise the decision, because the client is told the outcome and never the
reason. Design for the outcome.
"""
import asyncio
import sys
from typing import Any

from claude_agent_sdk import (
    AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, ResultMessage, TextBlock,
)

from playground import teach

MODEL = "claude-haiku-4-5"

# WHY: substrings, not one exact message. The text of a refusal is not part of
# any contract - it varies by client version and by whatever declined the
# attachment - so matching one literal string would make this detector work in
# exactly the environment it was written in and nowhere else.
REFUSAL_HINTS = ("blocked", "refused", "denied", "not allowed", "not permitted")

LESSON = {
    "domain": "D2 Tool Design and MCP Integration",
    "setup": "basics.check_auth passed, and `uv run python -m mockserver` runs by hand - "
             "see src/mockserver/README.md, which costs nothing and shows more "
             "of the protocol than this file does.",
    "run": "uv run python -m playground.run tools_mcp.external_mcp",
    "cost": "free if the server cannot be attached, since it stops before the "
            "model call; 1 model call if it can",
    "expect": "Either a status line and five tool names, followed by an answer "
              "about rmoore's tickets - or, if your setup declines to attach the "
              "server, no status line at all and a KNOWN ISSUE block. Which one "
              "you get is a property of your environment, so check rather than "
              "assume. The agent-run half has never been executed by the author; "
              "its output here is INFERRED.",
    "learn": "Your tool surface is not a constant - it can be narrowed by "
             "configuration you do not control, and that narrowing arrives as an "
             "empty list plus a line on stderr rather than as an exception, so "
             "code that hardcodes tool names cannot tell it apart from a crashed "
             "server.",
}

# WHY: the same paragraph appears at the line where the failure happens, further
# down. Duplicated on purpose - a reader who opens this file at the failure needs
# it there, and a reader who only runs the demo needs it on screen. The rule is
# that these two copies change together.
KNOWN_ISSUE = (
    "What did not work: the MCP handshake never completed, so discovery returned "
    "an empty tool list and the agent run below never started. The server itself "
    "is fine - `uv run python -m mockserver` runs standalone, and driving it by hand "
    "over stdio exercises every tool. What failed is the client's attempt to "
    "attach it. How to find out whether this affects you: run this demo. If you "
    "see a status line and five tool names, it works in your environment and "
    "this block will not print. If you see this block, something between the "
    "client and the server declined the attachment; the line captured from "
    "stderr above is the only diagnostic offered, and from the client side you "
    "cannot tell where the decision was made. Consequence for this repo: every "
    "line below the check that printed this block has never been executed by the "
    "author, so nothing in this repository claims to have observed its output. "
    "In-process tools (create_sdk_mcp_server) are not affected by whatever "
    "governs external ones, which is why permission_gate.py uses one."
)

_notices: list[str] = []


def _watch_stderr(line: str) -> None:
    # WHY: a refused attachment never surfaces as a Python exception. The CLI
    # writes a line to stderr and then reports an empty server list, so without
    # this hook it is indistinguishable from "the server process crashed".
    low = line.lower()
    if "mcp" in low and any(hint in low for hint in REFUSAL_HINTS):
        _notices.append(line.strip())


def server_config() -> dict[str, Any]:
    return {
        "type": "stdio",
        # WHY: sys.executable, not "python". The client spawns this as a bare
        # subprocess with no shell and no venv activation, so a bare "python"
        # would resolve to whatever is first on PATH - very likely an interpreter
        # without mockserver installed. The import would then fail inside a
        # process whose stderr you are not reading, and the symptom would be an
        # empty tool list rather than an error.
        "command": sys.executable,
        "args": ["-m", "mockserver"],
    }


async def discover() -> list[str]:
    """Connect, run the handshake, read the tool list, disconnect. No model call."""
    options = ClaudeAgentOptions(
        model=MODEL, max_turns=1, mcp_servers={"tickets": server_config()},
        # WHY: an empty allowlist is correct here. We are only asking the server
        # what it offers; no tool will be invoked, so nothing needs allowing.
        allowed_tools=[], stderr=_watch_stderr,
    )
    # WHY: entering the context manager performs the MCP handshake but sends no
    # prompt. This is the part worth internalising - your entire tool surface is
    # inspectable for free, before you commit a single token to a run.
    async with ClaudeSDKClient(options=options) as client:
        status = await client.get_mcp_status()

    names: list[str] = []
    for server in status["mcpServers"]:
        print(f"server 'tickets': {server['status']}  error={server.get('error')}")
        info = server.get("serverInfo") or {}
        if info:
            print(f"  serverInfo: {info.get('name')} v{info.get('version')}")
        for tool in server.get("tools", []):
            names.append(f"mcp__tickets__{tool['name']}")
            print(f"  tool: {tool['name']}")
    return names


async def main() -> None:
    teach.banner(LESSON)

    tools = await discover()

    # WHY: three outcomes, kept distinct. Refused, started but empty, and working
    # are different problems with different fixes. Collapsing them into one "it
    # did not work" is what made the npx version of this file so slow to
    # diagnose - the server binary was fine the whole time.
    if _notices:
        # KNOWN ISSUE, and this is the exact line where it happens.
        #
        # What did not work: the MCP handshake never completed, so discovery
        # returned an empty tool list and the agent run below never started. The
        # server itself is fine - `uv run python -m mockserver` runs standalone, and
        # driving it by hand over stdio exercises every tool. What failed is the
        # client's attempt to attach it. How to find out whether this affects
        # you: run this demo. If you see a status line and five tool names, it
        # works in your environment and this block will not print. If you see
        # this block, something between the client and the server declined the
        # attachment; the line captured from stderr above is the only diagnostic
        # offered, and from the client side you cannot tell where the decision
        # was made. Consequence for this repo: every line below the check that
        # printed this block has never been executed by the author, so nothing in
        # this repository claims to have observed its output. In-process tools
        # (create_sdk_mcp_server) are not affected by whatever governs external
        # ones, which is why permission_gate.py uses one.
        print("\nrefusal notice(s) captured from stderr:")
        print("\n".join(f"  {line}" for line in _notices))
        # WHY: known_issue() does not return. Everything below has never executed
        # here, which is why the LESSON says INFERRED instead of describing it.
        teach.known_issue(LESSON, KNOWN_ISSUE)
    if not tools:
        print("\nNo tools and no refusal notice: the server process failed to start.")
        print(f"Check that `{sys.executable} -m mockserver` runs by hand.")
        return

    # WHY: the allowlist is built from what discovery returned, not from names
    # typed against a version of the server that may not be the one running. A
    # renamed tool degrades this into "fewer tools" rather than a broken run.
    options = ClaudeAgentOptions(
        model=MODEL, max_turns=3, mcp_servers={"tickets": server_config()},
        allowed_tools=tools,
        system_prompt="Use the ticket tools. Be brief. Do not guess ticket data.",
    )

    # WHY: everything from here down is code the author has never executed. It is
    # kept, rather than deleted, because the shape of a working external-server
    # run is part of what this file teaches - but nothing in the repo may claim
    # to have observed its output. If it runs for you, you are ahead of the repo.
    print("\n--- agent run ---")
    result: ResultMessage | None = None
    async with ClaudeSDKClient(options=options) as client:
        await client.query(
            "How many tickets are assigned to rmoore, and what is the title of "
            "the highest priority one? Priority 1 is the highest."
        )
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text, end="", flush=True)
            elif isinstance(message, ResultMessage):
                result = message
                print(f"\n\n[{message.subtype}, {message.num_turns} turns]")

    teach.closing(
        LESSON,
        observed=[
            f"Discovery returned {len(tools)} tool name(s) for zero tokens, and "
            f"the allowlist was built from that list rather than typed by hand.",
            f"The agent answered using only those tools, ending "
            f"{result.subtype if result else 'unknown'} - and every one of them "
            f"ran in a separate process speaking JSON-RPC over stdio.",
        ],
        naive="An external server looks like a library with extra steps. The "
              "difference that matters is that a separate process is something "
              "someone else can version, break, or decline to attach - and you "
              "find out at runtime, on their schedule rather than yours.",
    )


if __name__ == "__main__":
    asyncio.run(main())
