"""Read the messages somebody sent to your numbers — awaited.

The SIBLING of inbound_messages.py, method for method: each body here is
its twin's body with an `await` on the line that goes to the network. The
query builder, the page reader, the noun and faxes.py's path escaper are
imported rather than copied, so the two clients cannot drift.

Read inbound_messages.py for the whys: the `message.received` webhook is
the push half of this collection, `received_at` is when the message was
sent, and media is described, never carried.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from .faxes import _data_object, _path_segment
from .inbound_messages import _NOUN, _PATH, _page, _params
from .models import InboundMessage, InboundMessagePage

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .async_client import AsyncRingivo

__all__ = ["AsyncInboundMessages"]


class AsyncInboundMessages:
    """The `client.inbound_messages` namespace on `AsyncRingivo`.

    Needs `numbers:read` or `numbers:messaging`.
    """

    def __init__(self, client: AsyncRingivo) -> None:
        self._client = client

    async def list(
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

        The awaited twin of `InboundMessages.list`; the same arguments mean
        the same things.
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
        response = await self._client.request("GET", _PATH, params=params)
        return _page(response.json())

    async def get(self, inbound_message_id: str) -> InboundMessage:
        """Read one received message. The awaited twin of `InboundMessages.get`."""
        response = await self._client.request(
            "GET",
            f"{_PATH}/{_path_segment(inbound_message_id, noun=_NOUN)}",
        )
        return InboundMessage._from_resource(_data_object(response.json()))
