from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.number_lookup_request import NumberLookupRequest
from ...models.number_lookup_result import NumberLookupResult
from ...types import Response


def _get_kwargs(
    *,
    body: NumberLookupRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/number-lookups",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDocument | NumberLookupResult | None:
    if response.status_code == 200:
        response_200 = NumberLookupResult.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = ErrorDocument.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ErrorDocument.from_dict(response.json())

        return response_403

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
) -> Response[ErrorDocument | NumberLookupResult]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: NumberLookupRequest,
) -> Response[ErrorDocument | NumberLookupResult]:
    r"""Look up a phone number

     Everything we can find out about one number: who carries it now, what name it presents, and
    whether it can receive text messages.

    **This call costs you money.** It is billed at your per-lookup rate, every time, for any
    number — including one you do not own and never will. There is no free or cached variant, and
    a repeated lookup of the same number is a second lookup.

    **It needs a personal access token, not a client-credentials token.** This is the only
    operation here with that requirement, and it follows from the line above: because a lookup
    spends your balance, it is not something a third-party integration's credential may do on
    your behalf. Mint a token for one of your own console users from the portal's Security page.
    That user needs permission to look numbers up, which is held by exactly the roles that can
    already buy a number — so if they can purchase a DID, they can run a lookup.

    **A POST, not a GET, for that reason.** A GET is safe and idempotent by definition, so
    proxies, prefetchers and retry logic are entitled to repeat one — and each repeat would be
    another charge.

    **Nothing is stored.** We return the answer and keep no copy of it, so there is no
    `GET /v1/number-lookups/{id}` to come back to and no id to come back with. Keep what you need
    from the response.

    ## The two geographies are two different facts

    `dialedNumber` describes the number you asked about. `components.lrn.data.rateCenter` and
    `.state` describe its **LRN** — the routing number it currently ports to. **They frequently
    disagree, and both are right**: `6502530000` is `MT VIEW` by dialed number and `MILLVALLEY`
    by LRN. Do not merge them, and do not treat one as a correction of the other. Use the LRN's
    when you care where the call actually lands, and the dialed number's when you care where the
    number is nominally from.

    `dialedNumber.rateCenter` and `.state` are `null` for a toll-free number. That is **absent,
    not missing**: toll-free numbers are assigned individually rather than in geographic blocks,
    so there is no rate center to report. Nothing failed.

    ## Read `status` before you read `data`

    Each of the three components reports its own outcome, and `data` is `null` for two of them:

    | `status` | What it means | Charged |
    |---|---|---|
    | `answered` | The provider returned data. It is in `data`. | yes |
    | `no_data` | The provider answered, and holds nothing for this number. | yes |
    | `failed` | We could not get an answer. | see `charged` |

    **`no_data` and `failed` are not the same fact.** \"This number has no CNAM record\" and \"we
    could not ask\" look identical if you only check `data == null`, and only the first is
    something to show a user as an answer.

    `charged` tells you whether this lookup was billed. A lookup where **some** components
    answered is billed in full; one where **every** component failed is not billed at all.

    Args:
        body (NumberLookupRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | NumberLookupResult]
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
    body: NumberLookupRequest,
) -> ErrorDocument | NumberLookupResult | None:
    r"""Look up a phone number

     Everything we can find out about one number: who carries it now, what name it presents, and
    whether it can receive text messages.

    **This call costs you money.** It is billed at your per-lookup rate, every time, for any
    number — including one you do not own and never will. There is no free or cached variant, and
    a repeated lookup of the same number is a second lookup.

    **It needs a personal access token, not a client-credentials token.** This is the only
    operation here with that requirement, and it follows from the line above: because a lookup
    spends your balance, it is not something a third-party integration's credential may do on
    your behalf. Mint a token for one of your own console users from the portal's Security page.
    That user needs permission to look numbers up, which is held by exactly the roles that can
    already buy a number — so if they can purchase a DID, they can run a lookup.

    **A POST, not a GET, for that reason.** A GET is safe and idempotent by definition, so
    proxies, prefetchers and retry logic are entitled to repeat one — and each repeat would be
    another charge.

    **Nothing is stored.** We return the answer and keep no copy of it, so there is no
    `GET /v1/number-lookups/{id}` to come back to and no id to come back with. Keep what you need
    from the response.

    ## The two geographies are two different facts

    `dialedNumber` describes the number you asked about. `components.lrn.data.rateCenter` and
    `.state` describe its **LRN** — the routing number it currently ports to. **They frequently
    disagree, and both are right**: `6502530000` is `MT VIEW` by dialed number and `MILLVALLEY`
    by LRN. Do not merge them, and do not treat one as a correction of the other. Use the LRN's
    when you care where the call actually lands, and the dialed number's when you care where the
    number is nominally from.

    `dialedNumber.rateCenter` and `.state` are `null` for a toll-free number. That is **absent,
    not missing**: toll-free numbers are assigned individually rather than in geographic blocks,
    so there is no rate center to report. Nothing failed.

    ## Read `status` before you read `data`

    Each of the three components reports its own outcome, and `data` is `null` for two of them:

    | `status` | What it means | Charged |
    |---|---|---|
    | `answered` | The provider returned data. It is in `data`. | yes |
    | `no_data` | The provider answered, and holds nothing for this number. | yes |
    | `failed` | We could not get an answer. | see `charged` |

    **`no_data` and `failed` are not the same fact.** \"This number has no CNAM record\" and \"we
    could not ask\" look identical if you only check `data == null`, and only the first is
    something to show a user as an answer.

    `charged` tells you whether this lookup was billed. A lookup where **some** components
    answered is billed in full; one where **every** component failed is not billed at all.

    Args:
        body (NumberLookupRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | NumberLookupResult
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: NumberLookupRequest,
) -> Response[ErrorDocument | NumberLookupResult]:
    r"""Look up a phone number

     Everything we can find out about one number: who carries it now, what name it presents, and
    whether it can receive text messages.

    **This call costs you money.** It is billed at your per-lookup rate, every time, for any
    number — including one you do not own and never will. There is no free or cached variant, and
    a repeated lookup of the same number is a second lookup.

    **It needs a personal access token, not a client-credentials token.** This is the only
    operation here with that requirement, and it follows from the line above: because a lookup
    spends your balance, it is not something a third-party integration's credential may do on
    your behalf. Mint a token for one of your own console users from the portal's Security page.
    That user needs permission to look numbers up, which is held by exactly the roles that can
    already buy a number — so if they can purchase a DID, they can run a lookup.

    **A POST, not a GET, for that reason.** A GET is safe and idempotent by definition, so
    proxies, prefetchers and retry logic are entitled to repeat one — and each repeat would be
    another charge.

    **Nothing is stored.** We return the answer and keep no copy of it, so there is no
    `GET /v1/number-lookups/{id}` to come back to and no id to come back with. Keep what you need
    from the response.

    ## The two geographies are two different facts

    `dialedNumber` describes the number you asked about. `components.lrn.data.rateCenter` and
    `.state` describe its **LRN** — the routing number it currently ports to. **They frequently
    disagree, and both are right**: `6502530000` is `MT VIEW` by dialed number and `MILLVALLEY`
    by LRN. Do not merge them, and do not treat one as a correction of the other. Use the LRN's
    when you care where the call actually lands, and the dialed number's when you care where the
    number is nominally from.

    `dialedNumber.rateCenter` and `.state` are `null` for a toll-free number. That is **absent,
    not missing**: toll-free numbers are assigned individually rather than in geographic blocks,
    so there is no rate center to report. Nothing failed.

    ## Read `status` before you read `data`

    Each of the three components reports its own outcome, and `data` is `null` for two of them:

    | `status` | What it means | Charged |
    |---|---|---|
    | `answered` | The provider returned data. It is in `data`. | yes |
    | `no_data` | The provider answered, and holds nothing for this number. | yes |
    | `failed` | We could not get an answer. | see `charged` |

    **`no_data` and `failed` are not the same fact.** \"This number has no CNAM record\" and \"we
    could not ask\" look identical if you only check `data == null`, and only the first is
    something to show a user as an answer.

    `charged` tells you whether this lookup was billed. A lookup where **some** components
    answered is billed in full; one where **every** component failed is not billed at all.

    Args:
        body (NumberLookupRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | NumberLookupResult]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: NumberLookupRequest,
) -> ErrorDocument | NumberLookupResult | None:
    r"""Look up a phone number

     Everything we can find out about one number: who carries it now, what name it presents, and
    whether it can receive text messages.

    **This call costs you money.** It is billed at your per-lookup rate, every time, for any
    number — including one you do not own and never will. There is no free or cached variant, and
    a repeated lookup of the same number is a second lookup.

    **It needs a personal access token, not a client-credentials token.** This is the only
    operation here with that requirement, and it follows from the line above: because a lookup
    spends your balance, it is not something a third-party integration's credential may do on
    your behalf. Mint a token for one of your own console users from the portal's Security page.
    That user needs permission to look numbers up, which is held by exactly the roles that can
    already buy a number — so if they can purchase a DID, they can run a lookup.

    **A POST, not a GET, for that reason.** A GET is safe and idempotent by definition, so
    proxies, prefetchers and retry logic are entitled to repeat one — and each repeat would be
    another charge.

    **Nothing is stored.** We return the answer and keep no copy of it, so there is no
    `GET /v1/number-lookups/{id}` to come back to and no id to come back with. Keep what you need
    from the response.

    ## The two geographies are two different facts

    `dialedNumber` describes the number you asked about. `components.lrn.data.rateCenter` and
    `.state` describe its **LRN** — the routing number it currently ports to. **They frequently
    disagree, and both are right**: `6502530000` is `MT VIEW` by dialed number and `MILLVALLEY`
    by LRN. Do not merge them, and do not treat one as a correction of the other. Use the LRN's
    when you care where the call actually lands, and the dialed number's when you care where the
    number is nominally from.

    `dialedNumber.rateCenter` and `.state` are `null` for a toll-free number. That is **absent,
    not missing**: toll-free numbers are assigned individually rather than in geographic blocks,
    so there is no rate center to report. Nothing failed.

    ## Read `status` before you read `data`

    Each of the three components reports its own outcome, and `data` is `null` for two of them:

    | `status` | What it means | Charged |
    |---|---|---|
    | `answered` | The provider returned data. It is in `data`. | yes |
    | `no_data` | The provider answered, and holds nothing for this number. | yes |
    | `failed` | We could not get an answer. | see `charged` |

    **`no_data` and `failed` are not the same fact.** \"This number has no CNAM record\" and \"we
    could not ask\" look identical if you only check `data == null`, and only the first is
    something to show a user as an answer.

    `charged` tells you whether this lookup was billed. A lookup where **some** components
    answered is billed in full; one where **every** component failed is not billed at all.

    Args:
        body (NumberLookupRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | NumberLookupResult
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
