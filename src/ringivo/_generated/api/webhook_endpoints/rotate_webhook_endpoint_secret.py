from http import HTTPStatus
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.webhook_endpoint_document_response import WebhookEndpointDocumentResponse
from ...types import Response


def _get_kwargs(
    webhook_endpoint: UUID,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/webhook-endpoints/{webhook_endpoint}/rotate-secret".format(
            webhook_endpoint=quote(str(webhook_endpoint), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDocument | WebhookEndpointDocumentResponse | None:
    if response.status_code == 200:
        response_200 = WebhookEndpointDocumentResponse.from_dict(response.json())

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
) -> Response[ErrorDocument | WebhookEndpointDocumentResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    webhook_endpoint: UUID,
    *,
    client: AuthenticatedClient,
) -> Response[ErrorDocument | WebhookEndpointDocumentResponse]:
    """Mint a new signing secret

     A verb and not a PATCH, because it MINTS A CREDENTIAL and starts a clock.

    The new secret is in this response and nowhere else. The **previous secret goes on signing
    for a 24-hour grace window**, and `secretPreviousExpiresAt` is the deadline — during that
    window a delivery's signature header carries two `v1` values, newest first. Roll your own
    copy before the deadline.

    **Scope:** `fax:write` may rotate only a **fax-account-scoped** endpoint's secret; a
    customer- or tenant-scoped endpoint answers **404** to a `fax:*` token and requires
    `webhooks:write`.

    Args:
        webhook_endpoint (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | WebhookEndpointDocumentResponse]
    """

    kwargs = _get_kwargs(
        webhook_endpoint=webhook_endpoint,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    webhook_endpoint: UUID,
    *,
    client: AuthenticatedClient,
) -> ErrorDocument | WebhookEndpointDocumentResponse | None:
    """Mint a new signing secret

     A verb and not a PATCH, because it MINTS A CREDENTIAL and starts a clock.

    The new secret is in this response and nowhere else. The **previous secret goes on signing
    for a 24-hour grace window**, and `secretPreviousExpiresAt` is the deadline — during that
    window a delivery's signature header carries two `v1` values, newest first. Roll your own
    copy before the deadline.

    **Scope:** `fax:write` may rotate only a **fax-account-scoped** endpoint's secret; a
    customer- or tenant-scoped endpoint answers **404** to a `fax:*` token and requires
    `webhooks:write`.

    Args:
        webhook_endpoint (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | WebhookEndpointDocumentResponse
    """

    return sync_detailed(
        webhook_endpoint=webhook_endpoint,
        client=client,
    ).parsed


async def asyncio_detailed(
    webhook_endpoint: UUID,
    *,
    client: AuthenticatedClient,
) -> Response[ErrorDocument | WebhookEndpointDocumentResponse]:
    """Mint a new signing secret

     A verb and not a PATCH, because it MINTS A CREDENTIAL and starts a clock.

    The new secret is in this response and nowhere else. The **previous secret goes on signing
    for a 24-hour grace window**, and `secretPreviousExpiresAt` is the deadline — during that
    window a delivery's signature header carries two `v1` values, newest first. Roll your own
    copy before the deadline.

    **Scope:** `fax:write` may rotate only a **fax-account-scoped** endpoint's secret; a
    customer- or tenant-scoped endpoint answers **404** to a `fax:*` token and requires
    `webhooks:write`.

    Args:
        webhook_endpoint (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | WebhookEndpointDocumentResponse]
    """

    kwargs = _get_kwargs(
        webhook_endpoint=webhook_endpoint,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    webhook_endpoint: UUID,
    *,
    client: AuthenticatedClient,
) -> ErrorDocument | WebhookEndpointDocumentResponse | None:
    """Mint a new signing secret

     A verb and not a PATCH, because it MINTS A CREDENTIAL and starts a clock.

    The new secret is in this response and nowhere else. The **previous secret goes on signing
    for a 24-hour grace window**, and `secretPreviousExpiresAt` is the deadline — during that
    window a delivery's signature header carries two `v1` values, newest first. Roll your own
    copy before the deadline.

    **Scope:** `fax:write` may rotate only a **fax-account-scoped** endpoint's secret; a
    customer- or tenant-scoped endpoint answers **404** to a `fax:*` token and requires
    `webhooks:write`.

    Args:
        webhook_endpoint (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | WebhookEndpointDocumentResponse
    """

    return (
        await asyncio_detailed(
            webhook_endpoint=webhook_endpoint,
            client=client,
        )
    ).parsed
