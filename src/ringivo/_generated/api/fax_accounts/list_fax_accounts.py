from http import HTTPStatus
from typing import Any
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.fax_account_collection_document import FaxAccountCollectionDocument
from ...models.fax_account_status import FaxAccountStatus
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    pagenumber: int | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    sort: str | Unset = UNSET,
    filtercustomer: UUID | Unset = UNSET,
    filterstatus: FaxAccountStatus | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["page[number]"] = pagenumber

    params["page[size]"] = pagesize

    params["sort"] = sort

    json_filtercustomer: str | Unset = UNSET
    if not isinstance(filtercustomer, Unset):
        json_filtercustomer = str(filtercustomer)
    params["filter[customer]"] = json_filtercustomer

    json_filterstatus: str | Unset = UNSET
    if not isinstance(filterstatus, Unset):
        json_filterstatus = filterstatus.value

    params["filter[status]"] = json_filterstatus

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/fax-accounts",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDocument | FaxAccountCollectionDocument | None:
    if response.status_code == 200:
        response_200 = FaxAccountCollectionDocument.from_dict(response.json())

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
) -> Response[ErrorDocument | FaxAccountCollectionDocument]:
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
    sort: str | Unset = UNSET,
    filtercustomer: UUID | Unset = UNSET,
    filterstatus: FaxAccountStatus | Unset = UNSET,
) -> Response[ErrorDocument | FaxAccountCollectionDocument]:
    """List fax accounts

     Not paged by default — an account list is small and a backend syncing state wants all of it.
    A token issued for a person lists only the accounts that person was granted; a machine
    credential lists every account in its scope.

    Args:
        pagenumber (int | Unset):
        pagesize (int | Unset):
        sort (str | Unset):
        filtercustomer (UUID | Unset):
        filterstatus (FaxAccountStatus | Unset): A suspended account may receive faxes but not
            send them.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | FaxAccountCollectionDocument]
    """

    kwargs = _get_kwargs(
        pagenumber=pagenumber,
        pagesize=pagesize,
        sort=sort,
        filtercustomer=filtercustomer,
        filterstatus=filterstatus,
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
    sort: str | Unset = UNSET,
    filtercustomer: UUID | Unset = UNSET,
    filterstatus: FaxAccountStatus | Unset = UNSET,
) -> ErrorDocument | FaxAccountCollectionDocument | None:
    """List fax accounts

     Not paged by default — an account list is small and a backend syncing state wants all of it.
    A token issued for a person lists only the accounts that person was granted; a machine
    credential lists every account in its scope.

    Args:
        pagenumber (int | Unset):
        pagesize (int | Unset):
        sort (str | Unset):
        filtercustomer (UUID | Unset):
        filterstatus (FaxAccountStatus | Unset): A suspended account may receive faxes but not
            send them.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | FaxAccountCollectionDocument
    """

    return sync_detailed(
        client=client,
        pagenumber=pagenumber,
        pagesize=pagesize,
        sort=sort,
        filtercustomer=filtercustomer,
        filterstatus=filterstatus,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    pagenumber: int | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    sort: str | Unset = UNSET,
    filtercustomer: UUID | Unset = UNSET,
    filterstatus: FaxAccountStatus | Unset = UNSET,
) -> Response[ErrorDocument | FaxAccountCollectionDocument]:
    """List fax accounts

     Not paged by default — an account list is small and a backend syncing state wants all of it.
    A token issued for a person lists only the accounts that person was granted; a machine
    credential lists every account in its scope.

    Args:
        pagenumber (int | Unset):
        pagesize (int | Unset):
        sort (str | Unset):
        filtercustomer (UUID | Unset):
        filterstatus (FaxAccountStatus | Unset): A suspended account may receive faxes but not
            send them.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | FaxAccountCollectionDocument]
    """

    kwargs = _get_kwargs(
        pagenumber=pagenumber,
        pagesize=pagesize,
        sort=sort,
        filtercustomer=filtercustomer,
        filterstatus=filterstatus,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    pagenumber: int | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    sort: str | Unset = UNSET,
    filtercustomer: UUID | Unset = UNSET,
    filterstatus: FaxAccountStatus | Unset = UNSET,
) -> ErrorDocument | FaxAccountCollectionDocument | None:
    """List fax accounts

     Not paged by default — an account list is small and a backend syncing state wants all of it.
    A token issued for a person lists only the accounts that person was granted; a machine
    credential lists every account in its scope.

    Args:
        pagenumber (int | Unset):
        pagesize (int | Unset):
        sort (str | Unset):
        filtercustomer (UUID | Unset):
        filterstatus (FaxAccountStatus | Unset): A suspended account may receive faxes but not
            send them.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | FaxAccountCollectionDocument
    """

    return (
        await asyncio_detailed(
            client=client,
            pagenumber=pagenumber,
            pagesize=pagesize,
            sort=sort,
            filtercustomer=filtercustomer,
            filterstatus=filterstatus,
        )
    ).parsed
