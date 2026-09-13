"""What the platform still owes an endpoint, and what it gave up on.

-- THIS IS EVIDENCE OF FAILURE, NOT A DELIVERY HISTORY -------------------------
A delivery that reaches your endpoint leaves NO ROW HERE. A row appears when
an attempt fails, moves along the retry ladder as later attempts fail, and is
removed the moment one succeeds. So this collection answers exactly one
question — what do we still owe you, and what did we give up on — and an
empty page is the good news.

Read it that way and the two statuses follow: `pending` is still on the
ladder, and `dead` ran out of rungs. **There is no `delivered`.** The
collection used to publish one; `filter[status]="delivered"` is now refused
with a 400 rather than quietly ignored, which is why `list()` passes the
caller's value through instead of validating a vocabulary of its own — the
API's refusal names the real answer, and a second copy of the enum here
would go stale on its own.

`list(status="dead")` IS THE QUERY THIS SURFACE EXISTS FOR. Delivery is
at-least-once with a dead letter, so "we tried and gave up" is a state that
is reached without your server ever hearing about it. After an outage this is
where you learn what you missed.

-- WHAT IT DOES NOT CARRY -----------------------------------------------------
The body that was POSTed is never published here — only `payload_sha256`, the
digest of the exact bytes that were signed. An integrator who kept what they
received can prove it is what was sent; nobody who can only read this
collection learns the contents of somebody's fax.

For proof that one specific event arrived, use your own receipt instead:
every POST carries an event id, and the resource itself can be re-fetched.

-- NO `include` WRAPPER -------------------------------------------------------
The API can side-load the endpoint a delivery was for (`include=endpoint`).
This module does not wrap it: `WebhookDelivery.endpoint_id` is the id, and
`webhook_endpoints.get()` reads the endpoint. `client.request()` is there for
a caller who wants the side-loaded document itself.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from .faxes import _data_object, _next_cursor, _next_link, _path_segment
from .models import WebhookDelivery, WebhookDeliveryPage

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .client import Ringivo

__all__ = ["WebhookDeliveries"]

#: What `_path_segment` calls this resource in its refusal.
_NOUN = "webhook delivery"


class WebhookDeliveries:
    """The `client.webhook_deliveries` namespace."""

    def __init__(self, client: Ringivo) -> None:
        self._client = client

    def list(
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

        An empty page means nothing is owed and nothing was given up on — a
        delivery that lands leaves no row at all (module docstring).

        Args:
            endpoint: Only this endpoint's deliveries.
            event_type: Only this event name, e.g. `fax.received`.
            status: `pending` — still on the retry ladder — or `dead`, which
                ran out of rungs. **There is no `delivered`**: the API
                answers 400 to it rather than ignoring it.
            after: Walk forward: the previous page's
                `WebhookDeliveryPage.next_cursor`. Mutually exclusive with
                `before` — passing both is refused with a 400.
            before: Walk backward from a cursor.
            page_size: Rows per page. The default is 25 and the ceiling is
                100.

        `status="dead"` is what this collection is for: it is the list of
        what an outage cost you, and the only place that list exists.

        Needs `webhooks:read`. A delivery borrows its endpoint's reach, so a
        `fax:read` token lists only the deliveries of FAX-ACCOUNT-SCOPED
        endpoints — the rest are absent from its page rather than refused.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
            "filter[endpoint]": endpoint,
            "filter[event_type]": event_type,
            "filter[status]": status,
        }
        document = self._client.request("GET", "/v1/webhook-deliveries", params=params).json()
        return _page(document)

    def get(self, webhook_delivery_id: str) -> WebhookDelivery:
        """Read one delivery.

        A delivery of an endpoint your token cannot reach answers 404, the
        same as an id that names nothing anywhere — and so does one that
        succeeded, because a success leaves no row to read.

        Needs `webhooks:read`, or `fax:read` for a delivery of a
        fax-account-scoped endpoint.
        """
        response = self._client.request(
            "GET",
            f"/v1/webhook-deliveries/{_path_segment(webhook_delivery_id, noun=_NOUN)}",
        )
        return WebhookDelivery._from_resource(_data_object(response.json()))


def _page(document: Any) -> WebhookDeliveryPage:
    """One `GET /v1/webhook-deliveries` body, as the page this package hands back."""
    if not isinstance(document, Mapping):
        document = {}

    data = document.get("data")
    deliveries = tuple(
        WebhookDelivery._from_resource(item)
        for item in (data if isinstance(data, list) else [])
        if isinstance(item, Mapping)
    )
    return WebhookDeliveryPage(
        deliveries=deliveries,
        next_url=_next_link(document),
        next_cursor=_next_cursor(document),
        raw=document,
    )
