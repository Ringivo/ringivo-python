from http import HTTPStatus
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.fax_account_user_document_response import FaxAccountUserDocumentResponse
from ...types import Response


def _get_kwargs(
    fax_account_user: UUID,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/fax-account-users/{fax_account_user}".format(
            fax_account_user=quote(str(fax_account_user), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDocument | FaxAccountUserDocumentResponse | None:
    if response.status_code == 200:
        response_200 = FaxAccountUserDocumentResponse.from_dict(response.json())

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
) -> Response[ErrorDocument | FaxAccountUserDocumentResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    fax_account_user: UUID,
    *,
    client: AuthenticatedClient,
) -> Response[ErrorDocument | FaxAccountUserDocumentResponse]:
    """Read one grant

    Args:
        fax_account_user (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | FaxAccountUserDocumentResponse]
    """

    kwargs = _get_kwargs(
        fax_account_user=fax_account_user,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    fax_account_user: UUID,
    *,
    client: AuthenticatedClient,
) -> ErrorDocument | FaxAccountUserDocumentResponse | None:
    """Read one grant

    Args:
        fax_account_user (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | FaxAccountUserDocumentResponse
    """

    return sync_detailed(
        fax_account_user=fax_account_user,
        client=client,
    ).parsed


async def asyncio_detailed(
    fax_account_user: UUID,
    *,
    client: AuthenticatedClient,
) -> Response[ErrorDocument | FaxAccountUserDocumentResponse]:
    """Read one grant

    Args:
        fax_account_user (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | FaxAccountUserDocumentResponse]
    """

    kwargs = _get_kwargs(
        fax_account_user=fax_account_user,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    fax_account_user: UUID,
    *,
    client: AuthenticatedClient,
) -> ErrorDocument | FaxAccountUserDocumentResponse | None:
    """Read one grant

    Args:
        fax_account_user (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | FaxAccountUserDocumentResponse
    """

    return (
        await asyncio_detailed(
            fax_account_user=fax_account_user,
            client=client,
        )
    ).parsed
