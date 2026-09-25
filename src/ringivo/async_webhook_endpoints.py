"""Register a webhook endpoint, read one, list them, change one — awaited.

The SIBLING of webhook_endpoints.py, method for method. Each body here is
its twin's body with an `await` on the line that goes to the network;
nothing is shared between the two classes, because the only thing they
could share is the awaiting itself.

What IS shared is the module-private helpers webhook_endpoints.py already
owns — `_events_for_create`, `_events_for_update`, `_page` and the constants
— plus the `NOT_GIVEN` sentinel and `_given` from fax_accounts.py and
`_path_segment` and `_data_object` from faxes.py. Those are pure functions
of their arguments, they touch no client, and one of them (`_path_segment`)
is a security control: a second copy of it is a second thing to get wrong.
So they are imported, not duplicated.

Read webhook_endpoints.py for the whys: why the secret is readable exactly
once per secret, what a rotation's grace window is, why the write bodies are
JSON:API documents with an explicit content type, and which member of the
vendored spec is wrong about `url`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from .fax_accounts import NOT_GIVEN, _JSONAPI, NotGiven, _given
from .faxes import _data_object, _path_segment
from .models import WebhookEndpoint, WebhookEndpointPage
from .webhook_endpoints import _NOUN, _TYPE, _events_for_create, _events_for_update, _page

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .async_client import AsyncRingivo

__all__ = ["AsyncWebhookEndpoints"]


class AsyncWebhookEndpoints:
    """The `client.webhook_endpoints` namespace on `AsyncRingivo`."""

    def __init__(self, client: AsyncRingivo) -> None:
        self._client = client

    async def list(
        self,
        *,
        scope_type: str | None = None,
        scope_id: str | None = None,
        active: bool | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> WebhookEndpointPage:
        """One page of registered endpoints, newest first.

        The awaited twin of `WebhookEndpoints.list`, and the same arguments
        mean the same things. Needs `webhooks:read`; a `fax:read` token
        lists only the fax-account-scoped endpoints, and the wider ones are
        absent rather than refused.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
            "filter[scopeType]": scope_type,
            "filter[scopeId]": scope_id,
            "filter[active]": active,
        }
        response = await self._client._request_filtered("/v1/webhook-endpoints", params)
        return _page(response.json())

    async def get(self, webhook_endpoint_id: str) -> WebhookEndpoint:
        """Read one endpoint. `secret` is always None here.

        Needs `webhooks:read`, or `fax:read` for a fax-account-scoped
        endpoint — a wider one answers 404 to a `fax:*` token, exactly as an
        id that names nothing does.
        """
        response = await self._client.request(
            "GET",
            f"/v1/webhook-endpoints/{_path_segment(webhook_endpoint_id, noun=_NOUN)}",
        )
        return WebhookEndpoint._from_resource(_data_object(response.json()))

    async def create(
        self,
        *,
        url: str,
        scope_type: str,
        scope_id: str,
        events: Sequence[str],
        active: bool | NotGiven = NOT_GIVEN,
    ) -> WebhookEndpoint:
        """Register an endpoint, and read its signing secret for the only time.

        The awaited twin of `WebhookEndpoints.create`: same arguments, same
        meanings, and the same rule that matters most — **the returned
        `secret` is the only copy you will ever be handed, so store it now;
        there is no way to read it back.** `events` is REQUIRED and must
        name at least one event type: `None` and `[]` are each refused
        before the request is built, exactly as the platform refuses them.

        Raises:
            ValueError: `events` was one string rather than a list of names.
                A str is a `Sequence[str]`, so it would be read one
                character at a time — the refusal `_events_for_create`
                explains.
            ValueError: `events` was `None` or `[]`.

        Needs `webhooks:write`, or `fax:write` for a `fax_account`-scoped
        endpoint only: naming a `customer` or `tenant` scope with a `fax:*`
        token is a 422.
        """
        attributes: dict[str, Any] = {
            "url": url,
            "scopeType": scope_type,
            "scopeId": scope_id,
            "events": _events_for_create(events),
        }
        attributes.update(_given({"active": active}))

        document = {"data": {"type": _TYPE, "attributes": attributes}}

        response = await self._client.request(
            "POST",
            "/v1/webhook-endpoints",
            accept=_JSONAPI,
            headers={"Content-Type": _JSONAPI},
            json=document,
        )
        return WebhookEndpoint._from_resource(_data_object(response.json()))

    async def update(
        self,
        webhook_endpoint_id: str,
        *,
        url: str | NotGiven = NOT_GIVEN,
        events: Sequence[str] | NotGiven = NOT_GIVEN,
        active: bool | NotGiven = NOT_GIVEN,
    ) -> WebhookEndpoint:
        """Change an endpoint's URL, its event list, or its switch.

        A SPARSE PATCH, exactly as `WebhookEndpoints.update` describes: only
        the arguments you pass are sent, so adding an event is
        `update(id, events=[...])` and nothing else moves. The list REPLACES
        the old one and must still name at least one: `[]` is refused, and
        `None` is not sent as `null` — passing it alone is the same as
        naming nothing. `scope_type` and `scope_id` cannot change.

        Raises:
            ValueError: No member was named — a bare `events=None` with
                nothing else named lands here too — or `events` was one
                string rather than a list of names, or `[]`.

        Needs `webhooks:write`, or `fax:write` for a fax-account-scoped
        endpoint.
        """
        attributes = _given({"url": url, "events": _events_for_update(events), "active": active})
        if not attributes:
            raise ValueError(
                "update() needs at least one member to change: url=, events= or active=."
            )

        document = {"data": {"type": _TYPE, "id": webhook_endpoint_id, "attributes": attributes}}

        response = await self._client.request(
            "PATCH",
            f"/v1/webhook-endpoints/{_path_segment(webhook_endpoint_id, noun=_NOUN)}",
            accept=_JSONAPI,
            headers={"Content-Type": _JSONAPI},
            json=document,
        )
        return WebhookEndpoint._from_resource(_data_object(response.json()))

    async def delete(self, webhook_endpoint_id: str) -> None:
        """Remove an endpoint. The fan-out stops; the delivery record stays.

        The awaited twin of `WebhookEndpoints.delete`. Needs
        `webhooks:write`, or `fax:write` for a fax-account-scoped endpoint.
        """
        await self._client.request(
            "DELETE",
            f"/v1/webhook-endpoints/{_path_segment(webhook_endpoint_id, noun=_NOUN)}",
        )

    async def rotate_secret(self, webhook_endpoint_id: str) -> WebhookEndpoint:
        """Mint a new signing secret, and start the grace window.

        The awaited twin of `WebhookEndpoints.rotate_secret`, including the
        parts that matter: the returned `secret` is the new one and the only
        copy you get, the PREVIOUS secret goes on signing until
        `secret_previous_expires_at`, and `webhooks.verify()` accepts either
        while both are live. Sends no body.

        Needs `webhooks:write`, or `fax:write` for a fax-account-scoped
        endpoint.
        """
        response = await self._client.request(
            "POST",
            f"/v1/webhook-endpoints/{_path_segment(webhook_endpoint_id, noun=_NOUN)}/rotate-secret",
            accept=_JSONAPI,
        )
        return WebhookEndpoint._from_resource(_data_object(response.json()))
