from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.webhook_endpoint_create_request import WebhookEndpointCreateRequest
from ...models.webhook_endpoint_document_response import WebhookEndpointDocumentResponse
from ...types import Response


def _get_kwargs(
    *,
    body: WebhookEndpointCreateRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/webhook-endpoints",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/vnd.api+json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDocument | WebhookEndpointDocumentResponse | None:
    if response.status_code == 201:
        response_201 = WebhookEndpointDocumentResponse.from_dict(response.json())

        return response_201

    if response.status_code == 401:
        response_401 = ErrorDocument.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ErrorDocument.from_dict(response.json())

        return response_403

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
    *,
    client: AuthenticatedClient,
    body: WebhookEndpointCreateRequest,
) -> Response[ErrorDocument | WebhookEndpointDocumentResponse]:
    r"""Register a webhook endpoint

     **The signing secret is in this response and nowhere else, ever.** Store it before you do
    anything else; there is no way to read it back.

    The URL must be `https` with a public host — plain http, credentials in the URL, a private
    address literal and a non-http scheme are each refused at registration. A hostname that
    does not resolve yet is accepted on purpose, so you can register before publishing DNS.

    `events` is the list you want. **`null` or `[]` both mean \"every event in scope\"**, and the
    list is published back verbatim rather than normalised, so a client that sent `[]` can tell
    its write was understood. An event name this platform does not publish is a 422 — a typo
    would otherwise subscribe you to silence.

    `scopeType`/`scopeId` say what the endpoint hears about, and neither can be changed
    afterwards: the delivery history is the record of what THAT scope was told.

    **Scope:** `fax:write` may register only a `fax_account`-scoped endpoint; naming a
    `customer` or `tenant` scope with a `fax:*` token is refused with a 422, and needs
    `webhooks:write`.

    Args:
        body (WebhookEndpointCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | WebhookEndpointDocumentResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: WebhookEndpointCreateRequest,
) -> ErrorDocument | WebhookEndpointDocumentResponse | None:
    r"""Register a webhook endpoint

     **The signing secret is in this response and nowhere else, ever.** Store it before you do
    anything else; there is no way to read it back.

    The URL must be `https` with a public host — plain http, credentials in the URL, a private
    address literal and a non-http scheme are each refused at registration. A hostname that
    does not resolve yet is accepted on purpose, so you can register before publishing DNS.

    `events` is the list you want. **`null` or `[]` both mean \"every event in scope\"**, and the
    list is published back verbatim rather than normalised, so a client that sent `[]` can tell
    its write was understood. An event name this platform does not publish is a 422 — a typo
    would otherwise subscribe you to silence.

    `scopeType`/`scopeId` say what the endpoint hears about, and neither can be changed
    afterwards: the delivery history is the record of what THAT scope was told.

    **Scope:** `fax:write` may register only a `fax_account`-scoped endpoint; naming a
    `customer` or `tenant` scope with a `fax:*` token is refused with a 422, and needs
    `webhooks:write`.

    Args:
        body (WebhookEndpointCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | WebhookEndpointDocumentResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: WebhookEndpointCreateRequest,
) -> Response[ErrorDocument | WebhookEndpointDocumentResponse]:
    r"""Register a webhook endpoint

     **The signing secret is in this response and nowhere else, ever.** Store it before you do
    anything else; there is no way to read it back.

    The URL must be `https` with a public host — plain http, credentials in the URL, a private
    address literal and a non-http scheme are each refused at registration. A hostname that
    does not resolve yet is accepted on purpose, so you can register before publishing DNS.

    `events` is the list you want. **`null` or `[]` both mean \"every event in scope\"**, and the
    list is published back verbatim rather than normalised, so a client that sent `[]` can tell
    its write was understood. An event name this platform does not publish is a 422 — a typo
    would otherwise subscribe you to silence.

    `scopeType`/`scopeId` say what the endpoint hears about, and neither can be changed
    afterwards: the delivery history is the record of what THAT scope was told.

    **Scope:** `fax:write` may register only a `fax_account`-scoped endpoint; naming a
    `customer` or `tenant` scope with a `fax:*` token is refused with a 422, and needs
    `webhooks:write`.

    Args:
        body (WebhookEndpointCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | WebhookEndpointDocumentResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: WebhookEndpointCreateRequest,
) -> ErrorDocument | WebhookEndpointDocumentResponse | None:
    r"""Register a webhook endpoint

     **The signing secret is in this response and nowhere else, ever.** Store it before you do
    anything else; there is no way to read it back.

    The URL must be `https` with a public host — plain http, credentials in the URL, a private
    address literal and a non-http scheme are each refused at registration. A hostname that
    does not resolve yet is accepted on purpose, so you can register before publishing DNS.

    `events` is the list you want. **`null` or `[]` both mean \"every event in scope\"**, and the
    list is published back verbatim rather than normalised, so a client that sent `[]` can tell
    its write was understood. An event name this platform does not publish is a 422 — a typo
    would otherwise subscribe you to silence.

    `scopeType`/`scopeId` say what the endpoint hears about, and neither can be changed
    afterwards: the delivery history is the record of what THAT scope was told.

    **Scope:** `fax:write` may register only a `fax_account`-scoped endpoint; naming a
    `customer` or `tenant` scope with a `fax:*` token is refused with a 422, and needs
    `webhooks:write`.

    Args:
        body (WebhookEndpointCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | WebhookEndpointDocumentResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
