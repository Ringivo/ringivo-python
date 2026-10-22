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
from typing import Any, Literal, get_args, get_type_hints

import pytest
from typing_extensions import assert_never, assert_type

from ringivo import (
    FailureCause,
    MessageDeliveredEvent,
    MessageEvent,
    MessageFailedEvent,
    MessageFailedEventData,
    MessageReceivedEvent,
    MessageReceivedEventData,
    MessageSender,
    MessageSentEvent,
    OutboundMessageEventData,
    UnknownMessageEvent,
    webhooks,
)

_Event = (
    MessageReceivedEvent
    | MessageSentEvent
    | MessageDeliveredEvent
    | MessageFailedEvent
    | UnknownMessageEvent
)

_RECEIVED: dict[str, Any] = {"type": "message.received", "data": {"id": "a"}}
_SENT: dict[str, Any] = {"type": "message.sent", "data": {"id": "b"}}
_DELIVERED: dict[str, Any] = {"type": "message.delivered", "data": {"id": "b"}}
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
        assert_type(event, MessageReceivedEvent)
        assert_type(event.message, MessageReceivedEventData)
        assert_type(event.message.received_at, datetime | None)
        return "received"
    if event.type == "message.sent":
        assert_type(event, MessageSentEvent)
        assert_type(event.message, OutboundMessageEventData)
        assert_type(event.message.sent_by, MessageSender | None)
        return "sent"
    if event.type == "message.delivered":
        assert_type(event, MessageDeliveredEvent)
        assert_type(event.message, OutboundMessageEventData)
        return "delivered"
    if event.type == "message.failed":
        assert_type(event, MessageFailedEvent)
        assert_type(event.message, MessageFailedEventData)
        assert_type(event.message.sent_by, MessageSender | None)
        assert_type(event.message.failure_cause, FailureCause | str | None)
        return "failed"
    assert_type(event, UnknownMessageEvent)
    assert_type(event.type, None)
    return "unknown"


def _route_on_isinstance(event: _Event) -> str:
    if isinstance(event, MessageReceivedEvent):
        assert_type(event.type, Literal["message.received"])
        return "received"
    if isinstance(event, MessageSentEvent):
        assert_type(event.type, Literal["message.sent"])
        return "sent"
    if isinstance(event, MessageDeliveredEvent):
        assert_type(event.type, Literal["message.delivered"])
        return "delivered"
    if isinstance(event, MessageFailedEvent):
        assert_type(event.type, Literal["message.failed"])
        return "failed"
    assert_type(event, UnknownMessageEvent)
    return "unknown"


def _route_on_match(event: _Event) -> str:
    match event:
        case MessageReceivedEvent(message=message):
            assert_type(message, MessageReceivedEventData)
            return "received"
        case MessageSentEvent(message=message) | MessageDeliveredEvent(message=message):
            assert_type(message, OutboundMessageEventData)
            return "sent or delivered"
        case MessageFailedEvent(message=message):
            assert_type(message.failure_cause, FailureCause | str | None)
            return "failed"
        case UnknownMessageEvent():
            return "unknown"
        case _:
            assert_never(event)


@pytest.mark.parametrize(
    ("payload", "on_type", "on_isinstance", "on_match"),
    [
        (_RECEIVED, "received", "received", "received"),
        (_SENT, "sent", "sent", "sent or delivered"),
        (_DELIVERED, "delivered", "delivered", "sent or delivered"),
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


def test_failure_causes_is_typed_as_the_literal() -> None:
    """Pins the `Literal` on `FAILURE_CAUSES` for pyright. `frozenset[str]`
    would fail both `assert_type()` calls."""
    assert_type(webhooks.FAILURE_CAUSES, frozenset[FailureCause])
    for cause in webhooks.FAILURE_CAUSES:
        assert_type(cause, FailureCause)


def test_the_failure_cause_field_keeps_the_literal_in_its_annotation() -> None:
    """Pins the `Literal` on the field at run time. Pyright reads
    `FailureCause | str | None` as `str | None`, so an `assert_type()` on the
    field passes even when the annotation is plain `str | None`. The
    annotation itself still carries the `Literal`, and this checks it.
    """
    hint = get_type_hints(MessageFailedEventData)["failure_cause"]

    assert set(get_args(hint)) == {FailureCause, str, type(None)}


def _reads_pyright_must_refuse(event: _Event) -> None:
    """Never called: see the module docstring."""
    _ = event.message  # pyright: ignore[reportAttributeAccessIssue]

    if isinstance(event, MessageReceivedEvent):
        _ = event.message.sent_by  # pyright: ignore[reportAttributeAccessIssue]
        _ = event.message.source  # pyright: ignore[reportAttributeAccessIssue]
        _ = event.message.status  # pyright: ignore[reportAttributeAccessIssue]
        _ = event.message.sent_at  # pyright: ignore[reportAttributeAccessIssue]
        _ = event.message.provider_message_id  # pyright: ignore[reportAttributeAccessIssue]
        _ = event.message.failure_cause  # pyright: ignore[reportAttributeAccessIssue]
        for item in event.message.media:
            _ = item.encoding  # pyright: ignore[reportAttributeAccessIssue]
            _ = item.byte_size  # pyright: ignore[reportAttributeAccessIssue]
    elif isinstance(event, (MessageSentEvent, MessageDeliveredEvent)):
        _ = event.message.received_at  # pyright: ignore[reportAttributeAccessIssue]
        _ = event.message.failure_cause  # pyright: ignore[reportAttributeAccessIssue]
        for item in event.message.media:
            # A media item sent from your number has no filename.
            _ = item.filename  # pyright: ignore[reportAttributeAccessIssue]
    elif isinstance(event, MessageFailedEvent):
        _ = event.message.received_at  # pyright: ignore[reportAttributeAccessIssue]
    else:
        _ = event.message  # pyright: ignore[reportAttributeAccessIssue]

    not_a_known_cause: FailureCause = "a_cause_added_later"  # pyright: ignore[reportAssignmentType]
    del not_a_known_cause
    retired_cause: FailureCause = "outcome_unknown"  # pyright: ignore[reportAssignmentType]
    del retired_cause
