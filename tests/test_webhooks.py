"""Webhook signature verification, from the receiver's side.

THE REFUSALS ARE THE TESTS. Every accept case here passes against a
`verify()` that returns None unconditionally, so the ones that carry weight
are the four negatives — a tampered body, a stale timestamp, the wrong
secret, and a malformed header — plus the cross-implementation vector, which
no implementation in this repository produced.

The vector is the point of the exercise. A port that agreed only with its
own tests would pass while signing something subtly different — the
timestamp outside the MAC, a re-encoded body, uppercase hex — and the first
real delivery would be rejected. tests/fixtures/webhook-signature-vector.json
was computed by the server's own signer, and it is committed into the
TypeScript client and asserted in the server's own test suite too.
"""

from __future__ import annotations

import dataclasses
import hashlib
import hmac
import json
import re
import time
from collections.abc import Iterator, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, get_args

import pytest

import ringivo
from ringivo import (
    FailureCause,
    InboundMessageMediaItem,
    MessageDeliveredEvent,
    MessageEvent,
    MessageFailedEvent,
    MessageFailedEventData,
    MessageReceivedEvent,
    MessageReceivedEventData,
    MessageSentEvent,
    OutboundMessageEventData,
    OutboundMessageMediaItem,
    SignatureVerificationError,
    UnknownMessageEvent,
    models,
    webhooks,
)

VECTOR: dict[str, Any] = json.loads(
    (Path(__file__).parent / "fixtures" / "webhook-signature-vector.json").read_text()
)


def _sign(body: bytes, secret: str, timestamp: int) -> str:
    """The published recipe, recomputed here rather than imported.

    Calling the implementation would make these tests agree with whatever
    it does. Written out, they agree with what the documentation SAYS.
    """
    return hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()


def _header(body: bytes, secrets: list[str], timestamp: int) -> str:
    parts = [f"t={timestamp}"]
    parts += [f"v1={_sign(body, secret, timestamp)}" for secret in secrets]
    return ",".join(parts)


BODY = b'{"event_id":"0198b0f8-0000-7000-8000-000000000001","type":"fax.delivered"}'
SECRET = "whsec_ZmFrZXNlY3JldGZvcnRlc3RzMDEyMzQ1Njc4OWFiY2Rl"
OTHER_SECRET = "whsec_b3RoZXJzZWNyZXRmb3J0ZXN0czAxMjM0NTY3ODlhYmM"
NOW = 1755331200


# -- the cross-implementation vector ---------------------------------------


def test_the_servers_own_vector_verifies_here() -> None:
    # The whole reason this file exists. Nothing in this repository computed
    # this header — if the port drifts by one byte, this is what says so.
    webhooks.verify(
        VECTOR["body"].encode(),
        VECTOR["header"],
        VECTOR["secret"],
        now=VECTOR["timestamp"],
    )


def test_the_vector_matches_the_published_recipe_independently() -> None:
    # Proves the fixture is a real MAC and not a string copied out of an
    # implementation: recomputed here from the documented recipe alone.
    recomputed = _sign(VECTOR["body"].encode(), VECTOR["secret"], VECTOR["timestamp"])

    assert recomputed == VECTOR["expected_v1"]
    assert VECTOR["header"] == f"t={VECTOR['timestamp']},v1={VECTOR['expected_v1']}"
    assert VECTOR["secret"].startswith("whsec_")


def test_the_vectors_body_is_verified_as_the_raw_bytes_it_arrived_as() -> None:
    # The commonest integration mistake with signatures of this shape:
    # parsing the JSON and re-encoding it before verifying. Key order,
    # spacing and escaping are free choices no two encoders make alike, so
    # the re-encoded body must NOT verify — and it must not verify quietly.
    reencoded = json.dumps(json.loads(VECTOR["body"])).encode()

    assert reencoded != VECTOR["body"].encode()

    with pytest.raises(SignatureVerificationError):
        webhooks.verify(reencoded, VECTOR["header"], VECTOR["secret"], now=VECTOR["timestamp"])


# -- the refusals ----------------------------------------------------------


def test_a_tampered_body_is_refused() -> None:
    header = _header(BODY, [SECRET], NOW)
    tampered = BODY.replace(b"fax.delivered", b"fax.cancelled")

    assert tampered != BODY

    with pytest.raises(SignatureVerificationError):
        webhooks.verify(tampered, header, SECRET, now=NOW)


def test_a_stale_timestamp_is_refused_in_either_direction() -> None:
    # A replay: a genuine body with its genuine header, sent again later.
    # The MAC still matches — it always will — so the window is the only
    # thing that refuses it. Both directions, because a clock ahead of ours
    # is as suspicious as one behind.
    header = _header(BODY, [SECRET], NOW)

    webhooks.verify(BODY, header, SECRET, now=NOW + 299)

    with pytest.raises(SignatureVerificationError):
        webhooks.verify(BODY, header, SECRET, now=NOW + 301)

    with pytest.raises(SignatureVerificationError):
        webhooks.verify(BODY, header, SECRET, now=NOW - 301)


def test_the_wrong_secret_is_refused() -> None:
    header = _header(BODY, [SECRET], NOW)

    with pytest.raises(SignatureVerificationError):
        webhooks.verify(BODY, header, OTHER_SECRET, now=NOW)


def test_a_malformed_header_verifies_nothing() -> None:
    # The header is the one part of a request an attacker controls
    # entirely, so every shape of rubbish must be a refusal and never an
    # exception a receiver did not plan for.
    rubbish = [
        "",
        "garbage",
        "t=",
        "v1=abc",
        "t=notanumber,v1=abc",
        "t=1755331200",
        "t=-1755331200,v1=abc",
        f"v1={_sign(BODY, SECRET, NOW)}",
        f"t={NOW}",
    ]

    for header in rubbish:
        with pytest.raises(SignatureVerificationError):
            webhooks.verify(BODY, header, SECRET, now=NOW)


def test_a_timestamp_that_is_not_ascii_digits_is_not_a_timestamp() -> None:
    # The server's parser is `ctype_digit`: ASCII digits, nothing else. A
    # Python port written with `str.isdigit()` or a bare `int()` would ALSO
    # accept fullwidth and Arabic-Indic digits, so this header — whose
    # timestamp is inside the window and whose signature is genuine — would
    # verify here and be refused by every other implementation.
    #
    # It needs a VALID signature to discriminate: with a rubbish `v1` the
    # MAC comparison refuses it either way, and the parser is never the
    # thing under test.
    fullwidth = str(NOW).translate({ord(d): ord("０") + int(d) for d in "0123456789"})

    assert fullwidth != str(NOW)
    assert fullwidth.isdigit()

    header = f"t={fullwidth},v1={_sign(BODY, SECRET, NOW)}"

    with pytest.raises(SignatureVerificationError):
        webhooks.verify(BODY, header, SECRET, now=NOW)


# -- rotation --------------------------------------------------------------


def test_every_v1_candidate_is_tried_so_a_rotation_does_not_drop_deliveries() -> None:
    # During a rotation's grace window the header carries two `v1` values,
    # newest first. A receiver holding EITHER copy must verify: the one
    # they have just installed, or the one they have not got round to
    # replacing. Stopping at the first candidate would break exactly one of
    # them, and only for as long as the window lasts — which is the worst
    # kind of bug to find.
    header = _header(BODY, [SECRET, OTHER_SECRET], NOW)

    assert header.count("v1=") == 2

    webhooks.verify(BODY, header, SECRET, now=NOW)
    webhooks.verify(BODY, header, OTHER_SECRET, now=NOW)


def test_once_the_grace_is_over_the_old_secret_is_refused() -> None:
    header = _header(BODY, [SECRET], NOW)

    with pytest.raises(SignatureVerificationError):
        webhooks.verify(BODY, header, OTHER_SECRET, now=NOW)


# -- the surface -----------------------------------------------------------


def test_the_header_name_is_published_so_a_receiver_need_not_hardcode_it() -> None:
    assert webhooks.SIGNATURE_HEADER == "Ringivo-Signature"
    assert webhooks.DEFAULT_TOLERANCE_SECONDS == 300


def test_the_tolerance_window_is_five_minutes_and_can_be_narrowed() -> None:
    header = _header(BODY, [SECRET], NOW)

    webhooks.verify(BODY, header, SECRET, now=NOW + 299)

    with pytest.raises(SignatureVerificationError):
        webhooks.verify(BODY, header, SECRET, tolerance=60, now=NOW + 61)


def test_with_no_clock_given_it_uses_the_receivers_own() -> None:
    now = int(time.time())

    webhooks.verify(BODY, _header(BODY, [SECRET], now), SECRET)

    with pytest.raises(SignatureVerificationError):
        webhooks.verify(BODY, _header(BODY, [SECRET], now - 3600), SECRET)


def test_a_str_payload_is_read_as_utf8_for_the_frameworks_that_hand_one_over() -> None:
    body = '{"note":"café"}'
    header = _header(body.encode(), [SECRET], NOW)

    webhooks.verify(body, header, SECRET, now=NOW)


def test_verify_answers_with_silence_and_raises_the_documented_type() -> None:
    # It returns None on success on purpose: a boolean invites
    # `if verify(...)` written without the `if`, which is a check that never
    # runs. There is nothing to forget about an exception.
    assert webhooks.verify(BODY, _header(BODY, [SECRET], NOW), SECRET, now=NOW) is None

    with pytest.raises(SignatureVerificationError) as caught:
        webhooks.verify(BODY, "t=1,v1=ff", SECRET, now=NOW)

    from ringivo import RingivoError

    assert isinstance(caught.value, RingivoError)


# -- message.* events: parse after verify ---------------------------------------

# The three examples the spec publishes for message.sent, message.delivered
# and message.failed, copied verbatim.
_MESSAGE_DATA: dict[str, Any] = {
    "id": "0192f0c1-8e4a-7b3d-a2c5-6d7e8f901234",
    "tenantId": "0191aa10-2b3c-7d4e-8f90-a1b2c3d4e5f6",
    "customerId": "0191ab22-3c4d-7e5f-9a01-b2c3d4e5f607",
    "source": "phone_system",
    "kind": "sms",
    "from": "+14075550142",
    "to": "+13215550187",
    "body": "Yes, a little grass is fine. Call us if he vomits.",
    "media": [],
    "status": "sent",
    "sentBy": {"kind": "phone_system_user", "name": "Dana Smith"},
    "sentAt": "2026-10-19T15:06:01+00:00",
    "providerMessageId": "01JC8ZB2H6V4S9D3Q7N1M5KTXR",
    "providerPartIds": ["01JC8ZB2H6V4S9D3Q7N1M5KTXR"],
}
MESSAGE_SENT: dict[str, Any] = {
    "eventId": "0192f0c2-1a7b-7c4d-9e8f-0a1b2c3d4e5f",
    "type": "message.sent",
    "occurredAt": "2026-10-19T15:06:01+00:00",
    "data": _MESSAGE_DATA,
}
MESSAGE_DELIVERED: dict[str, Any] = {
    "eventId": "0192f0c3-5d6e-7f80-91a2-b3c4d5e6f708",
    "type": "message.delivered",
    "occurredAt": "2026-10-19T15:06:04+00:00",
    "data": {**_MESSAGE_DATA, "status": "delivered"},
}
MESSAGE_FAILED: dict[str, Any] = {
    "eventId": "0192f0c4-6e7f-7091-a2b3-c4d5e6f70819",
    "type": "message.failed",
    "occurredAt": "2026-10-19T15:06:09+00:00",
    "data": {**_MESSAGE_DATA, "status": "undelivered", "failure": {"cause": "undelivered"}},
}


def test_outbound_message_event_types_are_the_three_sent_message_events() -> None:
    assert webhooks.OUTBOUND_MESSAGE_EVENT_TYPES == {
        "message.sent",
        "message.delivered",
        "message.failed",
    }


def test_inbound_message_event_types_are_the_received_message_event() -> None:
    assert webhooks.INBOUND_MESSAGE_EVENT_TYPES == {"message.received"}


def test_the_two_directions_do_not_overlap() -> None:
    assert webhooks.INBOUND_MESSAGE_EVENT_TYPES.isdisjoint(webhooks.OUTBOUND_MESSAGE_EVENT_TYPES)
    assert not hasattr(webhooks, "MESSAGE_EVENT_TYPES")


def test_the_event_type_sets_cannot_be_changed_at_runtime() -> None:
    for types in (
        webhooks.INBOUND_MESSAGE_EVENT_TYPES,
        webhooks.OUTBOUND_MESSAGE_EVENT_TYPES,
        webhooks.FAILURE_CAUSES,
    ):
        assert isinstance(types, frozenset)


def test_the_event_type_sets_are_exported() -> None:
    assert {
        "FAILURE_CAUSES",
        "INBOUND_MESSAGE_EVENT_TYPES",
        "OUTBOUND_MESSAGE_EVENT_TYPES",
    } <= set(webhooks.__all__)


# -- one variant per direction -------------------------------------------------


def test_the_variants_are_exported_and_the_shared_shape_is_gone() -> None:
    names = {
        "FailureCause",
        "MessageDeliveredEvent",
        "MessageEvent",
        "MessageFailedEvent",
        "MessageFailedEventData",
        "MessageReceivedEvent",
        "MessageReceivedEventData",
        "MessageSentEvent",
        "OutboundMessageEventData",
        "UnknownMessageEvent",
    }
    assert names <= set(ringivo.__all__)
    assert names <= set(models.__all__)
    for gone in ("MessageEventData", "InboundMessageEvent", "OutboundMessageEvent"):
        assert gone not in ringivo.__all__
        assert not hasattr(ringivo, gone)
        assert not hasattr(models, gone)


def test_message_event_is_now_the_union_of_the_variants() -> None:
    """The name `MessageEvent` was one class before 0.23.0. It is now the
    union `parse_message_event()` returns, the same as the TypeScript client.
    """
    assert set(get_args(MessageEvent)) == {
        MessageReceivedEvent,
        MessageSentEvent,
        MessageDeliveredEvent,
        MessageFailedEvent,
        UnknownMessageEvent,
    }


@pytest.mark.parametrize(
    ("payload", "variant"),
    [
        ({"type": "message.received"}, MessageReceivedEvent),
        ({"type": "message.sent"}, MessageSentEvent),
        ({"type": "message.delivered"}, MessageDeliveredEvent),
        ({"type": "message.failed"}, MessageFailedEvent),
    ],
)
def test_each_event_type_parses_to_the_class_named_after_it(
    payload: dict[str, Any], variant: type
) -> None:
    """One class per event type, named after it, as in the TypeScript
    client: `message.sent` is a `MessageSentEvent`, and so on.
    """
    event = webhooks.parse_message_event(payload)

    assert type(event) is variant
    assert event.type == payload["type"]
    assert variant.__name__ == "Message" + payload["type"].split(".")[1].title() + "Event"


def _field_names(model: type) -> set[str]:
    return {f.name for f in dataclasses.fields(model)}


def test_each_variant_carries_only_its_own_members() -> None:
    """A received text has none of a sent text's members, and the other way
    round. This is the whole point of the split: code cannot read `sent_by`
    off a customer's text and take it for a staff reply.
    """
    envelope = {"type", "event_id", "occurred_at", "raw"}
    assert _field_names(MessageReceivedEvent) == envelope | {"message"}
    assert _field_names(MessageSentEvent) == envelope | {"message"}
    assert _field_names(MessageDeliveredEvent) == envelope | {"message"}
    assert _field_names(MessageFailedEvent) == envelope | {"message"}
    assert _field_names(UnknownMessageEvent) == envelope

    shared = {"id", "tenant_id", "customer_id", "kind", "from_", "to", "body", "media", "raw"}
    assert _field_names(MessageReceivedEventData) == shared | {"received_at"}
    outbound = shared | {
        "source",
        "status",
        "sent_by",
        "sent_at",
        "provider_message_id",
        "provider_part_ids",
    }
    assert _field_names(OutboundMessageEventData) == outbound
    assert _field_names(MessageFailedEventData) == outbound | {"failure_cause"}
    assert issubclass(MessageFailedEventData, OutboundMessageEventData)


@pytest.mark.parametrize("payload", [MESSAGE_SENT, MESSAGE_DELIVERED])
def test_a_sent_or_delivered_event_carries_the_outbound_shape(payload: dict[str, Any]) -> None:
    event = webhooks.parse_message_event(payload)

    assert isinstance(event, (MessageSentEvent, MessageDeliveredEvent))
    assert type(event.message) is OutboundMessageEventData
    assert event.type == payload["type"]
    assert event.type in webhooks.OUTBOUND_MESSAGE_EVENT_TYPES
    assert not hasattr(event.message, "received_at")
    assert not hasattr(event.message, "failure_cause")


def test_a_failed_event_parses_as_its_own_variant() -> None:
    event = webhooks.parse_message_event(MESSAGE_FAILED)

    assert isinstance(event, MessageFailedEvent)
    assert event.type == "message.failed"
    assert event.type in webhooks.OUTBOUND_MESSAGE_EVENT_TYPES
    assert isinstance(event.message, MessageFailedEventData)
    assert not hasattr(event.message, "received_at")


def test_the_specs_message_received_example_parses_as_received(
    openapi_spec: dict[str, Any],
) -> None:
    event = webhooks.parse_message_event(_received_example(openapi_spec))

    assert isinstance(event, MessageReceivedEvent)
    assert event.type in webhooks.INBOUND_MESSAGE_EVENT_TYPES
    for member in ("source", "status", "sent_by", "sent_at", "failure_cause"):
        assert not hasattr(event.message, member)


def test_every_outbound_and_inbound_type_is_a_webhook_the_spec_publishes(
    openapi_spec: dict[str, Any],
) -> None:
    published = set(openapi_spec["webhooks"])
    assert webhooks.OUTBOUND_MESSAGE_EVENT_TYPES <= published
    assert webhooks.INBOUND_MESSAGE_EVENT_TYPES <= published


def test_every_message_event_type_is_a_webhook_the_spec_publishes(
    openapi_spec: dict[str, Any],
) -> None:
    published = {name for name in openapi_spec["webhooks"] if name.startswith("message.")}
    assert (
        webhooks.INBOUND_MESSAGE_EVENT_TYPES | webhooks.OUTBOUND_MESSAGE_EVENT_TYPES
    ) == published


def _received_example(spec: dict[str, Any]) -> dict[str, Any]:
    return spec["webhooks"]["message.received"]["post"]["requestBody"]["content"][
        "application/json"
    ]["example"]


def test_the_specs_message_received_example_parses(openapi_spec: dict[str, Any]) -> None:
    payload = _received_example(openapi_spec)
    raw = json.dumps(payload).encode()
    webhooks.verify(raw, _header(raw, [SECRET], NOW), SECRET, now=NOW)

    event = webhooks.parse_message_event(json.loads(raw))

    assert isinstance(event, MessageReceivedEvent)
    assert event.type == "message.received"
    assert event.event_id == payload["eventId"]
    assert event.occurred_at == datetime(2026, 8, 16, 11, 14, 7, tzinfo=timezone.utc)
    assert event.raw == payload
    message = event.message
    assert message.id == payload["data"]["id"]
    assert message.tenant_id == payload["data"]["tenantId"]
    assert message.customer_id == payload["data"]["customerId"]
    assert message.kind == "mms"
    assert message.from_ == "+13025556789"
    assert message.to == "+14075550100"
    assert message.body == "Here is the referral form."
    assert message.received_at == datetime(2026, 8, 16, 11, 14, 7, tzinfo=timezone.utc)
    (item,) = message.media
    # Exactly the webhook's item, never the API's linked one: a webhook body
    # carries no download link.
    assert type(item) is InboundMessageMediaItem
    assert not hasattr(item, "content_url")
    assert item.content_type == "image/jpeg"
    assert item.filename == "photo.jpg"
    assert item.size == 40213


def test_a_link_on_a_received_media_item_is_not_read() -> None:
    """`message.received` media items have no link: a webhook body can reach
    logs, and a retry can arrive hours after a link died. A body that carries
    one anyway (a server bug, or a forged body) still parses as the
    webhook's item, and the member stays on `raw` only. A download goes
    through `inbound_messages.get()` with the caller's own credential.
    """
    item = {
        "contentType": "image/jpeg",
        "filename": "photo.jpg",
        "size": 40213,
        "contentUrl": "https://api.yourprovider.example/v1/inbound-messages/x/media/y/content",
        "expiresAt": "2026-08-18T12:43:57+00:00",
    }
    event = webhooks.parse_message_event(
        {"type": "message.received", "data": {"id": "x", "media": [item]}}
    )

    assert isinstance(event, MessageReceivedEvent)
    (read,) = event.message.media
    assert type(read) is InboundMessageMediaItem
    assert not hasattr(read, "content_url")
    assert read.raw == item


def test_outbound_members_on_a_received_body_are_not_read() -> None:
    """A `message.received` body that carries `sentBy` (a server bug, or a
    forged body) still parses as a received text, and that member stays on
    `raw` only. It never becomes a staff reply.
    """
    data = {"id": "x", "sentBy": {"kind": "phone_system_user", "name": "Dana"}, "source": "api"}
    event = webhooks.parse_message_event({"type": "message.received", "data": data})

    assert isinstance(event, MessageReceivedEvent)
    assert not hasattr(event.message, "sent_by")
    assert event.message.raw["sentBy"] == data["sentBy"]


@pytest.mark.parametrize(
    "data",
    [
        "not an object",
        {"receivedAt": "not a date", "media": "x", "customerId": 7},
        {"receivedAt": 1755331200, "media": [None, "x", {"size": "big"}]},
    ],
)
def test_a_malformed_message_received_body_never_raises(data: Any) -> None:
    event = webhooks.parse_message_event({"type": "message.received", "data": data})
    assert isinstance(event, MessageReceivedEvent)
    assert event.type == "message.received"
    assert event.message.received_at is None
    assert event.message.customer_id is None
    assert all(item.size is None for item in event.message.media)


def test_a_verified_message_sent_body_parses() -> None:
    raw = json.dumps(MESSAGE_SENT).encode()
    webhooks.verify(raw, _header(raw, [SECRET], NOW), SECRET, now=NOW)

    event = webhooks.parse_message_event(json.loads(raw))

    assert isinstance(event, MessageSentEvent)
    assert event.event_id == "0192f0c2-1a7b-7c4d-9e8f-0a1b2c3d4e5f"
    assert event.type == "message.sent"
    assert event.occurred_at == datetime(2026, 10, 19, 15, 6, 1, tzinfo=timezone.utc)
    message = event.message
    assert message.id == "0192f0c1-8e4a-7b3d-a2c5-6d7e8f901234"
    assert message.tenant_id == "0191aa10-2b3c-7d4e-8f90-a1b2c3d4e5f6"
    assert message.customer_id == "0191ab22-3c4d-7e5f-9a01-b2c3d4e5f607"
    assert message.source == "phone_system"
    assert message.kind == "sms"
    assert message.from_ == "+14075550142"
    assert message.to == "+13215550187"
    assert message.body == "Yes, a little grass is fine. Call us if he vomits."
    assert message.media == ()
    assert message.status == "sent"
    assert message.sent_by is not None
    assert message.sent_by.kind == "phone_system_user"
    assert message.sent_by.name == "Dana Smith"
    assert message.sent_at == datetime(2026, 10, 19, 15, 6, 1, tzinfo=timezone.utc)
    assert message.provider_message_id == "01JC8ZB2H6V4S9D3Q7N1M5KTXR"
    assert message.provider_part_ids == ("01JC8ZB2H6V4S9D3Q7N1M5KTXR",)
    assert event.raw == MESSAGE_SENT


def test_message_delivered_parses() -> None:
    event = webhooks.parse_message_event(MESSAGE_DELIVERED)
    assert isinstance(event, MessageDeliveredEvent)
    assert event.type == "message.delivered"
    assert event.message.status == "delivered"


def test_message_failed_carries_its_cause() -> None:
    event = webhooks.parse_message_event(MESSAGE_FAILED)
    assert isinstance(event, MessageFailedEvent)
    assert event.type == "message.failed"
    assert event.message.status == "undelivered"
    assert event.message.failure_cause == "undelivered"


@pytest.mark.parametrize("payload", [MESSAGE_SENT, MESSAGE_DELIVERED])
def test_only_message_failed_reads_a_failure_cause(payload: dict[str, Any]) -> None:
    """The same rule as the TypeScript client: only the failed variant has
    the member. A `failure` on a sent or delivered body is not a failure,
    and stays on `raw` only.
    """
    data = {**_MESSAGE_DATA, "failure": {"cause": "provider_refused"}}
    event = webhooks.parse_message_event({**payload, "data": data})

    assert isinstance(event, (MessageSentEvent, MessageDeliveredEvent))
    assert not hasattr(event.message, "failure_cause")
    assert event.message.raw["failure"] == {"cause": "provider_refused"}


def _documented_failure_causes(spec: dict[str, Any]) -> set[str]:
    """The `OutboundMessageFailureCause` enum, after checking that
    `failure.cause` is typed by it."""
    schemas = spec["components"]["schemas"]
    failed = schemas["MessageFailedEventData"]["allOf"][1]
    cause = failed["properties"]["failure"]["properties"]["cause"]
    assert cause["allOf"] == [{"$ref": "#/components/schemas/OutboundMessageFailureCause"}]
    return set(schemas["OutboundMessageFailureCause"]["enum"])


def _causes_on_the_failed_webhook(spec: dict[str, Any]) -> set[str]:
    """The causes the `message.failed` webhook's description explains, one
    `` - `cause` `` bullet each (two share the `no_send_key` bullet)."""
    description = spec["webhooks"]["message.failed"]["post"]["description"]
    bullets = [line for line in description.splitlines() if line.startswith("- `")]
    return {name for line in bullets for name in re.findall(r"`([a-z_]+)`", line.split("—")[0])}


def test_failure_causes_are_the_causes_the_spec_documents(openapi_spec: dict[str, Any]) -> None:
    documented = _documented_failure_causes(openapi_spec)

    assert len(documented) == 7, f"{sorted(documented)} — the spec's list moved; read it again"
    assert webhooks.FAILURE_CAUSES == documented
    assert webhooks.FAILURE_CAUSES == frozenset(get_args(FailureCause))
    assert _causes_on_the_failed_webhook(openapi_spec) == documented


def test_send_interrupted_replaced_the_two_uncertain_causes() -> None:
    assert "send_interrupted" in webhooks.FAILURE_CAUSES
    assert "outcome_unknown" not in webhooks.FAILURE_CAUSES
    assert "submission_interrupted" not in webhooks.FAILURE_CAUSES


@pytest.mark.parametrize("cause", sorted(webhooks.FAILURE_CAUSES))
def test_every_known_cause_parses_as_itself(cause: str) -> None:
    data = {**_MESSAGE_DATA, "status": "failed", "failure": {"cause": cause}}
    event = webhooks.parse_message_event({**MESSAGE_FAILED, "data": data})

    assert isinstance(event, MessageFailedEvent)
    assert event.message.failure_cause == cause


def test_a_message_that_never_left_reads_none_for_the_provider_members() -> None:
    data = {
        **_MESSAGE_DATA,
        "source": "api",
        "status": "failed",
        "sentBy": None,
        "sentAt": None,
        "providerMessageId": None,
        "providerPartIds": None,
        "failure": {"cause": "provider_refused"},
    }
    event = webhooks.parse_message_event({**MESSAGE_FAILED, "data": data})
    assert isinstance(event, MessageFailedEvent)
    assert event.message.sent_by is None
    assert event.message.sent_at is None
    assert event.message.provider_message_id is None
    assert event.message.provider_part_ids is None
    assert event.message.failure_cause == "provider_refused"


def test_an_empty_part_id_list_still_reads_as_an_empty_tuple() -> None:
    """The API never sends `[]` any more (null exactly when the message id is
    null), but the reader does not flatten `[]` into None: what arrived is
    what you read."""
    data = {**_MESSAGE_DATA, "providerMessageId": None, "providerPartIds": []}
    event = webhooks.parse_message_event({**MESSAGE_FAILED, "data": data})
    assert isinstance(event, MessageFailedEvent)
    assert event.message.provider_part_ids == ()


def test_unknown_values_and_members_are_kept_not_refused() -> None:
    """A cause or source this release does not know still arrives, as a
    string. A receiver treats a cause it does not know as a failure.
    """
    data = {
        **_MESSAGE_DATA,
        "source": "a_source_added_later",
        "somethingNew": {"x": 1},
        "failure": {"cause": "a_cause_added_later"},
    }
    event = webhooks.parse_message_event({**MESSAGE_FAILED, "data": data, "extra": True})
    assert isinstance(event, MessageFailedEvent)
    assert event.message.source == "a_source_added_later"
    assert event.message.failure_cause == "a_cause_added_later"
    assert event.message.failure_cause not in webhooks.FAILURE_CAUSES
    assert event.message.raw["somethingNew"] == {"x": 1}
    assert event.raw["extra"] is True


def test_outbound_media_items_read_content_type_and_size() -> None:
    media = [{"contentType": "image/jpeg", "size": 40213}]
    event = webhooks.parse_message_event(
        {**MESSAGE_SENT, "data": {**_MESSAGE_DATA, "kind": "mms", "media": media}}
    )
    assert isinstance(event, MessageSentEvent)
    (item,) = event.message.media
    assert item == OutboundMessageMediaItem(
        content_type="image/jpeg", size=40213, raw={"contentType": "image/jpeg", "size": 40213}
    )
    # An outbound item has no filename: the platform keeps none for it.
    assert not hasattr(item, "filename")


def test_the_old_media_members_are_no_longer_read() -> None:
    """`bytes` and `encoding` left the wire in 0.23.0; an item that still
    carries them reads no size, and the old members stay on `raw` only."""
    media = [{"contentType": "image/jpeg", "filename": "a.jpg", "encoding": "base64", "bytes": 9}]
    event = webhooks.parse_message_event(
        {"type": "message.received", "data": {"kind": "mms", "media": media}}
    )
    assert isinstance(event, MessageReceivedEvent)
    (item,) = event.message.media
    assert item.size is None
    assert not hasattr(item, "encoding")
    assert item.raw["bytes"] == 9


@pytest.mark.parametrize(
    "event_type",
    [
        "fax.delivered",  # another event family
        "message.queued",  # a message event this release does not know
        "message.Sent",  # not the same string
        " message.sent",
        "MESSAGE.RECEIVED",
    ],
)
def test_an_unknown_type_parses_as_unknown_and_keeps_the_type_on_raw(event_type: str) -> None:
    payload = {**MESSAGE_SENT, "type": event_type}
    event = webhooks.parse_message_event(payload)

    assert isinstance(event, UnknownMessageEvent)
    assert event.type is None
    assert event.raw["type"] == event_type
    assert event.event_id == MESSAGE_SENT["eventId"]
    assert event.occurred_at == datetime(2026, 10, 19, 15, 6, 1, tzinfo=timezone.utc)
    assert not hasattr(event, "message")


class _NotADict(Mapping[str, Any]):
    """A mapping that is not a dict, whose `type` is a known one."""

    def __init__(self, items: dict[str, Any]) -> None:
        self._items = items

    def __getitem__(self, key: str) -> Any:
        return self._items[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)


def test_any_mapping_is_read_not_only_a_dict() -> None:
    event = webhooks.parse_message_event(_NotADict(MESSAGE_FAILED))

    assert isinstance(event, MessageFailedEvent)
    assert event.message.failure_cause == "undelivered"


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        [MESSAGE_SENT],
        "message.sent",
        b"message.sent",
        7,
        float("nan"),
        {},
        {"type": None},
        {"type": 7},
        {"type": ["message.sent"]},  # unhashable: a set lookup would raise
        {"type": {"message.sent": True}},
        {"eventId": 7, "occurredAt": "yesterday", "data": "x"},
    ],
)
def test_garbage_parses_as_unknown_and_never_raises(payload: Any) -> None:
    event = webhooks.parse_message_event(payload)

    assert isinstance(event, UnknownMessageEvent)
    assert event.type is None
    assert event.event_id is None
    assert event.occurred_at is None
    assert event.raw == (payload if isinstance(payload, dict) else {})


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "message.sent"},
        {"type": "message.sent", "data": "not an object"},
        {"type": "message.failed", "data": {"failure": "x"}},
        {"type": "message.failed", "data": {"failure": {"cause": 7}}},
        {
            "type": "message.delivered",
            "eventId": ["x"],
            "occurredAt": 1755331200,
            "data": {"providerMessageId": 12, "providerPartIds": "x", "sentBy": "Dana"},
        },
    ],
)
def test_a_malformed_outbound_body_reads_none_and_never_raises(payload: Any) -> None:
    event = webhooks.parse_message_event(payload)

    assert isinstance(event, (MessageSentEvent, MessageDeliveredEvent, MessageFailedEvent))
    assert event.type == payload["type"]
    assert event.event_id is None
    assert event.occurred_at is None
    assert event.message.provider_message_id is None
    assert event.message.provider_part_ids is None
    assert event.message.sent_by is None
    if isinstance(event, MessageFailedEvent):
        assert event.message.failure_cause is None
