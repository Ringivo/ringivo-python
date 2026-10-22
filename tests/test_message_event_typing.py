# pyright: reportUnnecessaryTypeIgnoreComment=true
"""The message event variants, as the type checker sees them.

CI runs pyright over this file, so the `assert_type()` calls are checks:
each one fails pyright if a check on `event.type`, `isinstance()` or a
`match` statement stops narrowing to the variant this file says. At run
time `assert_type()` does nothing, so the same functions also run below
against parsed bodies, to prove the runtime takes the branch the checker
expects.

`_reads_pyright_must_refuse()` is never called. Each line in it reads a
member the variant does not have, and carries a `# pyright: ignore[...]`.
The comment at the top of this file makes an ignore that suppresses
nothing an error, so the day one of those reads type-checks — the day a
received text has a `sent_by` again — pyright fails here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

import pytest
from typing_extensions import assert_never, assert_type

from ringivo import (
    FailureCause,
    InboundMessageEvent,
    InboundMessageEventData,
    MessageEvent,
    MessageFailedEvent,
    MessageFailedEventData,
    MessageSender,
    OutboundMessageEvent,
    OutboundMessageEventData,
    UnknownMessageEvent,
    webhooks,
)

_Event = InboundMessageEvent | OutboundMessageEvent | MessageFailedEvent | UnknownMessageEvent

_RECEIVED: dict[str, Any] = {"type": "message.received", "data": {"id": "a"}}
_SENT: dict[str, Any] = {"type": "message.sent", "data": {"id": "b"}}
_FAILED: dict[str, Any] = {
    "type": "message.failed",
    "data": {"id": "c", "failure": {"cause": "opted_out"}},
}
_OTHER: dict[str, Any] = {"type": "fax.delivered", "data": {"id": "d"}}


def test_the_parser_returns_the_message_event_union() -> None:
    assert_type(webhooks.parse_message_event(_SENT), MessageEvent)
    assert_type(webhooks.parse_message_event(_SENT), _Event)


def _route_on_type(event: _Event) -> str:
    if event.type == "message.received":
        assert_type(event, InboundMessageEvent)
        assert_type(event.message, InboundMessageEventData)
        assert_type(event.message.received_at, datetime | None)
        return "inbound"
    if event.type is None:
        assert_type(event, UnknownMessageEvent)
        return "unknown"
    if event.type == "message.failed":
        assert_type(event, MessageFailedEvent)
        assert_type(event.message, MessageFailedEventData)
        assert_type(event.message.sent_by, MessageSender | None)
        assert_type(event.message.failure_cause, FailureCause | str | None)
        return "failed"
    assert_type(event, OutboundMessageEvent)
    assert_type(event.type, Literal["message.sent", "message.delivered"])
    assert_type(event.message, OutboundMessageEventData)
    assert_type(event.message.sent_by, MessageSender | None)
    return "outbound"


def _route_on_isinstance(event: _Event) -> str:
    if isinstance(event, InboundMessageEvent):
        assert_type(event.type, Literal["message.received"])
        return "inbound"
    if isinstance(event, OutboundMessageEvent):
        assert_type(event.message, OutboundMessageEventData)
        return "outbound"
    if isinstance(event, MessageFailedEvent):
        assert_type(event.type, Literal["message.failed"])
        return "failed"
    assert_type(event, UnknownMessageEvent)
    assert_type(event.type, None)
    return "unknown"


def _route_on_match(event: _Event) -> str:
    match event:
        case InboundMessageEvent(message=message):
            assert_type(message, InboundMessageEventData)
            return "inbound"
        case MessageFailedEvent(message=message):
            assert_type(message.failure_cause, FailureCause | str | None)
            return "failed"
        case OutboundMessageEvent(message=message):
            assert_type(message, OutboundMessageEventData)
            return "outbound"
        case UnknownMessageEvent():
            return "unknown"
        case _:
            assert_never(event)


@pytest.mark.parametrize(
    ("payload", "on_type", "on_isinstance", "on_match"),
    [
        (_RECEIVED, "inbound", "inbound", "inbound"),
        (_SENT, "outbound", "outbound", "outbound"),
        (_FAILED, "failed", "failed", "failed"),
        (_OTHER, "unknown", "unknown", "unknown"),
        (None, "unknown", "unknown", "unknown"),
    ],
)
def test_the_runtime_takes_the_branch_the_checker_narrows_to(
    payload: Any, on_type: str, on_isinstance: str, on_match: str
) -> None:
    event = webhooks.parse_message_event(payload)

    assert _route_on_type(event) == on_type
    assert _route_on_isinstance(event) == on_isinstance
    assert _route_on_match(event) == on_match


def test_a_known_failure_cause_is_a_failure_cause_literal() -> None:
    cause: FailureCause = "opted_out"
    event = webhooks.parse_message_event(_FAILED)

    assert isinstance(event, MessageFailedEvent)
    assert event.message.failure_cause == cause


def _reads_pyright_must_refuse(event: _Event) -> None:
    """Never called: see the module docstring."""
    _ = event.message  # pyright: ignore[reportAttributeAccessIssue]

    if isinstance(event, InboundMessageEvent):
        _ = event.message.sent_by  # pyright: ignore[reportAttributeAccessIssue]
        _ = event.message.source  # pyright: ignore[reportAttributeAccessIssue]
        _ = event.message.status  # pyright: ignore[reportAttributeAccessIssue]
        _ = event.message.sent_at  # pyright: ignore[reportAttributeAccessIssue]
        _ = event.message.provider_message_id  # pyright: ignore[reportAttributeAccessIssue]
        _ = event.message.failure_cause  # pyright: ignore[reportAttributeAccessIssue]
    elif isinstance(event, OutboundMessageEvent):
        _ = event.message.received_at  # pyright: ignore[reportAttributeAccessIssue]
        _ = event.message.failure_cause  # pyright: ignore[reportAttributeAccessIssue]
    elif isinstance(event, MessageFailedEvent):
        _ = event.message.received_at  # pyright: ignore[reportAttributeAccessIssue]
    else:
        _ = event.message  # pyright: ignore[reportAttributeAccessIssue]

    not_a_known_cause: FailureCause = "a_cause_added_later"  # pyright: ignore[reportAssignmentType]
    del not_a_known_cause
