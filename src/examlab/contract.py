"""
WHAT      The request contract: what a content block is, how to read one, how to
          build a `tool_result`, and the four rules that make a `messages` array
          legal. No transport, no I/O.
WHY       Split out of `transport.py`, which went ten lines over the cap. The
          split is not arithmetic - these are two subjects. The contract answers
          "is this conversation well-formed", which is true or false regardless
          of whether anything is ever sent; the transport answers "how does it
          get sent". Keeping them together meant the validator read as a feature
          of the mock, and the validator is the part that transfers to real code.
DOMAIN    D1 Agentic Architecture and Orchestration (27%), task
          statement 1.1
TRADEOFF  These rules are DOCUMENTED from the tool-use pages and no 400 from the
          real API has been observed here to confirm any one of them. So the
          validator can be wrong in the direction of strictness: if a live run
          succeeds where this raises, this file is what is wrong, and it should
          be corrected here rather than worked around at the call site.
ALTERNATIVE  Let the API be the validator - send it and read the 400. Cheaper to
          write, and it needs a credential and a round trip to tell you
          something that is decidable locally in forty lines.

Not a demo, so no LESSON block. Makes no model call and no network call.
"""
from __future__ import annotations

from typing import Any

Block = dict[str, Any]
Message = dict[str, Any]
Response = dict[str, Any]


class TransportError(RuntimeError):
    """A request the real API would have rejected, raised where you can see it.

    Named for the transport rather than the contract, and it lives here anyway,
    because the contract is what decides that a request is invalid - every
    transport merely reports it. Deliberately not a subclass of anything the
    demos catch by accident: when this is raised the lesson is the traceback.
    """


def blocks_of(message: Message | Response) -> list[Block]:
    """Content blocks of a message, normalising the string shorthand.

    The API accepts `content` as a bare string or as a list of blocks, and every
    rule below is written against blocks. Normalising here rather than at each
    call site is the difference between four checks and twelve.
    """
    content = message.get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return list(content or [])


def tool_uses(source: Message | Response) -> list[Block]:
    """Every `tool_use` block, in order. Empty list if the turn asked for none."""
    return [b for b in blocks_of(source) if b.get("type") == "tool_use"]


def text_of(source: Message | Response) -> str:
    """Concatenated text blocks. Empty string on a pure tool-use turn.

    Note what this being empty means: a turn that only asks for tools carries no
    prose at all. Treating "there is text" as "the model is finished" is one of
    the three anti-patterns the blueprint names, and this function returning ""
    is where that mistake first becomes visible. See loop_antipatterns.py.
    """
    return "".join(b.get("text", "") for b in blocks_of(source)
                   if b.get("type") == "text")


def tool_result(tool_use_id: str, content: Any, *, is_error: bool = False) -> Block:
    """The block that carries a tool's output back to the model.

    `is_error` is the failure channel: the call still returns a result block, the
    turn still continues, and the model reads the content to decide what to do
    next. It is not an exception and it does not end anything - which is why a
    tool can report a policy refusal in a form the model can explain to a user.
    See tool_errors.py for what belongs in the content beside it.
    """
    block: Block = {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content if isinstance(content, str) else str(content),
    }
    if is_error:
        block["is_error"] = True
    return block


def validate_conversation(messages: list[Message]) -> None:
    """Raise TransportError if the real API would reject this `messages` array.

    Four rules, all DOCUMENTED, in order of how often they are got wrong:

    1. Every `tool_use` in an assistant turn must be answered, by id, in the
       very next message, which must have role `user`. Not two messages later,
       not in the same assistant turn.
    2. Every `tool_result` must name an id that was actually issued. A
       fabricated or stale `tool_use_id` is not ignored.
    3. All pending ids must be answered together. A turn that requests three
       tools and gets two results back is rejected - you cannot answer them one
       request at a time.
    4. Roles alternate, starting with `user`. Two assistant messages in a row is
       an error, which is what makes "append the result to history" mean "append
       a *user* message", not "append to the assistant's".
    """
    if not messages:
        raise TransportError("empty messages array")

    expected = "user"
    pending: list[str] = []
    for index, message in enumerate(messages):
        role = message.get("role")
        if role != expected:
            raise TransportError(
                f"messages[{index}]: role is {role!r}, expected {expected!r}. "
                f"Roles must alternate starting with 'user' (rule 4).")
        expected = "assistant" if role == "user" else "user"

        answered = [b.get("tool_use_id") for b in blocks_of(message)
                    if b.get("type") == "tool_result"]
        if answered and role != "user":
            raise TransportError(
                f"messages[{index}]: tool_result blocks in an assistant turn. "
                f"Results are carried by the user role (rule 4).")

        unknown = [i for i in answered if i not in pending]
        if unknown:
            raise TransportError(
                f"messages[{index}]: tool_result for id(s) {unknown} that no "
                f"preceding turn requested (rule 2).")
        missing = [i for i in pending if i not in answered]
        if pending and not answered:
            # WHY split from the partial case below: they are different
            # mistakes. Nothing answered means the loop treated a tool_use turn
            # as final - a termination-condition bug. A partial answer means the
            # loop is fine and the fan-out handling is not.
            raise TransportError(
                f"messages[{index}]: the previous turn requested {pending} and "
                f"this message answers none of them. A tool_use turn must be "
                f"followed immediately by its results (rule 1).")
        if missing:
            raise TransportError(
                f"messages[{index}]: {len(missing)} of {len(pending)} pending "
                f"tool_use id(s) unanswered: {missing} (rule 3).")
        pending = [b["id"] for b in tool_uses(message)] if role == "assistant" else []

    if pending:
        raise TransportError(
            f"conversation ends with {len(pending)} unanswered tool_use id(s): "
            f"{pending}. The model is waiting on a result (rule 1).")
