from http import HTTPStatus
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.fax_account_document_response import FaxAccountDocumentResponse
from ...models.fax_account_update_request import FaxAccountUpdateRequest
from ...types import Response


def _get_kwargs(
    fax_account: UUID,
    *,
    body: FaxAccountUpdateRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/v1/fax-accounts/{fax_account}".format(
            fax_account=quote(str(fax_account), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/vnd.api+json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDocument | FaxAccountDocumentResponse | None:
    if response.status_code == 200:
        response_200 = FaxAccountDocumentResponse.from_dict(response.json())

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
) -> Response[ErrorDocument | FaxAccountDocumentResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    fax_account: UUID,
    *,
    client: AuthenticatedClient,
    body: FaxAccountUpdateRequest,
) -> Response[ErrorDocument | FaxAccountDocumentResponse]:
    """Change a fax account's settings, or suspend it

     `status` is the operational lever: suspending an account stops it SENDING while it goes on
    receiving, without deleting the compliance record behind it.

    An account cannot be moved to another customer — every fax it holds carries the customer it
    was sent or received for — and naming a different one is a 422 rather than a silent drop. A
    sparse PATCH of one attribute leaves every other field alone.

    Args:
        fax_account (UUID):
        body (FaxAccountUpdateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | FaxAccountDocumentResponse]
    """

    kwargs = _get_kwargs(
        fax_account=fax_account,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    fax_account: UUID,
    *,
    client: AuthenticatedClient,
    body: FaxAccountUpdateRequest,
) -> ErrorDocument | FaxAccountDocumentResponse | None:
    """Change a fax account's settings, or suspend it

     `status` is the operational lever: suspending an account stops it SENDING while it goes on
    receiving, without deleting the compliance record behind it.

    An account cannot be moved to another customer — every fax it holds carries the customer it
    was sent or received for — and naming a different one is a 422 rather than a silent drop. A
    sparse PATCH of one attribute leaves every other field alone.

    Args:
        fax_account (UUID):
        body (FaxAccountUpdateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | FaxAccountDocumentResponse
    """

    return sync_detailed(
        fax_account=fax_account,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    fax_account: UUID,
    *,
    client: AuthenticatedClient,
    body: FaxAccountUpdateRequest,
) -> Response[ErrorDocument | FaxAccountDocumentResponse]:
    """Change a fax account's settings, or suspend it

     `status` is the operational lever: suspending an account stops it SENDING while it goes on
    receiving, without deleting the compliance record behind it.

    An account cannot be moved to another customer — every fax it holds carries the customer it
    was sent or received for — and naming a different one is a 422 rather than a silent drop. A
    sparse PATCH of one attribute leaves every other field alone.

    Args:
        fax_account (UUID):
        body (FaxAccountUpdateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | FaxAccountDocumentResponse]
    """

    kwargs = _get_kwargs(
        fax_account=fax_account,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    fax_account: UUID,
    *,
    client: AuthenticatedClient,
    body: FaxAccountUpdateRequest,
) -> ErrorDocument | FaxAccountDocumentResponse | None:
    """Change a fax account's settings, or suspend it

     `status` is the operational lever: suspending an account stops it SENDING while it goes on
    receiving, without deleting the compliance record behind it.

    An account cannot be moved to another customer — every fax it holds carries the customer it
    was sent or received for — and naming a different one is a 422 rather than a silent drop. A
    sparse PATCH of one attribute leaves every other field alone.

    Args:
        fax_account (UUID):
        body (FaxAccountUpdateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | FaxAccountDocumentResponse
    """

    return (
        await asyncio_detailed(
            fax_account=fax_account,
            client=client,
            body=body,
        )
    ).parsed
