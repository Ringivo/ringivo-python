from http import HTTPStatus
from typing import Any
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.fax_collection_document import FaxCollectionDocument
from ...models.fax_direction import FaxDirection
from ...models.fax_status import FaxStatus
from ...models.list_faxes_filtertag import ListFaxesFiltertag
from ...models.list_faxes_include import ListFaxesInclude
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    pagecursor: str | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    include: ListFaxesInclude | Unset = UNSET,
    filterfax_account: UUID | Unset = UNSET,
    filterdirection: FaxDirection | Unset = UNSET,
    filterstatus: FaxStatus | Unset = UNSET,
    filterfrom: str | Unset = UNSET,
    filterto: str | Unset = UNSET,
    filterclient_reference: str | Unset = UNSET,
    filtercreated_after: str | Unset = UNSET,
    filtercreated_before: str | Unset = UNSET,
    filterread: bool | Unset = UNSET,
    filterarchived: bool | Unset = UNSET,
    filtertag: ListFaxesFiltertag | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["page[cursor]"] = pagecursor

    params["page[size]"] = pagesize

    json_include: str | Unset = UNSET
    if not isinstance(include, Unset):
        json_include = include.value

    params["include"] = json_include

    json_filterfax_account: str | Unset = UNSET
    if not isinstance(filterfax_account, Unset):
        json_filterfax_account = str(filterfax_account)
    params["filter[fax_account]"] = json_filterfax_account

    json_filterdirection: str | Unset = UNSET
    if not isinstance(filterdirection, Unset):
        json_filterdirection = filterdirection.value

    params["filter[direction]"] = json_filterdirection

    json_filterstatus: str | Unset = UNSET
    if not isinstance(filterstatus, Unset):
        json_filterstatus = filterstatus.value

    params["filter[status]"] = json_filterstatus

    params["filter[from]"] = filterfrom

    params["filter[to]"] = filterto

    params["filter[client_reference]"] = filterclient_reference

    params["filter[created_after]"] = filtercreated_after

    params["filter[created_before]"] = filtercreated_before

    params["filter[read]"] = filterread

    params["filter[archived]"] = filterarchived

    json_filtertag: dict[str, Any] | Unset = UNSET
    if not isinstance(filtertag, Unset):
        json_filtertag = filtertag.to_dict()
    if not isinstance(json_filtertag, Unset):
        params.update(json_filtertag)

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/faxes",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDocument | FaxCollectionDocument | None:
    if response.status_code == 200:
        response_200 = FaxCollectionDocument.from_dict(response.json())

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
) -> Response[ErrorDocument | FaxCollectionDocument]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    pagecursor: str | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    include: ListFaxesInclude | Unset = UNSET,
    filterfax_account: UUID | Unset = UNSET,
    filterdirection: FaxDirection | Unset = UNSET,
    filterstatus: FaxStatus | Unset = UNSET,
    filterfrom: str | Unset = UNSET,
    filterto: str | Unset = UNSET,
    filterclient_reference: str | Unset = UNSET,
    filtercreated_after: str | Unset = UNSET,
    filtercreated_before: str | Unset = UNSET,
    filterread: bool | Unset = UNSET,
    filterarchived: bool | Unset = UNSET,
    filtertag: ListFaxesFiltertag | Unset = UNSET,
) -> Response[ErrorDocument | FaxCollectionDocument]:
    """List faxes

     The inbox and the outbox in one cursor-paginated collection, newest first. Nothing is
    sortable: the cursor's ordering IS the id ordering, so a client-supplied sort would make
    pages overlap.

    Args:
        pagecursor (str | Unset):
        pagesize (int | Unset):
        include (ListFaxesInclude | Unset):
        filterfax_account (UUID | Unset):
        filterdirection (FaxDirection | Unset):
        filterstatus (FaxStatus | Unset): `queued`, `converting`, `sending`, `delivered`,
            `partial` and `cancelled` belong to an
            outbound fax; `received` to an inbound one; `failed` to both.
        filterfrom (str | Unset):
        filterto (str | Unset):
        filterclient_reference (str | Unset):
        filtercreated_after (str | Unset):
        filtercreated_before (str | Unset):
        filterread (bool | Unset):
        filterarchived (bool | Unset):
        filtertag (ListFaxesFiltertag | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | FaxCollectionDocument]
    """

    kwargs = _get_kwargs(
        pagecursor=pagecursor,
        pagesize=pagesize,
        include=include,
        filterfax_account=filterfax_account,
        filterdirection=filterdirection,
        filterstatus=filterstatus,
        filterfrom=filterfrom,
        filterto=filterto,
        filterclient_reference=filterclient_reference,
        filtercreated_after=filtercreated_after,
        filtercreated_before=filtercreated_before,
        filterread=filterread,
        filterarchived=filterarchived,
        filtertag=filtertag,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    pagecursor: str | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    include: ListFaxesInclude | Unset = UNSET,
    filterfax_account: UUID | Unset = UNSET,
    filterdirection: FaxDirection | Unset = UNSET,
    filterstatus: FaxStatus | Unset = UNSET,
    filterfrom: str | Unset = UNSET,
    filterto: str | Unset = UNSET,
    filterclient_reference: str | Unset = UNSET,
    filtercreated_after: str | Unset = UNSET,
    filtercreated_before: str | Unset = UNSET,
    filterread: bool | Unset = UNSET,
    filterarchived: bool | Unset = UNSET,
    filtertag: ListFaxesFiltertag | Unset = UNSET,
) -> ErrorDocument | FaxCollectionDocument | None:
    """List faxes

     The inbox and the outbox in one cursor-paginated collection, newest first. Nothing is
    sortable: the cursor's ordering IS the id ordering, so a client-supplied sort would make
    pages overlap.

    Args:
        pagecursor (str | Unset):
        pagesize (int | Unset):
        include (ListFaxesInclude | Unset):
        filterfax_account (UUID | Unset):
        filterdirection (FaxDirection | Unset):
        filterstatus (FaxStatus | Unset): `queued`, `converting`, `sending`, `delivered`,
            `partial` and `cancelled` belong to an
            outbound fax; `received` to an inbound one; `failed` to both.
        filterfrom (str | Unset):
        filterto (str | Unset):
        filterclient_reference (str | Unset):
        filtercreated_after (str | Unset):
        filtercreated_before (str | Unset):
        filterread (bool | Unset):
        filterarchived (bool | Unset):
        filtertag (ListFaxesFiltertag | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | FaxCollectionDocument
    """

    return sync_detailed(
        client=client,
        pagecursor=pagecursor,
        pagesize=pagesize,
        include=include,
        filterfax_account=filterfax_account,
        filterdirection=filterdirection,
        filterstatus=filterstatus,
        filterfrom=filterfrom,
        filterto=filterto,
        filterclient_reference=filterclient_reference,
        filtercreated_after=filtercreated_after,
        filtercreated_before=filtercreated_before,
        filterread=filterread,
        filterarchived=filterarchived,
        filtertag=filtertag,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    pagecursor: str | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    include: ListFaxesInclude | Unset = UNSET,
    filterfax_account: UUID | Unset = UNSET,
    filterdirection: FaxDirection | Unset = UNSET,
    filterstatus: FaxStatus | Unset = UNSET,
    filterfrom: str | Unset = UNSET,
    filterto: str | Unset = UNSET,
    filterclient_reference: str | Unset = UNSET,
    filtercreated_after: str | Unset = UNSET,
    filtercreated_before: str | Unset = UNSET,
    filterread: bool | Unset = UNSET,
    filterarchived: bool | Unset = UNSET,
    filtertag: ListFaxesFiltertag | Unset = UNSET,
) -> Response[ErrorDocument | FaxCollectionDocument]:
    """List faxes

     The inbox and the outbox in one cursor-paginated collection, newest first. Nothing is
    sortable: the cursor's ordering IS the id ordering, so a client-supplied sort would make
    pages overlap.

    Args:
        pagecursor (str | Unset):
        pagesize (int | Unset):
        include (ListFaxesInclude | Unset):
        filterfax_account (UUID | Unset):
        filterdirection (FaxDirection | Unset):
        filterstatus (FaxStatus | Unset): `queued`, `converting`, `sending`, `delivered`,
            `partial` and `cancelled` belong to an
            outbound fax; `received` to an inbound one; `failed` to both.
        filterfrom (str | Unset):
        filterto (str | Unset):
        filterclient_reference (str | Unset):
        filtercreated_after (str | Unset):
        filtercreated_before (str | Unset):
        filterread (bool | Unset):
        filterarchived (bool | Unset):
        filtertag (ListFaxesFiltertag | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | FaxCollectionDocument]
    """

    kwargs = _get_kwargs(
        pagecursor=pagecursor,
        pagesize=pagesize,
        include=include,
        filterfax_account=filterfax_account,
        filterdirection=filterdirection,
        filterstatus=filterstatus,
        filterfrom=filterfrom,
        filterto=filterto,
        filterclient_reference=filterclient_reference,
        filtercreated_after=filtercreated_after,
        filtercreated_before=filtercreated_before,
        filterread=filterread,
        filterarchived=filterarchived,
        filtertag=filtertag,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    pagecursor: str | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    include: ListFaxesInclude | Unset = UNSET,
    filterfax_account: UUID | Unset = UNSET,
    filterdirection: FaxDirection | Unset = UNSET,
    filterstatus: FaxStatus | Unset = UNSET,
    filterfrom: str | Unset = UNSET,
    filterto: str | Unset = UNSET,
    filterclient_reference: str | Unset = UNSET,
    filtercreated_after: str | Unset = UNSET,
    filtercreated_before: str | Unset = UNSET,
    filterread: bool | Unset = UNSET,
    filterarchived: bool | Unset = UNSET,
    filtertag: ListFaxesFiltertag | Unset = UNSET,
) -> ErrorDocument | FaxCollectionDocument | None:
    """List faxes

     The inbox and the outbox in one cursor-paginated collection, newest first. Nothing is
    sortable: the cursor's ordering IS the id ordering, so a client-supplied sort would make
    pages overlap.

    Args:
        pagecursor (str | Unset):
        pagesize (int | Unset):
        include (ListFaxesInclude | Unset):
        filterfax_account (UUID | Unset):
        filterdirection (FaxDirection | Unset):
        filterstatus (FaxStatus | Unset): `queued`, `converting`, `sending`, `delivered`,
            `partial` and `cancelled` belong to an
            outbound fax; `received` to an inbound one; `failed` to both.
        filterfrom (str | Unset):
        filterto (str | Unset):
        filterclient_reference (str | Unset):
        filtercreated_after (str | Unset):
        filtercreated_before (str | Unset):
        filterread (bool | Unset):
        filterarchived (bool | Unset):
        filtertag (ListFaxesFiltertag | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | FaxCollectionDocument
    """

    return (
        await asyncio_detailed(
            client=client,
            pagecursor=pagecursor,
            pagesize=pagesize,
            include=include,
            filterfax_account=filterfax_account,
            filterdirection=filterdirection,
            filterstatus=filterstatus,
            filterfrom=filterfrom,
            filterto=filterto,
            filterclient_reference=filterclient_reference,
            filtercreated_after=filtercreated_after,
            filtercreated_before=filtercreated_before,
            filterread=filterread,
            filterarchived=filterarchived,
            filtertag=filtertag,
        )
    ).parsed
