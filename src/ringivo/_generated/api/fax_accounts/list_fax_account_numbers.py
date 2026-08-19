from http import HTTPStatus
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.phone_number_collection_document import PhoneNumberCollectionDocument
from ...types import UNSET, Response, Unset


def _get_kwargs(
    fax_account: UUID,
    *,
    pagesize: int | Unset = UNSET,
    pageafter: str | Unset = UNSET,
    pagebefore: str | Unset = UNSET,
    sort: str | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["page[size]"] = pagesize

    params["page[after]"] = pageafter

    params["page[before]"] = pagebefore

    params["sort"] = sort

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/fax-accounts/{fax_account}/numbers".format(
            fax_account=quote(str(fax_account), safe=""),
        ),
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDocument | PhoneNumberCollectionDocument | None:
    if response.status_code == 200:
        response_200 = PhoneNumberCollectionDocument.from_dict(response.json())

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
) -> Response[ErrorDocument | PhoneNumberCollectionDocument]:
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
    pagesize: int | Unset = UNSET,
    pageafter: str | Unset = UNSET,
    pagebefore: str | Unset = UNSET,
    sort: str | Unset = UNSET,
) -> Response[ErrorDocument | PhoneNumberCollectionDocument]:
    """List the numbers routed to a fax account

     Read-only. Attaching a number is the routing API's act, because a number points at one
    destination and that rule belongs to the number.

    Args:
        fax_account (UUID):
        pagesize (int | Unset):
        pageafter (str | Unset):
        pagebefore (str | Unset):
        sort (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | PhoneNumberCollectionDocument]
    """

    kwargs = _get_kwargs(
        fax_account=fax_account,
        pagesize=pagesize,
        pageafter=pageafter,
        pagebefore=pagebefore,
        sort=sort,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    fax_account: UUID,
    *,
    client: AuthenticatedClient,
    pagesize: int | Unset = UNSET,
    pageafter: str | Unset = UNSET,
    pagebefore: str | Unset = UNSET,
    sort: str | Unset = UNSET,
) -> ErrorDocument | PhoneNumberCollectionDocument | None:
    """List the numbers routed to a fax account

     Read-only. Attaching a number is the routing API's act, because a number points at one
    destination and that rule belongs to the number.

    Args:
        fax_account (UUID):
        pagesize (int | Unset):
        pageafter (str | Unset):
        pagebefore (str | Unset):
        sort (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | PhoneNumberCollectionDocument
    """

    return sync_detailed(
        fax_account=fax_account,
        client=client,
        pagesize=pagesize,
        pageafter=pageafter,
        pagebefore=pagebefore,
        sort=sort,
    ).parsed


async def asyncio_detailed(
    fax_account: UUID,
    *,
    client: AuthenticatedClient,
    pagesize: int | Unset = UNSET,
    pageafter: str | Unset = UNSET,
    pagebefore: str | Unset = UNSET,
    sort: str | Unset = UNSET,
) -> Response[ErrorDocument | PhoneNumberCollectionDocument]:
    """List the numbers routed to a fax account

     Read-only. Attaching a number is the routing API's act, because a number points at one
    destination and that rule belongs to the number.

    Args:
        fax_account (UUID):
        pagesize (int | Unset):
        pageafter (str | Unset):
        pagebefore (str | Unset):
        sort (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | PhoneNumberCollectionDocument]
    """

    kwargs = _get_kwargs(
        fax_account=fax_account,
        pagesize=pagesize,
        pageafter=pageafter,
        pagebefore=pagebefore,
        sort=sort,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    fax_account: UUID,
    *,
    client: AuthenticatedClient,
    pagesize: int | Unset = UNSET,
    pageafter: str | Unset = UNSET,
    pagebefore: str | Unset = UNSET,
    sort: str | Unset = UNSET,
) -> ErrorDocument | PhoneNumberCollectionDocument | None:
    """List the numbers routed to a fax account

     Read-only. Attaching a number is the routing API's act, because a number points at one
    destination and that rule belongs to the number.

    Args:
        fax_account (UUID):
        pagesize (int | Unset):
        pageafter (str | Unset):
        pagebefore (str | Unset):
        sort (str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | PhoneNumberCollectionDocument
    """

    return (
        await asyncio_detailed(
            fax_account=fax_account,
            client=client,
            pagesize=pagesize,
            pageafter=pageafter,
            pagebefore=pagebefore,
            sort=sort,
        )
    ).parsed
