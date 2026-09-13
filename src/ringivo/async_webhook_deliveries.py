"""What the platform owes an endpoint, and what it gave up on — awaited.

The SIBLING of webhook_deliveries.py, method for method: each body here is
its twin's body with an `await` on the line that goes to the network. The
page reader, the noun and `faxes.py`'s path escaper are imported rather than
copied, for the reason async_fax_accounts.py gives about its own imports.

Read webhook_deliveries.py for the whys: why a successful delivery leaves no
row, why there is no `delivered` status, why `list(status="dead")` is the
query this surface exists for, and why the body that was POSTed is never
published here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .faxes import _data_object, _path_segment
from .models import WebhookDelivery, WebhookDeliveryPage
from .webhook_deliveries import _NOUN, _page

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .async_client import AsyncRingivo

__all__ = ["AsyncWebhookDeliveries"]


class AsyncWebhookDeliveries:
    """The `client.webhook_deliveries` namespace on `AsyncRingivo`."""

    def __init__(self, client: AsyncRingivo) -> None:
        self._client = client

    async def list(
        self,
        *,
        endpoint: str | None = None,
        event_type: str | None = None,
        status: str | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> WebhookDeliveryPage:
        """One page of failed or pending deliveries, newest first.

        The awaited twin of `WebhookDeliveries.list`, and the same arguments
        mean the same things: `status` is `pending` or `dead` and nothing
        else, `status="dead"` is what this collection is for, and an empty
        page means nothing is owed.

        Needs `webhooks:read`; a `fax:read` token lists only the deliveries
        of fax-account-scoped endpoints.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
            "filter[endpoint]": endpoint,
            "filter[event_type]": event_type,
            "filter[status]": status,
        }
        response = await self._client.request("GET", "/v1/webhook-deliveries", params=params)
        return _page(response.json())

    async def get(self, webhook_delivery_id: str) -> WebhookDelivery:
        """Read one delivery.

        The awaited twin of `WebhookDeliveries.get`. A delivery that
        succeeded answers 404, because a success leaves no row to read.

        Needs `webhooks:read`, or `fax:read` for a delivery of a
        fax-account-scoped endpoint.
        """
        response = await self._client.request(
            "GET",
            f"/v1/webhook-deliveries/{_path_segment(webhook_delivery_id, noun=_NOUN)}",
        )
        return WebhookDelivery._from_resource(_data_object(response.json()))
