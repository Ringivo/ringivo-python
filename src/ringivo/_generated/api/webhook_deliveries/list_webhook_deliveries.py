from http import HTTPStatus
from typing import Any
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.list_webhook_deliveries_include import ListWebhookDeliveriesInclude
from ...models.webhook_delivery_collection_document import WebhookDeliveryCollectionDocument
from ...models.webhook_delivery_status import WebhookDeliveryStatus
from ...models.webhook_event_type import WebhookEventType
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    pagecursor: str | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    include: ListWebhookDeliveriesInclude | Unset = UNSET,
    filterendpoint: UUID | Unset = UNSET,
    filterevent_type: WebhookEventType | Unset = UNSET,
    filterstatus: WebhookDeliveryStatus | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["page[cursor]"] = pagecursor

    params["page[size]"] = pagesize

    json_include: str | Unset = UNSET
    if not isinstance(include, Unset):
        json_include = include.value

    params["include"] = json_include

    json_filterendpoint: str | Unset = UNSET
    if not isinstance(filterendpoint, Unset):
        json_filterendpoint = str(filterendpoint)
    params["filter[endpoint]"] = json_filterendpoint

    json_filterevent_type: str | Unset = UNSET
    if not isinstance(filterevent_type, Unset):
        json_filterevent_type = filterevent_type.value

    params["filter[event_type]"] = json_filterevent_type

    json_filterstatus: str | Unset = UNSET
    if not isinstance(filterstatus, Unset):
        json_filterstatus = filterstatus.value

    params["filter[status]"] = json_filterstatus

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/webhook-deliveries",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDocument | WebhookDeliveryCollectionDocument | None:
    if response.status_code == 200:
        response_200 = WebhookDeliveryCollectionDocument.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = ErrorDocument.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = ErrorDocument.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ErrorDocument.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = ErrorDocument.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDocument | WebhookDeliveryCollectionDocument]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    pagecursor: str | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    include: ListWebhookDeliveriesInclude | Unset = UNSET,
    filterendpoint: UUID | Unset = UNSET,
    filterevent_type: WebhookEventType | Unset = UNSET,
    filterstatus: WebhookDeliveryStatus | Unset = UNSET,
) -> Response[ErrorDocument | WebhookDeliveryCollectionDocument]:
    r"""List webhook deliveries

     Read-only evidence about your endpoints — what we owed each one, and what became of it.

    **`filter[status]=dead` is the query this collection exists for.** Delivery is at-least-once
    with a dead-letter, so \"we tried and gave up\" is a state that is reached without your server
    ever hearing about it; this is where you learn what you missed after an outage. An unknown
    status value is refused with a 400 rather than ignored.

    The body we POSTed is never published here — only its `payloadSha256` digest, so an
    integrator who kept what they received can prove it is what we sent.

    **Scope:** a delivery borrows its endpoint's reach, so `fax:read` lists only the deliveries
    of **fax-account-scoped** endpoints; the deliveries of customer- and tenant-scoped endpoints
    require `webhooks:read`.

    Args:
        pagecursor (str | Unset):
        pagesize (int | Unset):
        include (ListWebhookDeliveriesInclude | Unset):
        filterendpoint (UUID | Unset):
        filterevent_type (WebhookEventType | Unset): Every event name a subscriber may ask for.
        filterstatus (WebhookDeliveryStatus | Unset): Derived, not stored. `pending` is still on
            the retry ladder; `dead` ran out of rungs and is
            what an outage costs you.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | WebhookDeliveryCollectionDocument]
    """

    kwargs = _get_kwargs(
        pagecursor=pagecursor,
        pagesize=pagesize,
        include=include,
        filterendpoint=filterendpoint,
        filterevent_type=filterevent_type,
        filterstatus=filterstatus,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    pagecursor: str | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    include: ListWebhookDeliveriesInclude | Unset = UNSET,
    filterendpoint: UUID | Unset = UNSET,
    filterevent_type: WebhookEventType | Unset = UNSET,
    filterstatus: WebhookDeliveryStatus | Unset = UNSET,
) -> ErrorDocument | WebhookDeliveryCollectionDocument | None:
    r"""List webhook deliveries

     Read-only evidence about your endpoints — what we owed each one, and what became of it.

    **`filter[status]=dead` is the query this collection exists for.** Delivery is at-least-once
    with a dead-letter, so \"we tried and gave up\" is a state that is reached without your server
    ever hearing about it; this is where you learn what you missed after an outage. An unknown
    status value is refused with a 400 rather than ignored.

    The body we POSTed is never published here — only its `payloadSha256` digest, so an
    integrator who kept what they received can prove it is what we sent.

    **Scope:** a delivery borrows its endpoint's reach, so `fax:read` lists only the deliveries
    of **fax-account-scoped** endpoints; the deliveries of customer- and tenant-scoped endpoints
    require `webhooks:read`.

    Args:
        pagecursor (str | Unset):
        pagesize (int | Unset):
        include (ListWebhookDeliveriesInclude | Unset):
        filterendpoint (UUID | Unset):
        filterevent_type (WebhookEventType | Unset): Every event name a subscriber may ask for.
        filterstatus (WebhookDeliveryStatus | Unset): Derived, not stored. `pending` is still on
            the retry ladder; `dead` ran out of rungs and is
            what an outage costs you.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | WebhookDeliveryCollectionDocument
    """

    return sync_detailed(
        client=client,
        pagecursor=pagecursor,
        pagesize=pagesize,
        include=include,
        filterendpoint=filterendpoint,
        filterevent_type=filterevent_type,
        filterstatus=filterstatus,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    pagecursor: str | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    include: ListWebhookDeliveriesInclude | Unset = UNSET,
    filterendpoint: UUID | Unset = UNSET,
    filterevent_type: WebhookEventType | Unset = UNSET,
    filterstatus: WebhookDeliveryStatus | Unset = UNSET,
) -> Response[ErrorDocument | WebhookDeliveryCollectionDocument]:
    r"""List webhook deliveries

     Read-only evidence about your endpoints — what we owed each one, and what became of it.

    **`filter[status]=dead` is the query this collection exists for.** Delivery is at-least-once
    with a dead-letter, so \"we tried and gave up\" is a state that is reached without your server
    ever hearing about it; this is where you learn what you missed after an outage. An unknown
    status value is refused with a 400 rather than ignored.

    The body we POSTed is never published here — only its `payloadSha256` digest, so an
    integrator who kept what they received can prove it is what we sent.

    **Scope:** a delivery borrows its endpoint's reach, so `fax:read` lists only the deliveries
    of **fax-account-scoped** endpoints; the deliveries of customer- and tenant-scoped endpoints
    require `webhooks:read`.

    Args:
        pagecursor (str | Unset):
        pagesize (int | Unset):
        include (ListWebhookDeliveriesInclude | Unset):
        filterendpoint (UUID | Unset):
        filterevent_type (WebhookEventType | Unset): Every event name a subscriber may ask for.
        filterstatus (WebhookDeliveryStatus | Unset): Derived, not stored. `pending` is still on
            the retry ladder; `dead` ran out of rungs and is
            what an outage costs you.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | WebhookDeliveryCollectionDocument]
    """

    kwargs = _get_kwargs(
        pagecursor=pagecursor,
        pagesize=pagesize,
        include=include,
        filterendpoint=filterendpoint,
        filterevent_type=filterevent_type,
        filterstatus=filterstatus,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    pagecursor: str | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    include: ListWebhookDeliveriesInclude | Unset = UNSET,
    filterendpoint: UUID | Unset = UNSET,
    filterevent_type: WebhookEventType | Unset = UNSET,
    filterstatus: WebhookDeliveryStatus | Unset = UNSET,
) -> ErrorDocument | WebhookDeliveryCollectionDocument | None:
    r"""List webhook deliveries

     Read-only evidence about your endpoints — what we owed each one, and what became of it.

    **`filter[status]=dead` is the query this collection exists for.** Delivery is at-least-once
    with a dead-letter, so \"we tried and gave up\" is a state that is reached without your server
    ever hearing about it; this is where you learn what you missed after an outage. An unknown
    status value is refused with a 400 rather than ignored.

    The body we POSTed is never published here — only its `payloadSha256` digest, so an
    integrator who kept what they received can prove it is what we sent.

    **Scope:** a delivery borrows its endpoint's reach, so `fax:read` lists only the deliveries
    of **fax-account-scoped** endpoints; the deliveries of customer- and tenant-scoped endpoints
    require `webhooks:read`.

    Args:
        pagecursor (str | Unset):
        pagesize (int | Unset):
        include (ListWebhookDeliveriesInclude | Unset):
        filterendpoint (UUID | Unset):
        filterevent_type (WebhookEventType | Unset): Every event name a subscriber may ask for.
        filterstatus (WebhookDeliveryStatus | Unset): Derived, not stored. `pending` is still on
            the retry ladder; `dead` ran out of rungs and is
            what an outage costs you.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | WebhookDeliveryCollectionDocument
    """

    return (
        await asyncio_detailed(
            client=client,
            pagecursor=pagecursor,
            pagesize=pagesize,
            include=include,
            filterendpoint=filterendpoint,
            filterevent_type=filterevent_type,
            filterstatus=filterstatus,
        )
    ).parsed
