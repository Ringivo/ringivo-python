from http import HTTPStatus
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.get_fax_media_format import GetFaxMediaFormat
from ...models.media_link import MediaLink
from ...types import UNSET, Response, Unset


def _get_kwargs(
    fax: UUID,
    *,
    format_: GetFaxMediaFormat | Unset = GetFaxMediaFormat.PDF,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    json_format_: str | Unset = UNSET
    if not isinstance(format_, Unset):
        json_format_ = format_.value

    params["format"] = json_format_

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/faxes/{fax}/media".format(
            fax=quote(str(fax), safe=""),
        ),
        "params": params,
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
    format_: GetFaxMediaFormat | Unset = GetFaxMediaFormat.PDF,
) -> Response[ErrorDocument | MediaLink]:
    """Mint a download URL for a fax's document

     Answers a small **plain-JSON composite**, not the bytes and not a JSON:API document: `url`
    is a short-lived pre-signed link you follow yourself, and `expires_at` says until when.

    Every call mints a fresh capability and writes an audit entry naming who asked, so do not
    cache the URL past its expiry or share it — anyone holding it reads that document with no
    further authorization.

    Args:
        fax (UUID):
        format_ (GetFaxMediaFormat | Unset):  Default: GetFaxMediaFormat.PDF.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | MediaLink]
    """

    kwargs = _get_kwargs(
        fax=fax,
        format_=format_,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    fax: UUID,
    *,
    client: AuthenticatedClient,
    format_: GetFaxMediaFormat | Unset = GetFaxMediaFormat.PDF,
) -> ErrorDocument | MediaLink | None:
    """Mint a download URL for a fax's document

     Answers a small **plain-JSON composite**, not the bytes and not a JSON:API document: `url`
    is a short-lived pre-signed link you follow yourself, and `expires_at` says until when.

    Every call mints a fresh capability and writes an audit entry naming who asked, so do not
    cache the URL past its expiry or share it — anyone holding it reads that document with no
    further authorization.

    Args:
        fax (UUID):
        format_ (GetFaxMediaFormat | Unset):  Default: GetFaxMediaFormat.PDF.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | MediaLink
    """

    return sync_detailed(
        fax=fax,
        client=client,
        format_=format_,
    ).parsed


async def asyncio_detailed(
    fax: UUID,
    *,
    client: AuthenticatedClient,
    format_: GetFaxMediaFormat | Unset = GetFaxMediaFormat.PDF,
) -> Response[ErrorDocument | MediaLink]:
    """Mint a download URL for a fax's document

     Answers a small **plain-JSON composite**, not the bytes and not a JSON:API document: `url`
    is a short-lived pre-signed link you follow yourself, and `expires_at` says until when.

    Every call mints a fresh capability and writes an audit entry naming who asked, so do not
    cache the URL past its expiry or share it — anyone holding it reads that document with no
    further authorization.

    Args:
        fax (UUID):
        format_ (GetFaxMediaFormat | Unset):  Default: GetFaxMediaFormat.PDF.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | MediaLink]
    """

    kwargs = _get_kwargs(
        fax=fax,
        format_=format_,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    fax: UUID,
    *,
    client: AuthenticatedClient,
    format_: GetFaxMediaFormat | Unset = GetFaxMediaFormat.PDF,
) -> ErrorDocument | MediaLink | None:
    """Mint a download URL for a fax's document

     Answers a small **plain-JSON composite**, not the bytes and not a JSON:API document: `url`
    is a short-lived pre-signed link you follow yourself, and `expires_at` says until when.

    Every call mints a fresh capability and writes an audit entry naming who asked, so do not
    cache the URL past its expiry or share it — anyone holding it reads that document with no
    further authorization.

    Args:
        fax (UUID):
        format_ (GetFaxMediaFormat | Unset):  Default: GetFaxMediaFormat.PDF.

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
            format_=format_,
        )
    ).parsed
