from http import HTTPStatus
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.webhook_endpoint_document_response import WebhookEndpointDocumentResponse
from ...models.webhook_endpoint_update_request import WebhookEndpointUpdateRequest
from ...types import Response


def _get_kwargs(
    webhook_endpoint: UUID,
    *,
    body: WebhookEndpointUpdateRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/v1/webhook-endpoints/{webhook_endpoint}".format(
            webhook_endpoint=quote(str(webhook_endpoint), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/vnd.api+json"

    _kwargs["headers"] = headers
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

    if response.status_code == 422:
        response_422 = ErrorDocument.from_dict(response.json())

        return response_422

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
    body: WebhookEndpointUpdateRequest,
) -> Response[ErrorDocument | WebhookEndpointDocumentResponse]:
    """Change a webhook endpoint's URL, events or switch

     `url`, `events` and `active` are editable. `scopeType` and `scopeId` are not — a caller who
    wants a different scope removes this endpoint and registers another.

    **Scope:** `fax:write` reaches only **fax-account-scoped** endpoints; a customer- or
    tenant-scoped endpoint answers **404** to a `fax:*` token and requires `webhooks:write`.

    Args:
        webhook_endpoint (UUID):
        body (WebhookEndpointUpdateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | WebhookEndpointDocumentResponse]
    """

    kwargs = _get_kwargs(
        webhook_endpoint=webhook_endpoint,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    webhook_endpoint: UUID,
    *,
    client: AuthenticatedClient,
    body: WebhookEndpointUpdateRequest,
) -> ErrorDocument | WebhookEndpointDocumentResponse | None:
    """Change a webhook endpoint's URL, events or switch

     `url`, `events` and `active` are editable. `scopeType` and `scopeId` are not — a caller who
    wants a different scope removes this endpoint and registers another.

    **Scope:** `fax:write` reaches only **fax-account-scoped** endpoints; a customer- or
    tenant-scoped endpoint answers **404** to a `fax:*` token and requires `webhooks:write`.

    Args:
        webhook_endpoint (UUID):
        body (WebhookEndpointUpdateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | WebhookEndpointDocumentResponse
    """

    return sync_detailed(
        webhook_endpoint=webhook_endpoint,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    webhook_endpoint: UUID,
    *,
    client: AuthenticatedClient,
    body: WebhookEndpointUpdateRequest,
) -> Response[ErrorDocument | WebhookEndpointDocumentResponse]:
    """Change a webhook endpoint's URL, events or switch

     `url`, `events` and `active` are editable. `scopeType` and `scopeId` are not — a caller who
    wants a different scope removes this endpoint and registers another.

    **Scope:** `fax:write` reaches only **fax-account-scoped** endpoints; a customer- or
    tenant-scoped endpoint answers **404** to a `fax:*` token and requires `webhooks:write`.

    Args:
        webhook_endpoint (UUID):
        body (WebhookEndpointUpdateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | WebhookEndpointDocumentResponse]
    """

    kwargs = _get_kwargs(
        webhook_endpoint=webhook_endpoint,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    webhook_endpoint: UUID,
    *,
    client: AuthenticatedClient,
    body: WebhookEndpointUpdateRequest,
) -> ErrorDocument | WebhookEndpointDocumentResponse | None:
    """Change a webhook endpoint's URL, events or switch

     `url`, `events` and `active` are editable. `scopeType` and `scopeId` are not — a caller who
    wants a different scope removes this endpoint and registers another.

    **Scope:** `fax:write` reaches only **fax-account-scoped** endpoints; a customer- or
    tenant-scoped endpoint answers **404** to a `fax:*` token and requires `webhooks:write`.

    Args:
        webhook_endpoint (UUID):
        body (WebhookEndpointUpdateRequest):

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
            body=body,
        )
    ).parsed
