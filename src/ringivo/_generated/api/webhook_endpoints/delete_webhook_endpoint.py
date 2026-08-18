from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...types import Response


def _get_kwargs(
    webhook_endpoint: UUID,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/v1/webhook-endpoints/{webhook_endpoint}".format(
            webhook_endpoint=quote(str(webhook_endpoint), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | ErrorDocument | None:
    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

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
) -> Response[Any | ErrorDocument]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    webhook_endpoint: UUID,
    *,
    client: AuthenticatedClient,
) -> Response[Any | ErrorDocument]:
    r"""Remove a webhook endpoint

     The fan-out stops at once. **The delivery history survives** — \"why did our integration stop
    hearing about faxes?\" is answered by the deliveries of the endpoint somebody removed.

    **Scope:** `fax:write` reaches only **fax-account-scoped** endpoints; a customer- or
    tenant-scoped endpoint answers **404** to a `fax:*` token and requires `webhooks:write`.

    Args:
        webhook_endpoint (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ErrorDocument]
    """

    kwargs = _get_kwargs(
        webhook_endpoint=webhook_endpoint,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    webhook_endpoint: UUID,
    *,
    client: AuthenticatedClient,
) -> Any | ErrorDocument | None:
    r"""Remove a webhook endpoint

     The fan-out stops at once. **The delivery history survives** — \"why did our integration stop
    hearing about faxes?\" is answered by the deliveries of the endpoint somebody removed.

    **Scope:** `fax:write` reaches only **fax-account-scoped** endpoints; a customer- or
    tenant-scoped endpoint answers **404** to a `fax:*` token and requires `webhooks:write`.

    Args:
        webhook_endpoint (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ErrorDocument
    """

    return sync_detailed(
        webhook_endpoint=webhook_endpoint,
        client=client,
    ).parsed


async def asyncio_detailed(
    webhook_endpoint: UUID,
    *,
    client: AuthenticatedClient,
) -> Response[Any | ErrorDocument]:
    r"""Remove a webhook endpoint

     The fan-out stops at once. **The delivery history survives** — \"why did our integration stop
    hearing about faxes?\" is answered by the deliveries of the endpoint somebody removed.

    **Scope:** `fax:write` reaches only **fax-account-scoped** endpoints; a customer- or
    tenant-scoped endpoint answers **404** to a `fax:*` token and requires `webhooks:write`.

    Args:
        webhook_endpoint (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | ErrorDocument]
    """

    kwargs = _get_kwargs(
        webhook_endpoint=webhook_endpoint,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    webhook_endpoint: UUID,
    *,
    client: AuthenticatedClient,
) -> Any | ErrorDocument | None:
    r"""Remove a webhook endpoint

     The fan-out stops at once. **The delivery history survives** — \"why did our integration stop
    hearing about faxes?\" is answered by the deliveries of the endpoint somebody removed.

    **Scope:** `fax:write` reaches only **fax-account-scoped** endpoints; a customer- or
    tenant-scoped endpoint answers **404** to a `fax:*` token and requires `webhooks:write`.

    Args:
        webhook_endpoint (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | ErrorDocument
    """

    return (
        await asyncio_detailed(
            webhook_endpoint=webhook_endpoint,
            client=client,
        )
    ).parsed
