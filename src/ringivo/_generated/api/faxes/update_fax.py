from http import HTTPStatus
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.fax_document_response import FaxDocumentResponse
from ...models.fax_update_request import FaxUpdateRequest
from ...types import Response


def _get_kwargs(
    fax: UUID,
    *,
    body: FaxUpdateRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "patch",
        "url": "/v1/faxes/{fax}".format(
            fax=quote(str(fax), safe=""),
        ),
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/vnd.api+json"

    _kwargs["headers"] = headers
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
    body: FaxUpdateRequest,
) -> Response[ErrorDocument | FaxDocumentResponse]:
    r"""Move a fax's read, archived or tags flags

     Three fields belong to the reader — `read`, `archived` and `tags` — and everything else
    describes a transmission that already happened. Naming a machinery-owned field with a
    CHANGED value is refused with a 422 rather than silently dropped; echoing the whole document
    back unchanged is fine, which is what makes GET-then-PATCH work.

    `tags` is replaced wholesale, never merged: sending `{\"clinic\":\"north\"}` means the tags ARE
    that. `read` is idempotent — marking an already-read fax read again does not move when it
    was first read.

    Args:
        fax (UUID):
        body (FaxUpdateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | FaxDocumentResponse]
    """

    kwargs = _get_kwargs(
        fax=fax,
        body=body,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    fax: UUID,
    *,
    client: AuthenticatedClient,
    body: FaxUpdateRequest,
) -> ErrorDocument | FaxDocumentResponse | None:
    r"""Move a fax's read, archived or tags flags

     Three fields belong to the reader — `read`, `archived` and `tags` — and everything else
    describes a transmission that already happened. Naming a machinery-owned field with a
    CHANGED value is refused with a 422 rather than silently dropped; echoing the whole document
    back unchanged is fine, which is what makes GET-then-PATCH work.

    `tags` is replaced wholesale, never merged: sending `{\"clinic\":\"north\"}` means the tags ARE
    that. `read` is idempotent — marking an already-read fax read again does not move when it
    was first read.

    Args:
        fax (UUID):
        body (FaxUpdateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | FaxDocumentResponse
    """

    return sync_detailed(
        fax=fax,
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    fax: UUID,
    *,
    client: AuthenticatedClient,
    body: FaxUpdateRequest,
) -> Response[ErrorDocument | FaxDocumentResponse]:
    r"""Move a fax's read, archived or tags flags

     Three fields belong to the reader — `read`, `archived` and `tags` — and everything else
    describes a transmission that already happened. Naming a machinery-owned field with a
    CHANGED value is refused with a 422 rather than silently dropped; echoing the whole document
    back unchanged is fine, which is what makes GET-then-PATCH work.

    `tags` is replaced wholesale, never merged: sending `{\"clinic\":\"north\"}` means the tags ARE
    that. `read` is idempotent — marking an already-read fax read again does not move when it
    was first read.

    Args:
        fax (UUID):
        body (FaxUpdateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | FaxDocumentResponse]
    """

    kwargs = _get_kwargs(
        fax=fax,
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    fax: UUID,
    *,
    client: AuthenticatedClient,
    body: FaxUpdateRequest,
) -> ErrorDocument | FaxDocumentResponse | None:
    r"""Move a fax's read, archived or tags flags

     Three fields belong to the reader — `read`, `archived` and `tags` — and everything else
    describes a transmission that already happened. Naming a machinery-owned field with a
    CHANGED value is refused with a 422 rather than silently dropped; echoing the whole document
    back unchanged is fine, which is what makes GET-then-PATCH work.

    `tags` is replaced wholesale, never merged: sending `{\"clinic\":\"north\"}` means the tags ARE
    that. `read` is idempotent — marking an already-read fax read again does not move when it
    was first read.

    Args:
        fax (UUID):
        body (FaxUpdateRequest):

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
            body=body,
        )
    ).parsed
