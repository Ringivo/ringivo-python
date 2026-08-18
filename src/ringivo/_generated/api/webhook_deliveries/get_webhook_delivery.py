from http import HTTPStatus
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.get_webhook_delivery_include import GetWebhookDeliveryInclude
from ...models.webhook_delivery_document_response import WebhookDeliveryDocumentResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    webhook_delivery: UUID,
    *,
    include: GetWebhookDeliveryInclude | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_include: str | Unset = UNSET
    if not isinstance(include, Unset):
        json_include = include.value

    params["include"] = json_include

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/webhook-deliveries/{webhook_delivery}".format(
            webhook_delivery=quote(str(webhook_delivery), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDocument | WebhookDeliveryDocumentResponse | None:
    if response.status_code == 200:
        response_200 = WebhookDeliveryDocumentResponse.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = ErrorDocument.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ErrorDocument.from_dict(response.json())

        return response_403

    if response.status_code == 404:
        response_404 = ErrorDocument.from_dict(response.json())

        return response_404

    if response.status_code == 429:
        response_429 = ErrorDocument.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDocument | WebhookDeliveryDocumentResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    webhook_delivery: UUID,
    *,
    client: AuthenticatedClient,
    include: GetWebhookDeliveryInclude | Unset = UNSET,
) -> Response[ErrorDocument | WebhookDeliveryDocumentResponse]:
    """Read one webhook delivery

     **Scope:** a delivery borrows its endpoint's reach, so `fax:read` reaches only the
    deliveries of **fax-account-scoped** endpoints; a delivery of a customer- or tenant-scoped
    endpoint answers **404** to a `fax:*` token and requires `webhooks:read`.

    Args:
        webhook_delivery (UUID):
        include (GetWebhookDeliveryInclude | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | WebhookDeliveryDocumentResponse]
    """

    kwargs = _get_kwargs(
        webhook_delivery=webhook_delivery,
        include=include,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    webhook_delivery: UUID,
    *,
    client: AuthenticatedClient,
    include: GetWebhookDeliveryInclude | Unset = UNSET,
) -> ErrorDocument | WebhookDeliveryDocumentResponse | None:
    """Read one webhook delivery

     **Scope:** a delivery borrows its endpoint's reach, so `fax:read` reaches only the
    deliveries of **fax-account-scoped** endpoints; a delivery of a customer- or tenant-scoped
    endpoint answers **404** to a `fax:*` token and requires `webhooks:read`.

    Args:
        webhook_delivery (UUID):
        include (GetWebhookDeliveryInclude | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | WebhookDeliveryDocumentResponse
    """

    return sync_detailed(
        webhook_delivery=webhook_delivery,
        client=client,
        include=include,
    ).parsed


async def asyncio_detailed(
    webhook_delivery: UUID,
    *,
    client: AuthenticatedClient,
    include: GetWebhookDeliveryInclude | Unset = UNSET,
) -> Response[ErrorDocument | WebhookDeliveryDocumentResponse]:
    """Read one webhook delivery

     **Scope:** a delivery borrows its endpoint's reach, so `fax:read` reaches only the
    deliveries of **fax-account-scoped** endpoints; a delivery of a customer- or tenant-scoped
    endpoint answers **404** to a `fax:*` token and requires `webhooks:read`.

    Args:
        webhook_delivery (UUID):
        include (GetWebhookDeliveryInclude | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | WebhookDeliveryDocumentResponse]
    """

    kwargs = _get_kwargs(
        webhook_delivery=webhook_delivery,
        include=include,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    webhook_delivery: UUID,
    *,
    client: AuthenticatedClient,
    include: GetWebhookDeliveryInclude | Unset = UNSET,
) -> ErrorDocument | WebhookDeliveryDocumentResponse | None:
    """Read one webhook delivery

     **Scope:** a delivery borrows its endpoint's reach, so `fax:read` reaches only the
    deliveries of **fax-account-scoped** endpoints; a delivery of a customer- or tenant-scoped
    endpoint answers **404** to a `fax:*` token and requires `webhooks:read`.

    Args:
        webhook_delivery (UUID):
        include (GetWebhookDeliveryInclude | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | WebhookDeliveryDocumentResponse
    """

    return (
        await asyncio_detailed(
            webhook_delivery=webhook_delivery,
            client=client,
            include=include,
        )
    ).parsed
