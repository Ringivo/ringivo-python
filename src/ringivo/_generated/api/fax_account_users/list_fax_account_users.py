from http import HTTPStatus
from typing import Any
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.fax_account_user_collection_document import FaxAccountUserCollectionDocument
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    pagenumber: int | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    filterfax_account: UUID | Unset = UNSET,
    filteruser: UUID | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["page[number]"] = pagenumber

    params["page[size]"] = pagesize

    json_filterfax_account: str | Unset = UNSET
    if not isinstance(filterfax_account, Unset):
        json_filterfax_account = str(filterfax_account)
    params["filter[fax_account]"] = json_filterfax_account

    json_filteruser: str | Unset = UNSET
    if not isinstance(filteruser, Unset):
        json_filteruser = str(filteruser)
    params["filter[user]"] = json_filteruser

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/fax-account-users",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDocument | FaxAccountUserCollectionDocument | None:
    if response.status_code == 200:
        response_200 = FaxAccountUserCollectionDocument.from_dict(response.json())

        return response_200

    if response.status_code == 400:
        response_400 = ErrorDocument.from_dict(response.json())

        return response_400

    if response.status_code == 401:
        response_401 = ErrorDocument.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ErrorDocument.from_dict(response.json())

        return response_403

    if response.status_code == 429:
        response_429 = ErrorDocument.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDocument | FaxAccountUserCollectionDocument]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    pagenumber: int | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    filterfax_account: UUID | Unset = UNSET,
    filteruser: UUID | Unset = UNSET,
) -> Response[ErrorDocument | FaxAccountUserCollectionDocument]:
    r"""List fax-account grants

     One row per (user, fax account) pair — the answer to \"who can see this account's faxes?\".

    Args:
        pagenumber (int | Unset):
        pagesize (int | Unset):
        filterfax_account (UUID | Unset):
        filteruser (UUID | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | FaxAccountUserCollectionDocument]
    """

    kwargs = _get_kwargs(
        pagenumber=pagenumber,
        pagesize=pagesize,
        filterfax_account=filterfax_account,
        filteruser=filteruser,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    pagenumber: int | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    filterfax_account: UUID | Unset = UNSET,
    filteruser: UUID | Unset = UNSET,
) -> ErrorDocument | FaxAccountUserCollectionDocument | None:
    r"""List fax-account grants

     One row per (user, fax account) pair — the answer to \"who can see this account's faxes?\".

    Args:
        pagenumber (int | Unset):
        pagesize (int | Unset):
        filterfax_account (UUID | Unset):
        filteruser (UUID | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | FaxAccountUserCollectionDocument
    """

    return sync_detailed(
        client=client,
        pagenumber=pagenumber,
        pagesize=pagesize,
        filterfax_account=filterfax_account,
        filteruser=filteruser,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    pagenumber: int | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    filterfax_account: UUID | Unset = UNSET,
    filteruser: UUID | Unset = UNSET,
) -> Response[ErrorDocument | FaxAccountUserCollectionDocument]:
    r"""List fax-account grants

     One row per (user, fax account) pair — the answer to \"who can see this account's faxes?\".

    Args:
        pagenumber (int | Unset):
        pagesize (int | Unset):
        filterfax_account (UUID | Unset):
        filteruser (UUID | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | FaxAccountUserCollectionDocument]
    """

    kwargs = _get_kwargs(
        pagenumber=pagenumber,
        pagesize=pagesize,
        filterfax_account=filterfax_account,
        filteruser=filteruser,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    pagenumber: int | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    filterfax_account: UUID | Unset = UNSET,
    filteruser: UUID | Unset = UNSET,
) -> ErrorDocument | FaxAccountUserCollectionDocument | None:
    r"""List fax-account grants

     One row per (user, fax account) pair — the answer to \"who can see this account's faxes?\".

    Args:
        pagenumber (int | Unset):
        pagesize (int | Unset):
        filterfax_account (UUID | Unset):
        filteruser (UUID | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | FaxAccountUserCollectionDocument
    """

    return (
        await asyncio_detailed(
            client=client,
            pagenumber=pagenumber,
            pagesize=pagesize,
            filterfax_account=filterfax_account,
            filteruser=filteruser,
        )
    ).parsed
