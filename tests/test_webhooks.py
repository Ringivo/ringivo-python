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

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from ringivo import SignatureVerificationError, webhooks

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


def test_message_event_types_are_the_four_message_events() -> None:
    assert webhooks.MESSAGE_EVENT_TYPES == {
        "message.received",
        "message.sent",
        "message.delivered",
        "message.failed",
    }


def test_outbound_message_event_types_are_the_three_sent_message_events() -> None:
    assert webhooks.OUTBOUND_MESSAGE_EVENT_TYPES == {
        "message.sent",
        "message.delivered",
        "message.failed",
    }


def test_inbound_message_event_types_are_the_received_message_event() -> None:
    assert webhooks.INBOUND_MESSAGE_EVENT_TYPES == {"message.received"}


def test_message_event_types_is_the_union_of_the_two_directions() -> None:
    assert webhooks.INBOUND_MESSAGE_EVENT_TYPES.isdisjoint(webhooks.OUTBOUND_MESSAGE_EVENT_TYPES)
    assert webhooks.MESSAGE_EVENT_TYPES == (
        webhooks.INBOUND_MESSAGE_EVENT_TYPES | webhooks.OUTBOUND_MESSAGE_EVENT_TYPES
    )


def test_the_event_type_sets_cannot_be_changed_at_runtime() -> None:
    for types in (
        webhooks.MESSAGE_EVENT_TYPES,
        webhooks.INBOUND_MESSAGE_EVENT_TYPES,
        webhooks.OUTBOUND_MESSAGE_EVENT_TYPES,
    ):
        assert isinstance(types, frozenset)


def test_the_event_type_sets_are_exported() -> None:
    assert {
        "MESSAGE_EVENT_TYPES",
        "INBOUND_MESSAGE_EVENT_TYPES",
        "OUTBOUND_MESSAGE_EVENT_TYPES",
    } <= set(webhooks.__all__)


@pytest.mark.parametrize("payload", [MESSAGE_SENT, MESSAGE_DELIVERED, MESSAGE_FAILED])
def test_a_sent_message_event_routes_outbound_only(payload: dict[str, Any]) -> None:
    event = webhooks.parse_message_event(payload)

    assert event.type in webhooks.OUTBOUND_MESSAGE_EVENT_TYPES
    assert event.type not in webhooks.INBOUND_MESSAGE_EVENT_TYPES


def test_the_specs_message_received_example_routes_inbound_only(
    openapi_spec: dict[str, Any],
) -> None:
    event = webhooks.parse_message_event(_received_example(openapi_spec))

    assert event.type in webhooks.INBOUND_MESSAGE_EVENT_TYPES
    assert event.type not in webhooks.OUTBOUND_MESSAGE_EVENT_TYPES


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
    assert webhooks.MESSAGE_EVENT_TYPES == published


def _received_example(spec: dict[str, Any]) -> dict[str, Any]:
    return spec["webhooks"]["message.received"]["post"]["requestBody"]["content"][
        "application/json"
    ]["example"]


def test_the_specs_message_received_example_parses(openapi_spec: dict[str, Any]) -> None:
    payload = _received_example(openapi_spec)
    raw = json.dumps(payload).encode()
    webhooks.verify(raw, _header(raw, [SECRET], NOW), SECRET, now=NOW)

    event = webhooks.parse_message_event(json.loads(raw))

    assert event.type == "message.received"
    assert event.event_id == payload["eventId"]
    assert event.occurred_at == datetime(2026, 8, 16, 11, 14, 7, tzinfo=timezone.utc)
    message = event.message
    assert message.id == payload["data"]["id"]
    assert message.tenant_id == payload["data"]["tenantId"]
    assert message.customer_id == payload["data"]["customerId"]
    assert message.kind == "mms"
    assert message.from_ == "+13025556789"
    assert message.to == "+14075550100"
    assert message.body == "Here is the referral form."
    assert message.received_at == datetime(2026, 8, 16, 11, 14, 7, tzinfo=timezone.utc)
    (part,) = message.media
    assert part.content_type == "image/jpeg"
    assert part.filename == "photo.jpg"
    assert part.encoding == "base64"
    assert part.byte_size == 40213
    # The members only a message SENT from your number has are absent here.
    assert message.source is None
    assert message.status is None
    assert message.sent_by is None
    assert message.sent_at is None
    assert message.provider_message_id is None
    assert message.provider_part_ids is None
    assert message.failure_cause is None


def test_an_outbound_event_has_no_received_at() -> None:
    assert webhooks.parse_message_event(MESSAGE_SENT).message.received_at is None


@pytest.mark.parametrize(
    "data",
    [
        "not an object",
        {"receivedAt": "not a date", "media": "x", "customerId": 7},
        {"receivedAt": 1755331200, "media": [None, "x", {"bytes": "big"}]},
    ],
)
def test_a_malformed_message_received_body_never_raises(data: Any) -> None:
    event = webhooks.parse_message_event({"type": "message.received", "data": data})
    assert event.type == "message.received"
    assert event.message.received_at is None
    assert event.message.customer_id is None
    assert all(part.byte_size is None for part in event.message.media)


def test_a_verified_message_sent_body_parses() -> None:
    raw = json.dumps(MESSAGE_SENT).encode()
    webhooks.verify(raw, _header(raw, [SECRET], NOW), SECRET, now=NOW)

    event = webhooks.parse_message_event(json.loads(raw))

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
    assert message.failure_cause is None
    assert event.raw == MESSAGE_SENT


def test_message_delivered_parses() -> None:
    event = webhooks.parse_message_event(MESSAGE_DELIVERED)
    assert event.type == "message.delivered"
    assert event.message.status == "delivered"
    assert event.message.failure_cause is None


def test_message_failed_carries_its_cause() -> None:
    event = webhooks.parse_message_event(MESSAGE_FAILED)
    assert event.type == "message.failed"
    assert event.message.status == "undelivered"
    assert event.message.failure_cause == "undelivered"


def test_a_message_that_never_left_reads_none_for_the_provider_members() -> None:
    data = {
        **_MESSAGE_DATA,
        "source": "api",
        "status": "failed",
        "sentBy": None,
        "sentAt": None,
        "providerMessageId": None,
        "providerPartIds": [],
        "failure": {"cause": "provider_refused"},
    }
    event = webhooks.parse_message_event({**MESSAGE_FAILED, "data": data})
    assert event.message.sent_by is None
    assert event.message.sent_at is None
    assert event.message.provider_message_id is None
    assert event.message.provider_part_ids == ()
    assert event.message.failure_cause == "provider_refused"


def test_unknown_values_and_members_are_kept_not_refused() -> None:
    data = {
        **_MESSAGE_DATA,
        "source": "a_source_added_later",
        "somethingNew": {"x": 1},
        "failure": {"cause": "a_cause_added_later"},
    }
    event = webhooks.parse_message_event({**MESSAGE_FAILED, "data": data, "extra": True})
    assert event.message.source == "a_source_added_later"
    assert event.message.failure_cause == "a_cause_added_later"
    assert event.message.raw["somethingNew"] == {"x": 1}
    assert event.raw["extra"] is True


def test_picture_parts_read_the_bytes_member() -> None:
    media = [
        {"contentType": "image/jpeg", "filename": None, "encoding": None, "bytes": 40213},
    ]
    event = webhooks.parse_message_event(
        {**MESSAGE_SENT, "data": {**_MESSAGE_DATA, "kind": "mms", "media": media}}
    )
    (part,) = event.message.media
    assert part.content_type == "image/jpeg"
    assert part.filename is None
    assert part.encoding is None
    assert part.byte_size == 40213


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        "message.sent",
        {},
        {"type": "message.sent"},
        {"type": "message.sent", "data": "not an object"},
        {"type": 7, "data": {"providerMessageId": 12, "providerPartIds": "x", "sentBy": "Dana"}},
    ],
)
def test_a_malformed_body_reads_none_and_never_raises(payload: Any) -> None:
    event = webhooks.parse_message_event(payload)
    assert event.message.provider_message_id is None
    assert event.message.provider_part_ids is None
    assert event.message.sent_by is None
