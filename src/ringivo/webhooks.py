"""Prove a webhook body came from your provider, and recently.

    from ringivo import webhooks

    @app.post("/hooks/fax")
    def receive(request):
        webhooks.verify(
            request.body,                                  # the RAW bytes
            request.headers["Ringivo-Signature"],
            secret=YOUR_WHSEC_SECRET,
        )
        ...

No client, no network, no credential beyond the `whsec_` secret the endpoint
was created with. This is the whole receiving half of the contract.

-- SIGN THE RAW BODY, NEVER A RE-ENCODING --------------------------------------
The bytes verified must be the bytes that arrived. A receiver that parses the
JSON and re-encodes it before verifying WILL fail, and correctly so: key
order, unicode escaping and number formatting are free choices no two
encoders make identically. This is the single most common integration
mistake with signatures of this shape, so reach for your framework's raw-body
accessor — `request.get_data()`, `await request.body()`, `request.body` —
rather than for the parsed object.

-- WHY THE TIMESTAMP IS INSIDE THE MAC -----------------------------------------
The signed message is `"<t>.<raw body>"`, not the body alone. Were `t` merely
a header beside the signature, an attacker holding one captured delivery
could replay it forever under a fresh `t` and the MAC would still check out,
because it never covered the time. Binding them means a replay must reuse the
original `t`, which is what makes the tolerance window real.

-- BOTH HALVES MUST PASS -------------------------------------------------------
A good MAC under an old `t` is a replay; a fresh `t` with no matching MAC is a
forgery. Neither is a delivery, and both raise.

-- EVERY `v1` IS TRIED ---------------------------------------------------------
A second `v1` appears during a rotation's grace window, signed with the
previous secret, newest first. A receiver holding EITHER copy must verify —
that is the whole reason the window exists — so the loop below does not stop
at the first candidate.

-- PARSING COMES AFTER, AND IS SEPARATE ----------------------------------------
`verify()` proves the bytes; it does not read them. A receiver verifies the
raw body, decodes the JSON itself — so it decides what a body that is not
JSON, or not an object, deserves — and then hands the object to a parser:

    webhooks.verify(raw, request.headers[webhooks.SIGNATURE_HEADER], secret=WHSEC)
    event = webhooks.parse_message_event(json.loads(raw))
    if event.type == "message.received":   # a text sent TO you: MessageReceivedEvent
        ...
    elif event.type == "message.failed":   # a text from you did not arrive: MessageFailedEvent
        ...
    elif event.type is not None:            # MessageSentEvent or MessageDeliveredEvent
        ...
    # else: not a message event (UnknownMessageEvent). Accept it and ignore it.

`parse_message_event()` reads defensively, like every model in this package:
a member that is missing or of the wrong type reads None and the whole
body stays on `raw`. It never raises on content, so the receiver decides
which None it cannot work without.

-- ONE CLASS PER EVENT TYPE ----------------------------------------------------
Each event type is its own class, named after it, and each has only its own
members. Code that reads `sent_by` off a received text, and so could
take a customer's text for a staff reply, fails in the type checker. The
`type` member is a `Literal`, so a check on it narrows the variant.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import time
from typing import Any, get_args

from .errors import SignatureVerificationError
from .models import (
    FailureCause,
    MessageEvent,
    _message_event_from_json,
)

__all__ = [
    "DEFAULT_TOLERANCE_SECONDS",
    "FAILURE_CAUSES",
    "INBOUND_MESSAGE_EVENT_TYPES",
    "OUTBOUND_MESSAGE_EVENT_TYPES",
    "SIGNATURE_HEADER",
    "parse_message_event",
    "verify",
]

#: The events about a message sent FROM one of your numbers. All three carry
#: the same members, and `message.failed` adds `failure.cause`. They parse to
#: a `MessageSentEvent`, a `MessageDeliveredEvent` and a `MessageFailedEvent`.
OUTBOUND_MESSAGE_EVENT_TYPES = frozenset({"message.sent", "message.delivered", "message.failed"})

#: The events about a message somebody sent TO one of your numbers. Each
#: parses to a `MessageReceivedEvent`.
INBOUND_MESSAGE_EVENT_TYPES = frozenset({"message.received"})

#: Every `failure.cause` a `message.failed` event can carry today — the
#: values of `FailureCause`. More can be added: a cause not in this set
#: still parses, as a string, and is still a failure.
FAILURE_CAUSES: frozenset[FailureCause] = frozenset(get_args(FailureCause))

#: The header a delivery carries its signature in.
SIGNATURE_HEADER = "Ringivo-Signature"

#: How far a delivery's `t` may be from your clock, in seconds.
DEFAULT_TOLERANCE_SECONDS = 300

# Digits only, and nothing else: not a sign, not whitespace, not a unicode
# digit `int()` would happily accept but no signer would ever emit.
_TIMESTAMP = re.compile(r"\A[0-9]+\Z")


def verify(
    payload: bytes | str,
    header: str,
    secret: str,
    *,
    tolerance: int = DEFAULT_TOLERANCE_SECONDS,
    now: int | None = None,
) -> None:
    """Raise unless `payload` was signed with `secret`, recently.

    Args:
        payload: The RAW request body — the bytes as they arrived. A `str`
            is read as UTF-8 for the frameworks that hand one over.
        header: The whole `Ringivo-Signature` header value,
            `t=<unix>,v1=<hex>[,v1=<hex>]`.
        secret: Your endpoint's `whsec_` signing secret.
        tolerance: How far the delivery's timestamp may be from your clock,
            in seconds. Five minutes by default.
        now: The moment to measure against, as a Unix second. Yours by
            default; pass one to test a receiver deterministically.

    Raises:
        SignatureVerificationError: for every failure — a missing or
            malformed header, a timestamp outside the window, or no `v1`
            that matches. One exception for all of them, because a receiver
            has exactly one useful reaction, and telling a stranger WHICH
            check their forgery failed is help they should not get.

    Returns:
        None. Success is silence: a boolean invites `verify(...)` written
        without the `if`, which is a check that never runs.
    """
    body = payload.encode() if isinstance(payload, str) else bytes(payload)
    timestamp, candidates = _parse(header)

    if timestamp is None or not candidates:
        raise SignatureVerificationError(
            f"the {SIGNATURE_HEADER} header carried no timestamp and signature pair"
        )

    elapsed = abs((int(time.time()) if now is None else now) - timestamp)
    if elapsed > tolerance:
        raise SignatureVerificationError(
            f"the signature timestamp is {elapsed}s from now, outside the {tolerance}s window"
        )

    expected = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256
    ).hexdigest()

    # `compare_digest`, never `==`. A short-circuiting comparison over a hex
    # digest leaks how many leading characters were right, which is enough to
    # forge one byte at a time given enough attempts. And every candidate is
    # compared — during a rotation only one of them is signed with the secret
    # this receiver holds.
    if not any(hmac.compare_digest(expected, candidate) for candidate in candidates):
        raise SignatureVerificationError("no signature in the header matches this body and secret")


def _parse(header: str) -> tuple[int | None, tuple[str, ...]]:
    """Read `t=<unix>,v1=<hex>[,v1=<hex>]` as forgivingly as is safe.

    Unknown members are skipped rather than refused, so a future scheme
    version added beside `v1` does not break every receiver at once. A
    malformed member is simply not a member.
    """
    timestamp: int | None = None
    candidates: list[str] = []

    for part in header.split(","):
        key, separator, value = part.strip().partition("=")
        if not separator:
            continue
        if key == "t" and _TIMESTAMP.match(value):
            timestamp = int(value)
        elif key == "v1" and value:
            candidates.append(value)

    return timestamp, tuple(candidates)


def parse_message_event(payload: Any) -> MessageEvent:
    """Read a decoded `message.received`, `message.sent`, `message.delivered`
    or `message.failed` body.

    Args:
        payload: The decoded JSON body — call `verify()` on the raw bytes
            first.

    Returns:
        A `MessageEvent`: one variant, told apart by `type`:

        - `MessageReceivedEvent` for `message.received`, a message somebody
          sent to one of your numbers;
        - `MessageSentEvent` for `message.sent`: the provider accepted a
          message sent from one of your numbers;
        - `MessageDeliveredEvent` for `message.delivered`: the recipient's
          carrier took it;
        - `MessageFailedEvent` for `message.failed`, a message sent from one
          of your numbers that did not reach its recipient, with
          `message.failure_cause`;
        - `UnknownMessageEvent`, whose `type` is None, for anything else:
          another event, a type this release does not know yet, or no JSON
          object at all. The type that arrived is on `raw`.

        Members that are missing or of the wrong type are None, and the
        whole body is on `raw`, or `raw` is `{}` when the body is not a JSON
        object.

        NEVER RAISES. A receiver that answered a malformed delivery with a
        500 would only be sent it again.
    """
    return _message_event_from_json(payload)
