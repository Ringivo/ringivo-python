from http import HTTPStatus
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.fax_document_response import FaxDocumentResponse
from ...models.get_fax_include import GetFaxInclude
from ...types import UNSET, Response, Unset


def _get_kwargs(
    fax: UUID,
    *,
    include: GetFaxInclude | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_include: str | Unset = UNSET
    if not isinstance(include, Unset):
        json_include = include.value

    params["include"] = json_include

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/faxes/{fax}".format(
            fax=quote(str(fax), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDocument | FaxDocumentResponse | None:
    if response.status_code == 200:
        response_200 = FaxDocumentResponse.from_dict(response.json())

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
) -> Response[ErrorDocument | FaxDocumentResponse]:
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
    include: GetFaxInclude | Unset = UNSET,
) -> Response[ErrorDocument | FaxDocumentResponse]:
    """Read one fax

     The fax and its document metadata. **No object key and no URL is ever published here** — the
    bytes are reached only through `GET /v1/faxes/{fax}/media`, which mints a short-lived
    download URL and records who asked.

    Args:
        fax (UUID):
        include (GetFaxInclude | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | FaxDocumentResponse]
    """

    kwargs = _get_kwargs(
        fax=fax,
        include=include,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    fax: UUID,
    *,
    client: AuthenticatedClient,
    include: GetFaxInclude | Unset = UNSET,
) -> ErrorDocument | FaxDocumentResponse | None:
    """Read one fax

     The fax and its document metadata. **No object key and no URL is ever published here** — the
    bytes are reached only through `GET /v1/faxes/{fax}/media`, which mints a short-lived
    download URL and records who asked.

    Args:
        fax (UUID):
        include (GetFaxInclude | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | FaxDocumentResponse
    """

    return sync_detailed(
        fax=fax,
        client=client,
        include=include,
    ).parsed


async def asyncio_detailed(
    fax: UUID,
    *,
    client: AuthenticatedClient,
    include: GetFaxInclude | Unset = UNSET,
) -> Response[ErrorDocument | FaxDocumentResponse]:
    """Read one fax

     The fax and its document metadata. **No object key and no URL is ever published here** — the
    bytes are reached only through `GET /v1/faxes/{fax}/media`, which mints a short-lived
    download URL and records who asked.

    Args:
        fax (UUID):
        include (GetFaxInclude | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | FaxDocumentResponse]
    """

    kwargs = _get_kwargs(
        fax=fax,
        include=include,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    fax: UUID,
    *,
    client: AuthenticatedClient,
    include: GetFaxInclude | Unset = UNSET,
) -> ErrorDocument | FaxDocumentResponse | None:
    """Read one fax

     The fax and its document metadata. **No object key and no URL is ever published here** — the
    bytes are reached only through `GET /v1/faxes/{fax}/media`, which mints a short-lived
    download URL and records who asked.

    Args:
        fax (UUID):
        include (GetFaxInclude | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | FaxDocumentResponse
    """

    return (
        await asyncio_detailed(
            fax=fax,
            client=client,
            include=include,
        )
    ).parsed
