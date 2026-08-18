from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.o_auth_error import OAuthError
from ...models.token_request import TokenRequest
from ...models.token_response import TokenResponse
from ...types import Response


def _get_kwargs(
    *,
    body: TokenRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/oauth/token",
    }

    _kwargs["data"] = body.to_dict()
    headers["Content-Type"] = "application/x-www-form-urlencoded"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> OAuthError | TokenResponse | None:
    if response.status_code == 200:
        response_200 = TokenResponse.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = OAuthError.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = OAuthError.from_dict(response.json())

        return response_401

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[OAuthError | TokenResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: TokenRequest,
) -> Response[OAuthError | TokenResponse]:
    """Exchange client credentials for a bearer token

     The OAuth 2.0 client-credentials grant (RFC 6749 §4.4). Send the client id and secret you
    were issued, plus the space-separated scopes you want.

    **A scope outside your client's ceiling is dropped, not refused.** Ask for
    `fax:read fax:write` with only `fax:read` granted and you receive a 200 carrying a token
    that holds `fax:read` alone. Read the scopes back from the token rather than assuming the
    request was honoured in full. A scope this platform does not publish at all is a different
    case: that is a `400 invalid_scope`.

    Args:
        body (TokenRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[OAuthError | TokenResponse]
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
    client: AuthenticatedClient | Client,
    body: TokenRequest,
) -> OAuthError | TokenResponse | None:
    """Exchange client credentials for a bearer token

     The OAuth 2.0 client-credentials grant (RFC 6749 §4.4). Send the client id and secret you
    were issued, plus the space-separated scopes you want.

    **A scope outside your client's ceiling is dropped, not refused.** Ask for
    `fax:read fax:write` with only `fax:read` granted and you receive a 200 carrying a token
    that holds `fax:read` alone. Read the scopes back from the token rather than assuming the
    request was honoured in full. A scope this platform does not publish at all is a different
    case: that is a `400 invalid_scope`.

    Args:
        body (TokenRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        OAuthError | TokenResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: TokenRequest,
) -> Response[OAuthError | TokenResponse]:
    """Exchange client credentials for a bearer token

     The OAuth 2.0 client-credentials grant (RFC 6749 §4.4). Send the client id and secret you
    were issued, plus the space-separated scopes you want.

    **A scope outside your client's ceiling is dropped, not refused.** Ask for
    `fax:read fax:write` with only `fax:read` granted and you receive a 200 carrying a token
    that holds `fax:read` alone. Read the scopes back from the token rather than assuming the
    request was honoured in full. A scope this platform does not publish at all is a different
    case: that is a `400 invalid_scope`.

    Args:
        body (TokenRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[OAuthError | TokenResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: TokenRequest,
) -> OAuthError | TokenResponse | None:
    """Exchange client credentials for a bearer token

     The OAuth 2.0 client-credentials grant (RFC 6749 §4.4). Send the client id and secret you
    were issued, plus the space-separated scopes you want.

    **A scope outside your client's ceiling is dropped, not refused.** Ask for
    `fax:read fax:write` with only `fax:read` granted and you receive a 200 carrying a token
    that holds `fax:read` alone. Read the scopes back from the token rather than assuming the
    request was honoured in full. A scope this platform does not publish at all is a different
    case: that is a `400 invalid_scope`.

    Args:
        body (TokenRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        OAuthError | TokenResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
