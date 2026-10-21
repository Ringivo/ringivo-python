"""Record a text your own system already sent — awaited.

The SIBLING of messages.py. The body rules, the label rule and the timeout
floor are messages.py's own pure helpers, imported rather than copied, so
the two clients cannot drift. Read messages.py for the whys.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING

from .messages import _JSONAPI, _PATH, _record_body, _record_timeout, _recorded
from .models import OutboundMessage

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .async_client import AsyncRingivo

__all__ = ["AsyncMessages"]


class AsyncMessages:
    """The `client.messages` namespace on `AsyncRingivo`. Needs `messages:record`."""

    def __init__(self, client: AsyncRingivo) -> None:
        self._client = client

    async def record(
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
        """Record one text you already sent. See `Messages.record()`."""
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
        response = await self._client.request(
            "POST",
            _PATH,
            accept=_JSONAPI,
            headers={"Content-Type": _JSONAPI},
            json=document,
            timeout=_record_timeout(self._client._timeout),
        )
        return _recorded(response.json(), response.status_code)
