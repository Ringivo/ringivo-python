"""Record a text your own system already sent, so staff see it in their threads.

    recorded = client.messages.record(
        from_="+14075550142",
        to="+13215550187",
        body="Reminder: Rex is due for his rabies booster on Oct 24.",
        sender_label="Appointment reminder",
        provider_message_id="01JC8ZA1F5T3R8C2P6M0L4JSWQ",
        provider_part_ids=["01JC8ZA1F5T3R8C2P6M0L4JSWQ"],
        sent_at=datetime(2026, 10, 19, 15, 2, 44, tzinfo=timezone.utc),
    )

`POST /v1/outbound-messages` with `alreadySent`. The platform sends nothing:
the text already left through your own messaging-provider account, and the
call files it in the conversation with your label in front of it.

-- NO IDEMPOTENCY-KEY ------------------------------------------------------------
The provider message id IS the key, by contract. A repeat with the same id
and the same `from`, `to`, `body` and media count answers 200 with the
first record and stores nothing new; `OutboundMessage.replayed` is then
True. A repeat with different content is a 409. So a retry is the same call
with the same arguments — and NEW presigned media links, because the
platform fetches the media during the call and never fetches a link again.

-- MEDIA ------------------------------------------------------------------------
`media_urls` links to MEDIA ITEMS of any type: an image, a contact card
(vCard), audio, video, a PDF or any other file. They go on the wire as
`mediaUrls`. Each is copied into the staff threads as you sent it. The
API's limits: at most 10 media items, at most 10 MB each and at most 20 MB
together. It refuses `text/plain` (put the text in `body`), a SMIL layout,
HTML, XML, SVG and script, by the declared type and by the file's own
first bytes. Only the count and the `https` scheme are checked here — the
type and the size are known only once the API fetches the link, so those
refusals come from the API. The answer describes the media in
`OutboundMessage.media` (content type and size), never with your links.

If any link fails, nothing is stored. The `ApiError` names the link in
`errors[0].source["pointer"]` (`/data/attributes/mediaUrls/<index>`) and
the reason in `code`:

- 422 `media_rejected`: the link or what it served can never be used. Fix
  the link; do not retry it unchanged.
- 504 `media_timeout`: the link did not finish within 10 seconds.
- 502 `media_unreachable`: its host answered 5xx, refused the connection,
  or does not resolve.
- 503 `media_store_unavailable`: the platform could not keep the media
  right now.

The last three carry `Retry-After` and `is_retryable()` is True for them:
retry after `retry_after` seconds, with NEW links for the first two.

-- REFUSED BEFORE ANY REQUEST -----------------------------------------------------
What the API would answer with a 422 that no retry can fix is a
`ValueError` here instead, before a request goes out — the same rule as the
empty-page refusal in faxes.py: an empty provider message id or part-id
list, a `sent_at` without a time zone, a text with neither a body nor a
media link, more than ten media links, a link that is not `https`, and a
label that breaks the label rule. A `ValueError` is never worth retrying,
and your queue should not see it as an API failure.

-- THE LABEL RULE ---------------------------------------------------------------
Staff see every recorded text as `"<label>: <body>"`. After trimming the
white space at both ends, a label is one line (no control character, no
line or paragraph separator), has at least one visible character (a letter,
digit, punctuation mark or symbol) and is 1 to 40 Unicode code points
long. `record()` REFUSES a label that breaks the rule; it never changes your
label silently. `sender_label()` below is the helper that MAKES any text —
a person's name, say — into a label that keeps the rule.

The API also limits the label, a colon, a space and the body together to
1024 code points. That limit is not checked here, because the API counts it
after its own trim; a text over it is a 422.

-- THE TIMEOUT -----------------------------------------------------------------
The call fetches your media before it answers: all links at once, each
within 10 seconds, and then stores up to 20 MB. The API ends any request
at 30 seconds. A client built with a shorter timeout would give up on a
call that was about to succeed; the retry is then answered 200, but it
fetches the media again. So this one call waits at least
`RECORD_MIN_TIMEOUT_SECONDS` (30), whatever the client's own timeout is; a
longer client timeout is kept. A client built
with an `httpx.Timeout` has its read timeout raised and its connect, write
and pool timeouts kept (`_record_timeout`).
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

import httpx

from ._generated_types import OutboundMessageRecordRequest
from .models import OutboundMessage

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .client import Ringivo

__all__ = [
    "MAX_MEDIA",
    "MAX_PROVIDER_ID_LENGTH",
    "MAX_SENDER_LABEL_CODE_POINTS",
    "RECORD_MIN_TIMEOUT_SECONDS",
    "Messages",
    "sender_label",
]

#: The longest label the API accepts, in Unicode code points — the spec's
#: `senderLabel.maxLength` (tests/test_messages.py reads it from the spec).
MAX_SENDER_LABEL_CODE_POINTS = 40

#: The most media links one record may carry — the spec's `mediaUrls.maxItems`.
MAX_MEDIA = 10

#: The longest provider message id or part id — the spec's `maxLength`.
MAX_PROVIDER_ID_LENGTH = 128

#: The shortest timeout `record()` uses: the API's own cut for any request.
#: It fetches every media link at once, each within 10 seconds, then stores
#: the media, all before it answers.
RECORD_MIN_TIMEOUT_SECONDS = 30.0

#: What the record call sends and accepts. `client.JSONAPI_MEDIA_TYPE` is the
#: same string; this module cannot import it (client imports this module).
_JSONAPI = "application/vnd.api+json"

_PATH = "/v1/outbound-messages"

#: What the API trims as white space besides the `Z` categories: what its
#: `\s` matches — space, tab, LF, VT, FF, CR, and U+0085 (NEL; the API's
#: PCRE trims it at either end, so "\x85Rex" is accepted as "Rex"). NOT
#: U+001C–U+001F: Python's `str.isspace()` counts those four `Cc` separators
#: as space, the API's regex does not, so a label padded with one is a
#: control character there, and must be one here too.
_ASCII_SPACE = frozenset(" \t\n\x0b\x0c\r\x85")

#: The two separators that end a line without being `Cc` characters.
_LINE_BREAKS = frozenset({" ", " "})


def _is_space(character: str) -> bool:
    """White space as the API trims it (`[\\s\\p{Z}]`): ASCII white space,
    U+0085, and the Unicode separators (`Zs`, `Zl`, `Zp`)."""
    return character in _ASCII_SPACE or unicodedata.category(character).startswith("Z")


def _breaks_line(character: str) -> bool:
    return unicodedata.category(character) == "Cc" or character in _LINE_BREAKS


def _is_visible(character: str) -> bool:
    """A letter, digit, punctuation mark or symbol (`L`, `N`, `P`, `S`)."""
    return unicodedata.category(character)[0] in "LNPS"


def _trimmed(text: str) -> str:
    start, end = 0, len(text)
    while start < end and _is_space(text[start]):
        start += 1
    while end > start and _is_space(text[end - 1]):
        end -= 1
    return text[start:end]


def _label_refusal(label: str) -> str | None:
    """Why this label breaks the rule, or None when it keeps it.

    The checks are the API's, in the API's order, on the trimmed label.
    """
    trimmed = _trimmed(label)
    if not trimmed:
        return "the sender label is empty: give the label staff see in front of the text"
    if any(_breaks_line(character) for character in trimmed):
        return "the sender label must be one line, with no newline or other control character"
    if not any(_is_visible(character) for character in trimmed):
        return (
            "the sender label must have at least one visible character: a letter, a digit, "
            "a punctuation mark or a symbol"
        )
    if len(trimmed) > MAX_SENDER_LABEL_CODE_POINTS:
        return (
            f"the sender label must be at most {MAX_SENDER_LABEL_CODE_POINTS} characters "
            f"(Unicode code points); it is {len(trimmed)}"
        )
    return None


def sender_label(text: str) -> str:
    """Make any text a label that keeps the label rule.

    Every control character and line break becomes a space, every run of
    white space becomes one space, the ends are trimmed, and the result is
    cut to `MAX_SENDER_LABEL_CODE_POINTS` code points (and trimmed again,
    so a cut never ends on a space).

    Raises:
        ValueError: nothing visible is left — the text was empty, white
            space, or invisible characters only. There is no label to make,
            so choose your own fallback.
    """
    spaced = "".join(" " if _breaks_line(character) else character for character in text)

    words: list[str] = []
    current: list[str] = []
    for character in spaced:
        if _is_space(character):
            if current:
                words.append("".join(current))
                current = []
        else:
            current.append(character)
    if current:
        words.append("".join(current))

    label = _trimmed(" ".join(words)[:MAX_SENDER_LABEL_CODE_POINTS])
    if not any(_is_visible(character) for character in label):
        raise ValueError("no visible character is left to make a sender label from")
    return label


def _record_body(
    *,
    from_: str,
    to: str,
    body: str | None,
    sender_label: str,
    provider_message_id: str,
    provider_part_ids: Sequence[str],
    sent_at: datetime,
    media_urls: Sequence[str],
    mark_conversation_read: bool,
) -> OutboundMessageRecordRequest:
    """The JSON:API request document, after every pre-request refusal.

    Shared by `Messages.record()` and `AsyncMessages.record()`: the rules
    are pure functions of the arguments and must not drift between the two
    clients.
    """
    if not provider_message_id:
        raise ValueError("provider_message_id is required: it is the key a retry is matched on")
    if len(provider_message_id) > MAX_PROVIDER_ID_LENGTH:
        raise ValueError(
            f"provider_message_id must be at most {MAX_PROVIDER_ID_LENGTH} characters; "
            f"it is {len(provider_message_id)}"
        )
    if isinstance(provider_part_ids, str):
        raise ValueError(
            "provider_part_ids must be a list of part ids, not one string; a one-part text "
            "names its own id: [provider_message_id]"
        )
    part_ids = list(provider_part_ids)
    if not part_ids or not all(isinstance(part, str) and part for part in part_ids):
        raise ValueError(
            "provider_part_ids must name every part id your provider returned, at least one; "
            "a one-part text names its own id"
        )
    if any(len(part) > MAX_PROVIDER_ID_LENGTH for part in part_ids):
        raise ValueError(
            f"every provider part id must be at most {MAX_PROVIDER_ID_LENGTH} characters"
        )
    if len(set(part_ids)) != len(part_ids):
        raise ValueError("provider_part_ids must not repeat a part id")
    if sent_at.tzinfo is None or sent_at.utcoffset() is None:
        raise ValueError(
            "sent_at must carry a time zone: a naive datetime is a different instant on "
            "every machine that reads it"
        )
    if isinstance(media_urls, str):
        raise ValueError("media_urls must be a list of links, not one string")
    links = list(media_urls)
    if len(links) > MAX_MEDIA:
        raise ValueError(f"a record carries at most {MAX_MEDIA} media links; got {len(links)}")
    for index, link in enumerate(links):
        if urlsplit(link).scheme != "https" or not urlsplit(link).netloc:
            raise ValueError(f"media_urls[{index}] must be an https link")
    if not body and not links:
        raise ValueError("a recorded text needs a body or at least one media link")
    refusal = _label_refusal(sender_label)
    if refusal is not None:
        raise ValueError(refusal)

    # Built inline against the generated `OutboundMessageRecordRequest`, so
    # pyright checks every member name and type against the spec (its
    # attributes block is `closed`: an unknown member is a type error).
    return {
        "data": {
            "type": "outbound-messages",
            "attributes": {
                "from": from_,
                "to": to,
                "body": body,
                "mediaUrls": links,
                "senderLabel": sender_label,
                "markConversationRead": mark_conversation_read,
                "alreadySent": {
                    "providerMessageId": provider_message_id,
                    "providerPartIds": part_ids,
                    "sentAt": _instant(sent_at),
                },
            },
        }
    }


def _instant(value: datetime) -> str:
    """An aware datetime as the UTC ISO-8601 instant the API reads."""
    text = value.astimezone(timezone.utc).isoformat()
    return f"{text[:-6]}Z" if text.endswith("+00:00") else text


def _record_timeout(
    client_timeout: float | httpx.Timeout | None,
) -> float | httpx.Timeout | None:
    """The client's own timeout, raised to the floor; None (no timeout) is kept.

    A client may be built with a number or with an `httpx.Timeout`. A
    number is one timeout for every phase and is raised as a whole. A
    `Timeout` is raised in its READ phase only — the wait for the answer,
    which is where the API spends its media fetches — and its
    connect, write and pool timeouts stay the caller's. A read phase of
    None (no read timeout) is kept, as a None client timeout is.
    """
    if client_timeout is None:
        return None
    if isinstance(client_timeout, httpx.Timeout):
        read = client_timeout.read
        return httpx.Timeout(
            connect=client_timeout.connect,
            read=None if read is None else max(read, RECORD_MIN_TIMEOUT_SECONDS),
            write=client_timeout.write,
            pool=client_timeout.pool,
        )
    return max(client_timeout, RECORD_MIN_TIMEOUT_SECONDS)


def _recorded(payload: Any, status_code: int) -> OutboundMessage:
    data = payload.get("data") if isinstance(payload, Mapping) else None
    message = OutboundMessage._from_resource(data if isinstance(data, Mapping) else {})
    return replace(message, replayed=status_code == 200)


class Messages:
    """The `client.messages` namespace. Needs the `messages:record` scope."""

    def __init__(self, client: Ringivo) -> None:
        self._client = client

    def record(
        self,
        *,
        from_: str,
        to: str,
        sender_label: str,
        provider_message_id: str,
        provider_part_ids: Sequence[str],
        sent_at: datetime,
        body: str | None = None,
        media_urls: Sequence[str] = (),
        mark_conversation_read: bool = False,
    ) -> OutboundMessage:
        """Record one text you already sent.

        Args:
            from_: Your number that sent it, in E.164, on your own
                messaging-provider account.
            to: The one recipient, in E.164.
            sender_label: What staff see in front of the text. It must keep
                the label rule (module docstring); `sender_label()` makes
                one from any text.
            provider_message_id: Your provider's id for the text — the
                dedupe key. A retry passes the same one.
            provider_part_ids: Every part id your provider returned. A
                one-part text names its own id.
            sent_at: When your provider accepted the text. Must carry a
                time zone.
            body: The text as you sent it. Required unless `media_urls`
                names a media item.
            media_urls: Up to ten `https` links to the media you sent, in
                order — any type but plain text, at most 10 MB each and
                20 MB together (module docstring). Make NEW presigned
                links for each attempt: they are all fetched at once
                during this call, each within 10 seconds, and never again.
            mark_conversation_read: True marks the staff threads read — for
                a reply a person typed in your own inbox. False (the
                default) leaves the read marks as they were.

        Returns:
            The record. `replayed` is True when the answer was 200 — a
            repeat of an earlier record, returned unchanged.

        Raises:
            ValueError: before any request, for what the API would refuse
                with a 422 that no retry can fix.
            ApiError: the API refused. Retry only what `is_retryable()`
                says is retryable, after `retry_after` when it is set. A
                media link that failed is named by `code` and
                `source["pointer"]` (module docstring).
        """
        document = _record_body(
            from_=from_,
            to=to,
            body=body,
            sender_label=sender_label,
            provider_message_id=provider_message_id,
            provider_part_ids=provider_part_ids,
            sent_at=sent_at,
            media_urls=media_urls,
            mark_conversation_read=mark_conversation_read,
        )
        response = self._client.request(
            "POST",
            _PATH,
            accept=_JSONAPI,
            headers={"Content-Type": _JSONAPI},
            json=document,
            timeout=_record_timeout(self._client._timeout),
        )
        return _recorded(response.json(), response.status_code)
