from http import HTTPStatus
from typing import Any
from uuid import UUID

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.webhook_endpoint_collection_document import WebhookEndpointCollectionDocument
from ...models.webhook_scope_type import WebhookScopeType
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    pagenumber: int | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    sort: str | Unset = UNSET,
    filterscope_type: WebhookScopeType | Unset = UNSET,
    filterscope_id: UUID | Unset = UNSET,
    filteractive: bool | Unset = UNSET,
) -> dict[str, Any]:

    params: dict[str, Any] = {}

    params["page[number]"] = pagenumber

    params["page[size]"] = pagesize

    params["sort"] = sort

    json_filterscope_type: str | Unset = UNSET
    if not isinstance(filterscope_type, Unset):
        json_filterscope_type = filterscope_type.value

    params["filter[scope_type]"] = json_filterscope_type

    json_filterscope_id: str | Unset = UNSET
    if not isinstance(filterscope_id, Unset):
        json_filterscope_id = str(filterscope_id)
    params["filter[scope_id]"] = json_filterscope_id

    params["filter[active]"] = filteractive

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/v1/webhook-endpoints",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDocument | WebhookEndpointCollectionDocument | None:
    if response.status_code == 200:
        response_200 = WebhookEndpointCollectionDocument.from_dict(response.json())

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
) -> Response[ErrorDocument | WebhookEndpointCollectionDocument]:
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
    filterscope_type: WebhookScopeType | Unset = UNSET,
    filterscope_id: UUID | Unset = UNSET,
    filteractive: bool | Unset = UNSET,
) -> Response[ErrorDocument | WebhookEndpointCollectionDocument]:
    r"""List webhook endpoints

     **No response ever carries a signing secret** except the create and the rotate that minted
    it. Every other read answers `\"secret\": null` — an honest statement that the platform holds
    no readable copy.

    **Scope:** `fax:read` lists only **fax-account-scoped** endpoints; customer- and
    tenant-scoped endpoints are absent from that list and require `webhooks:read`.

    Args:
        pagenumber (int | Unset):
        pagesize (int | Unset):
        sort (str | Unset):
        filterscope_type (WebhookScopeType | Unset): What an endpoint hears about. All three are
            matched as a containment order, so a
            reseller-wide endpoint and a per-account one both hear about the same fax.
        filterscope_id (UUID | Unset):
        filteractive (bool | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | WebhookEndpointCollectionDocument]
    """

    kwargs = _get_kwargs(
        pagenumber=pagenumber,
        pagesize=pagesize,
        sort=sort,
        filterscope_type=filterscope_type,
        filterscope_id=filterscope_id,
        filteractive=filteractive,
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
    filterscope_type: WebhookScopeType | Unset = UNSET,
    filterscope_id: UUID | Unset = UNSET,
    filteractive: bool | Unset = UNSET,
) -> ErrorDocument | WebhookEndpointCollectionDocument | None:
    r"""List webhook endpoints

     **No response ever carries a signing secret** except the create and the rotate that minted
    it. Every other read answers `\"secret\": null` — an honest statement that the platform holds
    no readable copy.

    **Scope:** `fax:read` lists only **fax-account-scoped** endpoints; customer- and
    tenant-scoped endpoints are absent from that list and require `webhooks:read`.

    Args:
        pagenumber (int | Unset):
        pagesize (int | Unset):
        sort (str | Unset):
        filterscope_type (WebhookScopeType | Unset): What an endpoint hears about. All three are
            matched as a containment order, so a
            reseller-wide endpoint and a per-account one both hear about the same fax.
        filterscope_id (UUID | Unset):
        filteractive (bool | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | WebhookEndpointCollectionDocument
    """

    return sync_detailed(
        client=client,
        pagenumber=pagenumber,
        pagesize=pagesize,
        sort=sort,
        filterscope_type=filterscope_type,
        filterscope_id=filterscope_id,
        filteractive=filteractive,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    pagenumber: int | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    sort: str | Unset = UNSET,
    filterscope_type: WebhookScopeType | Unset = UNSET,
    filterscope_id: UUID | Unset = UNSET,
    filteractive: bool | Unset = UNSET,
) -> Response[ErrorDocument | WebhookEndpointCollectionDocument]:
    r"""List webhook endpoints

     **No response ever carries a signing secret** except the create and the rotate that minted
    it. Every other read answers `\"secret\": null` — an honest statement that the platform holds
    no readable copy.

    **Scope:** `fax:read` lists only **fax-account-scoped** endpoints; customer- and
    tenant-scoped endpoints are absent from that list and require `webhooks:read`.

    Args:
        pagenumber (int | Unset):
        pagesize (int | Unset):
        sort (str | Unset):
        filterscope_type (WebhookScopeType | Unset): What an endpoint hears about. All three are
            matched as a containment order, so a
            reseller-wide endpoint and a per-account one both hear about the same fax.
        filterscope_id (UUID | Unset):
        filteractive (bool | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | WebhookEndpointCollectionDocument]
    """

    kwargs = _get_kwargs(
        pagenumber=pagenumber,
        pagesize=pagesize,
        sort=sort,
        filterscope_type=filterscope_type,
        filterscope_id=filterscope_id,
        filteractive=filteractive,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    pagenumber: int | Unset = UNSET,
    pagesize: int | Unset = UNSET,
    sort: str | Unset = UNSET,
    filterscope_type: WebhookScopeType | Unset = UNSET,
    filterscope_id: UUID | Unset = UNSET,
    filteractive: bool | Unset = UNSET,
) -> ErrorDocument | WebhookEndpointCollectionDocument | None:
    r"""List webhook endpoints

     **No response ever carries a signing secret** except the create and the rotate that minted
    it. Every other read answers `\"secret\": null` — an honest statement that the platform holds
    no readable copy.

    **Scope:** `fax:read` lists only **fax-account-scoped** endpoints; customer- and
    tenant-scoped endpoints are absent from that list and require `webhooks:read`.

    Args:
        pagenumber (int | Unset):
        pagesize (int | Unset):
        sort (str | Unset):
        filterscope_type (WebhookScopeType | Unset): What an endpoint hears about. All three are
            matched as a containment order, so a
            reseller-wide endpoint and a per-account one both hear about the same fax.
        filterscope_id (UUID | Unset):
        filteractive (bool | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | WebhookEndpointCollectionDocument
    """

    return (
        await asyncio_detailed(
            client=client,
            pagenumber=pagenumber,
            pagesize=pagesize,
            sort=sort,
            filterscope_type=filterscope_type,
            filterscope_id=filterscope_id,
            filteractive=filteractive,
        )
    ).parsed
