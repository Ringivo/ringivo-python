from http import HTTPStatus
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.cancel_fax_result import CancelFaxResult
from ...models.error_document import ErrorDocument
from ...types import Response


def _get_kwargs(
    fax: UUID,
) -> dict[str, Any]:

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/faxes/{fax}/cancel".format(
            fax=quote(str(fax), safe=""),
        ),
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> CancelFaxResult | ErrorDocument | None:
    if response.status_code == 200:
        response_200 = CancelFaxResult.from_dict(response.json())

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

    if response.status_code == 409:
        response_409 = ErrorDocument.from_dict(response.json())

        return response_409

    if response.status_code == 429:
        response_429 = ErrorDocument.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[CancelFaxResult | ErrorDocument]:
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
) -> Response[CancelFaxResult | ErrorDocument]:
    r"""Cancel a fax before the far end answers

     A decision recorded against a call that may already be up — which is why it is a verb and
    not `PATCH {status: \"cancelled\"}`. **200 and not 202**: the decision is complete when this
    returns, and no later result undoes it.

    Once the far end has answered, or the fax has already finished, it cannot be cancelled:
    that is a 409 whose `meta.reason` is `answered` or `terminal`. This refusal carries **no
    `code` member** — the status is the contract.

    Args:
        fax (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CancelFaxResult | ErrorDocument]
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
) -> CancelFaxResult | ErrorDocument | None:
    r"""Cancel a fax before the far end answers

     A decision recorded against a call that may already be up — which is why it is a verb and
    not `PATCH {status: \"cancelled\"}`. **200 and not 202**: the decision is complete when this
    returns, and no later result undoes it.

    Once the far end has answered, or the fax has already finished, it cannot be cancelled:
    that is a 409 whose `meta.reason` is `answered` or `terminal`. This refusal carries **no
    `code` member** — the status is the contract.

    Args:
        fax (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CancelFaxResult | ErrorDocument
    """

    return sync_detailed(
        fax=fax,
        client=client,
    ).parsed


async def asyncio_detailed(
    fax: UUID,
    *,
    client: AuthenticatedClient,
) -> Response[CancelFaxResult | ErrorDocument]:
    r"""Cancel a fax before the far end answers

     A decision recorded against a call that may already be up — which is why it is a verb and
    not `PATCH {status: \"cancelled\"}`. **200 and not 202**: the decision is complete when this
    returns, and no later result undoes it.

    Once the far end has answered, or the fax has already finished, it cannot be cancelled:
    that is a 409 whose `meta.reason` is `answered` or `terminal`. This refusal carries **no
    `code` member** — the status is the contract.

    Args:
        fax (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CancelFaxResult | ErrorDocument]
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
) -> CancelFaxResult | ErrorDocument | None:
    r"""Cancel a fax before the far end answers

     A decision recorded against a call that may already be up — which is why it is a verb and
    not `PATCH {status: \"cancelled\"}`. **200 and not 202**: the decision is complete when this
    returns, and no later result undoes it.

    Once the far end has answered, or the fax has already finished, it cannot be cancelled:
    that is a 409 whose `meta.reason` is `answered` or `terminal`. This refusal carries **no
    `code` member** — the status is the contract.

    Args:
        fax (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CancelFaxResult | ErrorDocument
    """

    return (
        await asyncio_detailed(
            fax=fax,
            client=client,
        )
    ).parsed
