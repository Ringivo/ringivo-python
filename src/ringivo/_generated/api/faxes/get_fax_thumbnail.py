from http import HTTPStatus
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.media_link import MediaLink
from ...types import Response


def _get_kwargs(
    fax: UUID,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/faxes/{fax}/thumbnail".format(
            fax=quote(str(fax), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDocument | MediaLink | None:
    if response.status_code == 200:
        response_200 = MediaLink.from_dict(response.json())

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
) -> Response[ErrorDocument | MediaLink]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    fax: UUID,
    *,
    client: AuthenticatedClient,
) -> Response[ErrorDocument | MediaLink]:
    """Mint a download URL for a fax's first-page preview

     The same composite as `GET /v1/faxes/{fax}/media`, one document kind over: the first-page
    PNG generated at conversion. Its own path rather than a third `format` value, because a
    list screen asks for a preview from a different place in your code than the one that
    downloads a fax.

    Follow `url` the same way — a plain `GET`, no `Authorization` header.

    Args:
        fax (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | MediaLink]
    """

    kwargs = _get_kwargs(
        fax=fax,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    fax: UUID,
    *,
    client: AuthenticatedClient,
) -> ErrorDocument | MediaLink | None:
    """Mint a download URL for a fax's first-page preview

     The same composite as `GET /v1/faxes/{fax}/media`, one document kind over: the first-page
    PNG generated at conversion. Its own path rather than a third `format` value, because a
    list screen asks for a preview from a different place in your code than the one that
    downloads a fax.

    Follow `url` the same way — a plain `GET`, no `Authorization` header.

    Args:
        fax (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | MediaLink
    """

    return sync_detailed(
        fax=fax,
        client=client,
    ).parsed


async def asyncio_detailed(
    fax: UUID,
    *,
    client: AuthenticatedClient,
) -> Response[ErrorDocument | MediaLink]:
    """Mint a download URL for a fax's first-page preview

     The same composite as `GET /v1/faxes/{fax}/media`, one document kind over: the first-page
    PNG generated at conversion. Its own path rather than a third `format` value, because a
    list screen asks for a preview from a different place in your code than the one that
    downloads a fax.

    Follow `url` the same way — a plain `GET`, no `Authorization` header.

    Args:
        fax (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | MediaLink]
    """

    kwargs = _get_kwargs(
        fax=fax,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    fax: UUID,
    *,
    client: AuthenticatedClient,
) -> ErrorDocument | MediaLink | None:
    """Mint a download URL for a fax's first-page preview

     The same composite as `GET /v1/faxes/{fax}/media`, one document kind over: the first-page
    PNG generated at conversion. Its own path rather than a third `format` value, because a
    list screen asks for a preview from a different place in your code than the one that
    downloads a fax.

    Follow `url` the same way — a plain `GET`, no `Authorization` header.

    Args:
        fax (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | MediaLink
    """

    return (
        await asyncio_detailed(
            fax=fax,
            client=client,
        )
    ).parsed
