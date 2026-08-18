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
