from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.fax_account_user_create_request import FaxAccountUserCreateRequest
from ...models.fax_account_user_document_response import FaxAccountUserDocumentResponse
from ...types import Response


def _get_kwargs(
    *,
    body: FaxAccountUserCreateRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/fax-account-users",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/vnd.api+json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDocument | FaxAccountUserDocumentResponse | None:
    if response.status_code == 201:
        response_201 = FaxAccountUserDocumentResponse.from_dict(response.json())

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
) -> Response[ErrorDocument | FaxAccountUserDocumentResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: FaxAccountUserCreateRequest,
) -> Response[ErrorDocument | FaxAccountUserDocumentResponse]:
    """Grant a user access to a fax account

     A grant is a pair of foreign keys and a fact: it exists or it does not. There is no update
    route — withdraw one by deleting it.

    The account may be one the caller does not themselves hold: administering an account is
    permission-gated, while reading its content is grant-gated, so somebody has to be able to
    add the first member.

    Args:
        body (FaxAccountUserCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | FaxAccountUserDocumentResponse]
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
    body: FaxAccountUserCreateRequest,
) -> ErrorDocument | FaxAccountUserDocumentResponse | None:
    """Grant a user access to a fax account

     A grant is a pair of foreign keys and a fact: it exists or it does not. There is no update
    route — withdraw one by deleting it.

    The account may be one the caller does not themselves hold: administering an account is
    permission-gated, while reading its content is grant-gated, so somebody has to be able to
    add the first member.

    Args:
        body (FaxAccountUserCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | FaxAccountUserDocumentResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: FaxAccountUserCreateRequest,
) -> Response[ErrorDocument | FaxAccountUserDocumentResponse]:
    """Grant a user access to a fax account

     A grant is a pair of foreign keys and a fact: it exists or it does not. There is no update
    route — withdraw one by deleting it.

    The account may be one the caller does not themselves hold: administering an account is
    permission-gated, while reading its content is grant-gated, so somebody has to be able to
    add the first member.

    Args:
        body (FaxAccountUserCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | FaxAccountUserDocumentResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: FaxAccountUserCreateRequest,
) -> ErrorDocument | FaxAccountUserDocumentResponse | None:
    """Grant a user access to a fax account

     A grant is a pair of foreign keys and a fact: it exists or it does not. There is no update
    route — withdraw one by deleting it.

    The account may be one the caller does not themselves hold: administering an account is
    permission-gated, while reading its content is grant-gated, so somebody has to be able to
    add the first member.

    Args:
        body (FaxAccountUserCreateRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | FaxAccountUserDocumentResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
