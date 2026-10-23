"""Read the text messages (SMS and MMS) somebody sent to your numbers.

    page = client.inbound_messages.list(number="+13215550101")
    for message in page:
        print(message.from_, message.body)

-- THE POLLING HALF OF A PAIR ---------------------------------------------------
The other half is the `message.received` webhook (webhooks.py): register an
endpoint and your backend is told as each message arrives. Read this
collection to catch up on what you missed while your endpoint was down, or
instead of a webhook when you have no public callback URL. The webhook's
`message.id` is this collection's id, so `get()` reads the message back.

-- TWO TIMESTAMPS ---------------------------------------------------------------
`received_at` is when the message was SENT, and `created_at` is when the
platform stored it; they differ by however long a redelivery took. The date
filters match `received_at`, and the cursor walks `created_at`.

-- MEDIA: DESCRIBED, AND LINKED WHEN THE PLATFORM HOLDS THE FILE ---------------
Each media item names its content type, filename and size. When the
platform holds the file — the number is connected to your phone system —
the item also carries `content_url`, a signed link on your API host that
works for five minutes (`expires_at`), and `download_media()` fetches it.
Every read makes new links, so read the message again for a fresh one.
An item the platform does not hold (any other number, the message's text,
a file larger than 10 MB) has no link: ask your messaging provider for it.

The webhook's media items have no link: a webhook body can reach logs, and
a retry can arrive after a link died. Read the message with `get()`.

-- THE DOWNLOAD SENDS NO TOKEN --------------------------------------------------
`download_media()` follows the link through the client's UNAUTHENTICATED
downloads connection, the one `faxes.media()` uses (client.py explains
why). The link is on your own API host, but it reads one file, briefly; the
bearer token reads every message this client can reach, and never travels
with it. A changed or expired link is an `ApiError` with status 403, a file
the platform no longer holds is a 404 `not_found`, and downloads count
against the API rate limit (a 429 with `retry_after`).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from .faxes import _data_object, _next_cursor, _next_link, _path_segment
from .models import InboundMessage, InboundMessageMediaWithLink, InboundMessagePage

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .client import Ringivo

__all__ = ["InboundMessages"]

_PATH = "/v1/inbound-messages"

#: What `_path_segment` calls this resource in its refusal.
_NOUN = "inbound message"

_BARE_STRING_IDS = (
    "ids must be a list of message ids, not one string: a str is read one "
    "character at a time, so it asks for one-character ids the platform "
    'matches none of. Pass ids=["<id>"].'
)


def _id_filter(ids: Sequence[str] | None) -> tuple[str, ...] | None:
    """The `filter[id][]` value: one id per pair, or the parameter left off.

    The rule of customers.py's `_id_filter`, with this resource's noun in
    the refusal: one bare string is refused, because a str is a
    `Sequence[str]` and would be read one character at a time; the tuple is
    built before the emptiness check, so a one-shot iterable is read once;
    and an empty sequence leaves the parameter off.
    """
    if isinstance(ids, str):
        raise ValueError(_BARE_STRING_IDS)
    if ids is None:
        return None
    return tuple(ids) or None


def _content_url(item: InboundMessageMediaWithLink) -> str:
    """The link `download_media()` follows, or a refusal before any request.

    Shared by both clients so the two refuse the same things in the same
    words. A webhook item is refused by its class, not by a missing
    attribute, so the refusal can name the way to a link: `get()`.
    """
    if not isinstance(item, InboundMessageMediaWithLink):
        raise TypeError(
            f"download_media() takes a media item of an InboundMessage, not a "
            f"{type(item).__name__}. A message.received media item has no download "
            f"link: read the message with client.inbound_messages.get() and download "
            f"one of its media items"
        )
    if item.content_url is None:
        raise ValueError(
            "this media item has no download link: the platform does not hold the file. "
            "The number is not connected to your phone system, the item is the "
            "message's text, or the file was not kept (for example, it is larger than "
            "10 MB). For a customer-scoped credential, the file can also be one kept "
            "for another customer. Ask your messaging provider for the file."
        )
    return item.content_url


def _params(
    *,
    number: str | None,
    from_: str | None,
    kind: str | None,
    received_after: str | None,
    received_before: str | None,
    ids: Sequence[str] | None,
    after: str | None,
    before: str | None,
    page_size: int | None,
) -> dict[str, Any]:
    """The list query. Shared by both clients so the two cannot drift."""
    return {
        "page[after]": after,
        "page[before]": before,
        "page[size]": page_size,
        "filter[number]": number,
        "filter[from]": from_,
        "filter[kind]": kind,
        "filter[receivedAfter]": received_after,
        "filter[receivedBefore]": received_before,
        # One `filter[id][]=<id>` pair per id — the only shape the platform
        # reads as a list (customers.py explains the other two).
        "filter[id][]": _id_filter(ids),
    }


class InboundMessages:
    """The `client.inbound_messages` namespace.

    Needs `numbers:read` or `numbers:messaging`.
    """

    def __init__(self, client: Ringivo) -> None:
        self._client = client

    def list(
        self,
        *,
        number: str | None = None,
        from_: str | None = None,
        kind: str | None = None,
        received_after: str | None = None,
        received_before: str | None = None,
        ids: Sequence[str] | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> InboundMessagePage:
        """One page of received messages, newest first.

        Args:
            number: Only messages sent TO this number of yours, in E.164.
            from_: Only messages from this sender, in E.164.
            kind: `sms` or `mms`.
            received_after: Messages received at or after this instant,
                ISO-8601. A value that is not a date matches NOTHING rather
                than being ignored.
            received_before: Messages received at or before this instant.
                Both ends are inclusive.
            ids: Read several messages by id in one request. One bare
                string is refused with `ValueError`, as on
                `customers.list()`.
            after: Walk forward: the previous page's
                `InboundMessagePage.next_cursor`. Mutually exclusive with
                `before` — passing both is refused with a 400.
            before: Walk backward from a cursor.
            page_size: Rows per page. The default is 25 and the ceiling is
                100.

        Needs `numbers:read` or `numbers:messaging`.
        """
        params = _params(
            number=number,
            from_=from_,
            kind=kind,
            received_after=received_after,
            received_before=received_before,
            ids=ids,
            after=after,
            before=before,
            page_size=page_size,
        )
        document = self._client.request("GET", _PATH, params=params).json()
        return _page(document)

    def get(self, inbound_message_id: str) -> InboundMessage:
        """Read one received message, exactly as the list serves it.

        A message sent to a number you do not carry text messaging for is
        not yours and answers 404.

        Needs `numbers:read` or `numbers:messaging`.
        """
        response = self._client.request(
            "GET",
            f"{_PATH}/{_path_segment(inbound_message_id, noun=_NOUN)}",
        )
        return InboundMessage._from_resource(_data_object(response.json()))

    def download_media(self, item: InboundMessageMediaWithLink) -> bytes:
        """The bytes of one media item: follow its `content_url`.

        The download goes out with NO `Authorization` header, through the
        same unauthenticated connection as `faxes.media()`. The link is
        followed exactly as the API minted it.

        Args:
            item: A media item of a message read with `list()` or `get()`.

        Raises:
            ValueError: The item has no link (`content_url` is None): the
                platform does not hold the file. No request is sent.
            TypeError: The item is a `message.received` webhook item, which
                never has a link. Read the message with `get()` first.
            ApiError: 403 when the link expired (`expires_at` passed) or was
                changed — read the message again for a fresh link; 404
                `not_found` when the platform no longer holds the file; 429
                with `retry_after` when downloads hit the API rate limit.

        No scope is needed for the download itself: the link is the
        authorization.
        """
        return self._client._download(_content_url(item))


def _page(document: Any) -> InboundMessagePage:
    """One `GET /v1/inbound-messages` body, as the page this package hands back."""
    if not isinstance(document, Mapping):
        document = {}

    data = document.get("data")
    messages = tuple(
        InboundMessage._from_resource(item)
        for item in (data if isinstance(data, list) else [])
        if isinstance(item, Mapping)
    )
    return InboundMessagePage(
        messages=messages,
        next_url=_next_link(document),
        next_cursor=_next_cursor(document),
        raw=document,
    )
