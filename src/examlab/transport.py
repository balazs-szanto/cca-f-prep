"""
WHAT      Two ways to send a request - the real Messages API if a credential
          happens to be resolvable, a fabricated response script otherwise -
          plus the note each one obliges a demo to print.
WHY       The demos here are about control flow: when do you send another
          request, what goes in it, when do you stop. That flow is identical
          whether the response came over the wire or out of a list, so binding
          the lesson to a live call would make it unrunnable for no gain. The
          scripted path is worth having because it validates: a mock that only
          replays is theatre, and one that refuses a malformed conversation is
          the grader for the exercise.
DOMAIN    D1 Agentic Architecture and Orchestration (27%)
TRADEOFF  Both transports normalise to plain dicts, so nothing downstream ever
          sees the `anthropic` SDK's typed objects. That keeps the scripted and
          live paths interchangeable, and it means this package teaches the wire
          shape rather than that library's API - useful for the exam, one step
          removed from what you would write against the library itself.
ALTERNATIVE  Record real responses once and replay the recordings. Strictly
          better evidence, and it needs a credential to produce them plus a
          policy for the transcripts, which is a second problem. The scripts
          here are hand-written and every demo says so.

The request contract and its validator live in `contract.py`; this file is only
the plumbing. SCRIPTED is a provenance label introduced by this package - see
CLAUDE.md beside this file. No module here may present a scripted value as a
measurement.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from examlab.contract import Block, Response, TransportError, validate_conversation

# WHY an opt-in flag and not just "is the package installed": installing a
# library must not start spending money. Without this, `uv sync --extra live` -
# a command a reader might run out of curiosity - would silently turn eight free
# demos into paid ones for anyone who happens to have a credential configured
# for something else. The name is this repo's own and holds no secret; it is the
# same shape as PLAYGROUND_ALLOW_ANY_AUTH in basics/check_auth.py.
LIVE_FLAG = "PLAYGROUND_EXAMLAB_LIVE"

# WHY: one string, printed by every demo, rather than a sentence each module
# writes its own way. The claim is identical in all of them, and the moment it is
# paraphrased per file the weakest paraphrase becomes the one a reader remembers.
SCRIPTED_NOTE = (
    "TRANSPORT: scripted. No network call was made. The requests below are the "
    "ones your code really built and the validator really checked; the "
    "responses are fabricated by this repo. Provenance of anything downstream "
    "of a response is SCRIPTED, never MEASURED."
)
LIVE_NOTE = (
    "TRANSPORT: live Messages API. Responses came from the model, so they may "
    "differ from the commentary below, which was written against the script. "
    "Where they disagree, the run is right and the prose is stale."
)


@dataclass
class ScriptedTransport:
    """Replays a fixed list of responses, validating each request first.

    `requests` keeps every request it was handed, so a demo can print what the
    loop actually sent - which is the half of the exchange a live transport makes
    hardest to see.
    """

    script: list[Response]
    requests: list[dict[str, Any]] = field(default_factory=list)
    label: str = "scripted"

    def create(self, **request: Any) -> Response:
        validate_conversation(request.get("messages", []))
        self.requests.append(request)
        if len(self.requests) > len(self.script):
            # WHY: an explicit failure, not a repeated last response. A loop with
            # a broken termination condition would otherwise spin on the same
            # canned answer forever and look like it was working.
            raise TransportError(
                f"the loop sent request {len(self.requests)} but the script has "
                f"only {len(self.script)}. Either the termination condition is "
                f"wrong or the script is short - check stop_reason handling "
                f"before lengthening the script.")
        return self.script[len(self.requests) - 1]


@dataclass
class LiveTransport:
    """Thin adapter over `anthropic`'s client, normalised to plain dicts.

    Everything downstream reads `response["stop_reason"]` and
    `response["content"]`, so both transports must hand back the same shape.
    Returning the SDK's typed objects here would make the scripted path the odd
    one out and push `if hasattr(...)` into every demo.
    """

    client: Any
    label: str = "live"

    def create(self, **request: Any) -> Response:
        validate_conversation(request.get("messages", []))
        return self.client.messages.create(**request).model_dump()


def live() -> tuple[LiveTransport | None, str]:
    """A live transport if one is both asked for and possible, plus the reason
    when it is not. Never raises.

    Four gates, in cost order: the opt-in flag, the optional package, whether the
    client constructs, and whether that client actually holds a credential.

    **The fourth gate exists because of a bug this function shipped with.** The
    first version had three gates and assumed `anthropic.Anthropic()` would raise
    without a credential. **MEASURED, 2026-08-21, anthropic 1.0.0: it does not.**
    It constructs cleanly, `live()` returned a `LiveTransport`, the banner claimed
    a live run, and the demo crashed at request time - so a reader who installed
    the extra without a credential got a traceback where this package promises a
    scripted fallback. Found by running the path rather than by reading it, which
    is the only reason it was found at all.

    WHY this still names no *credential* variable: the client is asked what it
    resolved, through its own attributes. `LIVE_FLAG` is this repo's own switch
    and holds no secret. So the auth rule's substance holds - nothing here reads
    or documents a key - while the earlier and stronger claim, that this file
    names no environment variable at all, does not. That claim was worth giving
    up to stop promising a fallback that did not happen.
    """
    if os.environ.get(LIVE_FLAG) != "1":
        return None, f"{LIVE_FLAG} is not set to 1, so no live run was attempted."
    try:
        import anthropic  # noqa: PLC0415 - lazy on purpose; optional dependency
    except ImportError:
        return None, (f"{LIVE_FLAG} is set but `anthropic` is not installed. "
                      f"Install it with: uv sync --extra live")
    try:
        client = anthropic.Anthropic()
    except Exception as exc:
        # WHY broad: "malformed credential" and "this SDK version raises
        # something else" have the same correct response - fall back and name it.
        return None, (f"{LIVE_FLAG} is set but the anthropic client would not "
                      f"construct ({type(exc).__name__}).")
    if not (getattr(client, "api_key", None) or getattr(client, "auth_token", None)):
        return None, (f"{LIVE_FLAG} is set and `anthropic` is installed, but that "
                      f"SDK resolved no credential of its own. Falling back now "
                      f"rather than failing at request time.")
    return LiveTransport(client), ""


def choose(script: list[Response]) -> tuple[Any, str]:
    """The transport a demo should use, plus the note it must print.

    Live wins when available, because a reader who set the flag and configured a
    credential asked for the real thing. The note is returned rather than printed
    so the caller decides where in its banner it goes - and so that a demo cannot
    obtain a transport without also obtaining the sentence that discloses it.

    When live is declined, `live()`'s reason is appended to the scripted note.
    Silently falling back is how a reader ends up believing the flag worked.
    """
    transport, reason = live()
    if transport is not None:
        return transport, LIVE_NOTE
    return ScriptedTransport(script), f"{SCRIPTED_NOTE} {reason}".strip()


def response(
    *,
    stop_reason: str,
    content: list[Block],
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> Response:
    """Build one fabricated response. Keyword-only, so a script reads as a table.

    `stop_reason` first because it is the field the loop branches on, and a
    script whose stop reasons are hard to scan is a script whose lesson is hidden.
    """
    return {
        "id": f"msg_scripted_{abs(hash((stop_reason, len(content)))) % 10**6:06d}",
        "role": "assistant",
        "model": "scripted",
        "stop_reason": stop_reason,
        "content": content,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }
