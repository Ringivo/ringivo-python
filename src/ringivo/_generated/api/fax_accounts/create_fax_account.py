from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.fax_account_create_request import FaxAccountCreateRequest
from ...models.fax_account_document_response import FaxAccountDocumentResponse
from ...types import Response


def _get_kwargs(
    *,
    body: FaxAccountCreateRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/fax-accounts",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/vnd.api+json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDocument | FaxAccountDocumentResponse | None:
    if response.status_code == 201:
        response_201 = FaxAccountDocumentResponse.from_dict(response.json())

        return response_201

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
) -> Response[ErrorDocument | FaxAccountDocumentResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: FaxAccountCreateRequest,
) -> Response[ErrorDocument | FaxAccountDocumentResponse]:
    """Create a fax account

     An account is created FOR one of your customers, named in the `customer` relationship. A
    customer id that is not yours answers **404** on that relationship pointer — the same answer
    an id that names nothing anywhere gets.

    Numbers are not attached here: point a DID at the account through the routing API.

    Args:
        body (FaxAccountCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | FaxAccountDocumentResponse]
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
    body: FaxAccountCreateRequest,
) -> ErrorDocument | FaxAccountDocumentResponse | None:
    """Create a fax account

     An account is created FOR one of your customers, named in the `customer` relationship. A
    customer id that is not yours answers **404** on that relationship pointer — the same answer
    an id that names nothing anywhere gets.

    Numbers are not attached here: point a DID at the account through the routing API.

    Args:
        body (FaxAccountCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | FaxAccountDocumentResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: FaxAccountCreateRequest,
) -> Response[ErrorDocument | FaxAccountDocumentResponse]:
    """Create a fax account

     An account is created FOR one of your customers, named in the `customer` relationship. A
    customer id that is not yours answers **404** on that relationship pointer — the same answer
    an id that names nothing anywhere gets.

    Numbers are not attached here: point a DID at the account through the routing API.

    Args:
        body (FaxAccountCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | FaxAccountDocumentResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: FaxAccountCreateRequest,
) -> ErrorDocument | FaxAccountDocumentResponse | None:
    """Create a fax account

     An account is created FOR one of your customers, named in the `customer` relationship. A
    customer id that is not yours answers **404** on that relationship pointer — the same answer
    an id that names nothing anywhere gets.

    Numbers are not attached here: point a DID at the account through the routing API.

    Args:
        body (FaxAccountCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | FaxAccountDocumentResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
