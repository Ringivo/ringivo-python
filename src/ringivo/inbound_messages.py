"""Read the text and picture messages somebody sent to your numbers.

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

-- ATTACHMENTS ARE DESCRIBED, NEVER CARRIED -------------------------------------
Each part names its content type, filename, encoding and size. There is no
file and no URL: the platform does not keep the bytes, so ask your
messaging provider for the file.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from .faxes import _data_object, _next_cursor, _next_link, _path_segment
from .models import InboundMessage, InboundMessagePage

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
