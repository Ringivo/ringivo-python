from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.integration_token_request import IntegrationTokenRequest
from ...models.integration_token_response import IntegrationTokenResponse
from ...types import Response


def _get_kwargs(
    *,
    body: IntegrationTokenRequest,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/integration/token",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDocument | IntegrationTokenResponse | None:
    if response.status_code == 200:
        response_200 = IntegrationTokenResponse.from_dict(response.json())

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
) -> Response[ErrorDocument | IntegrationTokenResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: IntegrationTokenRequest,
) -> Response[ErrorDocument | IntegrationTokenResponse]:
    r"""Exchange client credentials for a tenant- or customer-scoped token

     The token a machine client presents to the rest of this API. Send the client id and secret
    you were issued, name the **tenant** you are acting for, and you get back a token that
    carries that tenant — and, when you name one, a **customer** inside it.

    Which rows you reach is decided by the token, never by a header or a path you send later.
    That is why the tenant is named here and nowhere else: acting for another tenant means
    asking for another token, and one token is one context for its whole life.

    The token lasts **15 minutes**. There is no refresh token — mint another when it expires.

    ## Your client must already hold a grant

    Credentials alone are not access. A **grant** is a record your reseller wrote that says
    *this client may act for this tenant, with at most these scopes*, optionally narrowed to one
    **customer** inside that tenant. If no active grant matches what you asked for, this
    endpoint answers **403** however good your credentials are.

    Grants are made out of band and never through this API. Ask the reseller whose platform you
    are integrating with for a client id, its secret, and the grant behind them.

    ## Two acts stand behind a customer-scoped credential

    A credential that acts for **one customer** of a reseller exists only after two separate
    acts by two different parties:

    1. the **reseller** turns API access on for that one customer and picks the scopes it may
       ever hold — its ceiling. This is the act that writes the grant.
    2. the **customer** then has its own credential created inside that ceiling.

    Neither act happens through this API, and together they are the whole answer to *why can my
    client mint a token for customer A but not for customer B?* — a grant exists for A and not
    for B.

    ## `customer` selects a context; by itself it narrows nothing

    Naming a customer **selects a grant somebody already wrote for it**. It never trims a wider
    grant down. A client holding only a tenant-wide grant cannot obtain a customer-scoped token
    by naming a customer, and a client granted customer A cannot reach customer B by asking. So
    there is no narrowing step you can forget: omit `customer` and you get the tenant-wide token
    your tenant-wide grant allows; name one and you get that customer's token, or a 403.

    That 403 reads the same for a tenant nobody granted you and for a customer nobody granted
    you. This is deliberate: a different message would let a caller discover which of a
    reseller's customers a client has been enabled for.

    ## Your scopes are an intersection, and a dropped scope is silent

    The scopes on the token are

    ```
    requested ∩ granted ∩ (customer named ? customer-scopeable : everything)
    ```

    **A scope outside that set is dropped, not refused.** You get a 200 carrying a token that
    simply does not hold it. That covers a scope your grant does not carry, a scope no customer
    credential may hold, **and a scope name this platform does not publish at all** — so a typo
    costs you a capability rather than an error.

    So **read `scopes` back off the response** and treat it as the authoritative answer. A call
    made on the assumption that you got what you asked for fails later at the resource instead,
    with a 403 that looks unrelated to this one.

    **`scopes` is optional and you almost always want it.** Leave it out and the intersection is
    empty: the request succeeds and hands you a token that carries no scopes and is refused by
    every resource you spend it on.

    ## Which scopes a customer-scoped token may hold

    Only scopes marked customer-scopeable survive that third intersection. Today they are
    `numbers:read` and `numbers:route`.

    **`numbers:assign` is not one of them and cannot be.** Assignment decides which customer a
    number belongs to, so it is never self-served by that customer's own credential; a token
    carrying it would be refused at every number it tried to assign. Ask for it on a
    customer-scoped token and it is dropped like any other unflagged scope:

    ```
    POST /v1/integration/token
    { \"client_id\": \"…\", \"client_secret\": \"…\", \"tenant\": \"…\", \"customer\": \"…\",
      \"scopes\": [\"numbers:read\", \"numbers:assign\", \"numbers:route\"] }

    200 OK
    { \"token_type\": \"Bearer\", \"expires_in\": 900,
      \"scopes\": [\"numbers:read\", \"numbers:route\"] }
    ```

    A tenant-wide credential is a different case: it may hold `numbers:assign`, and moving
    numbers between customers is exactly what it is for.

    ## Revocation, with its real clock

    Your grant is re-checked on **every** request you make with the token, not only when the
    token is minted. So a reseller who withdraws a grant, or a customer who revokes the
    credential, stops you on your next call rather than at the end of the token's 15 minutes.

    Reaching every region takes a moment: the answer is cached per region. In practice the cut
    lands well under a second, but **30 seconds** is the worst case to design against — never
    \"immediate\".

    Rotating a secret is not a revocation: it stops the old secret minting NEW tokens and leaves
    tokens already minted alive until they expire.

    Args:
        body (IntegrationTokenRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | IntegrationTokenResponse]
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
    body: IntegrationTokenRequest,
) -> ErrorDocument | IntegrationTokenResponse | None:
    r"""Exchange client credentials for a tenant- or customer-scoped token

     The token a machine client presents to the rest of this API. Send the client id and secret
    you were issued, name the **tenant** you are acting for, and you get back a token that
    carries that tenant — and, when you name one, a **customer** inside it.

    Which rows you reach is decided by the token, never by a header or a path you send later.
    That is why the tenant is named here and nowhere else: acting for another tenant means
    asking for another token, and one token is one context for its whole life.

    The token lasts **15 minutes**. There is no refresh token — mint another when it expires.

    ## Your client must already hold a grant

    Credentials alone are not access. A **grant** is a record your reseller wrote that says
    *this client may act for this tenant, with at most these scopes*, optionally narrowed to one
    **customer** inside that tenant. If no active grant matches what you asked for, this
    endpoint answers **403** however good your credentials are.

    Grants are made out of band and never through this API. Ask the reseller whose platform you
    are integrating with for a client id, its secret, and the grant behind them.

    ## Two acts stand behind a customer-scoped credential

    A credential that acts for **one customer** of a reseller exists only after two separate
    acts by two different parties:

    1. the **reseller** turns API access on for that one customer and picks the scopes it may
       ever hold — its ceiling. This is the act that writes the grant.
    2. the **customer** then has its own credential created inside that ceiling.

    Neither act happens through this API, and together they are the whole answer to *why can my
    client mint a token for customer A but not for customer B?* — a grant exists for A and not
    for B.

    ## `customer` selects a context; by itself it narrows nothing

    Naming a customer **selects a grant somebody already wrote for it**. It never trims a wider
    grant down. A client holding only a tenant-wide grant cannot obtain a customer-scoped token
    by naming a customer, and a client granted customer A cannot reach customer B by asking. So
    there is no narrowing step you can forget: omit `customer` and you get the tenant-wide token
    your tenant-wide grant allows; name one and you get that customer's token, or a 403.

    That 403 reads the same for a tenant nobody granted you and for a customer nobody granted
    you. This is deliberate: a different message would let a caller discover which of a
    reseller's customers a client has been enabled for.

    ## Your scopes are an intersection, and a dropped scope is silent

    The scopes on the token are

    ```
    requested ∩ granted ∩ (customer named ? customer-scopeable : everything)
    ```

    **A scope outside that set is dropped, not refused.** You get a 200 carrying a token that
    simply does not hold it. That covers a scope your grant does not carry, a scope no customer
    credential may hold, **and a scope name this platform does not publish at all** — so a typo
    costs you a capability rather than an error.

    So **read `scopes` back off the response** and treat it as the authoritative answer. A call
    made on the assumption that you got what you asked for fails later at the resource instead,
    with a 403 that looks unrelated to this one.

    **`scopes` is optional and you almost always want it.** Leave it out and the intersection is
    empty: the request succeeds and hands you a token that carries no scopes and is refused by
    every resource you spend it on.

    ## Which scopes a customer-scoped token may hold

    Only scopes marked customer-scopeable survive that third intersection. Today they are
    `numbers:read` and `numbers:route`.

    **`numbers:assign` is not one of them and cannot be.** Assignment decides which customer a
    number belongs to, so it is never self-served by that customer's own credential; a token
    carrying it would be refused at every number it tried to assign. Ask for it on a
    customer-scoped token and it is dropped like any other unflagged scope:

    ```
    POST /v1/integration/token
    { \"client_id\": \"…\", \"client_secret\": \"…\", \"tenant\": \"…\", \"customer\": \"…\",
      \"scopes\": [\"numbers:read\", \"numbers:assign\", \"numbers:route\"] }

    200 OK
    { \"token_type\": \"Bearer\", \"expires_in\": 900,
      \"scopes\": [\"numbers:read\", \"numbers:route\"] }
    ```

    A tenant-wide credential is a different case: it may hold `numbers:assign`, and moving
    numbers between customers is exactly what it is for.

    ## Revocation, with its real clock

    Your grant is re-checked on **every** request you make with the token, not only when the
    token is minted. So a reseller who withdraws a grant, or a customer who revokes the
    credential, stops you on your next call rather than at the end of the token's 15 minutes.

    Reaching every region takes a moment: the answer is cached per region. In practice the cut
    lands well under a second, but **30 seconds** is the worst case to design against — never
    \"immediate\".

    Rotating a secret is not a revocation: it stops the old secret minting NEW tokens and leaves
    tokens already minted alive until they expire.

    Args:
        body (IntegrationTokenRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | IntegrationTokenResponse
    """

    return sync_detailed(
        client=client,
        body=body,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: IntegrationTokenRequest,
) -> Response[ErrorDocument | IntegrationTokenResponse]:
    r"""Exchange client credentials for a tenant- or customer-scoped token

     The token a machine client presents to the rest of this API. Send the client id and secret
    you were issued, name the **tenant** you are acting for, and you get back a token that
    carries that tenant — and, when you name one, a **customer** inside it.

    Which rows you reach is decided by the token, never by a header or a path you send later.
    That is why the tenant is named here and nowhere else: acting for another tenant means
    asking for another token, and one token is one context for its whole life.

    The token lasts **15 minutes**. There is no refresh token — mint another when it expires.

    ## Your client must already hold a grant

    Credentials alone are not access. A **grant** is a record your reseller wrote that says
    *this client may act for this tenant, with at most these scopes*, optionally narrowed to one
    **customer** inside that tenant. If no active grant matches what you asked for, this
    endpoint answers **403** however good your credentials are.

    Grants are made out of band and never through this API. Ask the reseller whose platform you
    are integrating with for a client id, its secret, and the grant behind them.

    ## Two acts stand behind a customer-scoped credential

    A credential that acts for **one customer** of a reseller exists only after two separate
    acts by two different parties:

    1. the **reseller** turns API access on for that one customer and picks the scopes it may
       ever hold — its ceiling. This is the act that writes the grant.
    2. the **customer** then has its own credential created inside that ceiling.

    Neither act happens through this API, and together they are the whole answer to *why can my
    client mint a token for customer A but not for customer B?* — a grant exists for A and not
    for B.

    ## `customer` selects a context; by itself it narrows nothing

    Naming a customer **selects a grant somebody already wrote for it**. It never trims a wider
    grant down. A client holding only a tenant-wide grant cannot obtain a customer-scoped token
    by naming a customer, and a client granted customer A cannot reach customer B by asking. So
    there is no narrowing step you can forget: omit `customer` and you get the tenant-wide token
    your tenant-wide grant allows; name one and you get that customer's token, or a 403.

    That 403 reads the same for a tenant nobody granted you and for a customer nobody granted
    you. This is deliberate: a different message would let a caller discover which of a
    reseller's customers a client has been enabled for.

    ## Your scopes are an intersection, and a dropped scope is silent

    The scopes on the token are

    ```
    requested ∩ granted ∩ (customer named ? customer-scopeable : everything)
    ```

    **A scope outside that set is dropped, not refused.** You get a 200 carrying a token that
    simply does not hold it. That covers a scope your grant does not carry, a scope no customer
    credential may hold, **and a scope name this platform does not publish at all** — so a typo
    costs you a capability rather than an error.

    So **read `scopes` back off the response** and treat it as the authoritative answer. A call
    made on the assumption that you got what you asked for fails later at the resource instead,
    with a 403 that looks unrelated to this one.

    **`scopes` is optional and you almost always want it.** Leave it out and the intersection is
    empty: the request succeeds and hands you a token that carries no scopes and is refused by
    every resource you spend it on.

    ## Which scopes a customer-scoped token may hold

    Only scopes marked customer-scopeable survive that third intersection. Today they are
    `numbers:read` and `numbers:route`.

    **`numbers:assign` is not one of them and cannot be.** Assignment decides which customer a
    number belongs to, so it is never self-served by that customer's own credential; a token
    carrying it would be refused at every number it tried to assign. Ask for it on a
    customer-scoped token and it is dropped like any other unflagged scope:

    ```
    POST /v1/integration/token
    { \"client_id\": \"…\", \"client_secret\": \"…\", \"tenant\": \"…\", \"customer\": \"…\",
      \"scopes\": [\"numbers:read\", \"numbers:assign\", \"numbers:route\"] }

    200 OK
    { \"token_type\": \"Bearer\", \"expires_in\": 900,
      \"scopes\": [\"numbers:read\", \"numbers:route\"] }
    ```

    A tenant-wide credential is a different case: it may hold `numbers:assign`, and moving
    numbers between customers is exactly what it is for.

    ## Revocation, with its real clock

    Your grant is re-checked on **every** request you make with the token, not only when the
    token is minted. So a reseller who withdraws a grant, or a customer who revokes the
    credential, stops you on your next call rather than at the end of the token's 15 minutes.

    Reaching every region takes a moment: the answer is cached per region. In practice the cut
    lands well under a second, but **30 seconds** is the worst case to design against — never
    \"immediate\".

    Rotating a secret is not a revocation: it stops the old secret minting NEW tokens and leaves
    tokens already minted alive until they expire.

    Args:
        body (IntegrationTokenRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | IntegrationTokenResponse]
    """

    kwargs = _get_kwargs(
        body=body,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: IntegrationTokenRequest,
) -> ErrorDocument | IntegrationTokenResponse | None:
    r"""Exchange client credentials for a tenant- or customer-scoped token

     The token a machine client presents to the rest of this API. Send the client id and secret
    you were issued, name the **tenant** you are acting for, and you get back a token that
    carries that tenant — and, when you name one, a **customer** inside it.

    Which rows you reach is decided by the token, never by a header or a path you send later.
    That is why the tenant is named here and nowhere else: acting for another tenant means
    asking for another token, and one token is one context for its whole life.

    The token lasts **15 minutes**. There is no refresh token — mint another when it expires.

    ## Your client must already hold a grant

    Credentials alone are not access. A **grant** is a record your reseller wrote that says
    *this client may act for this tenant, with at most these scopes*, optionally narrowed to one
    **customer** inside that tenant. If no active grant matches what you asked for, this
    endpoint answers **403** however good your credentials are.

    Grants are made out of band and never through this API. Ask the reseller whose platform you
    are integrating with for a client id, its secret, and the grant behind them.

    ## Two acts stand behind a customer-scoped credential

    A credential that acts for **one customer** of a reseller exists only after two separate
    acts by two different parties:

    1. the **reseller** turns API access on for that one customer and picks the scopes it may
       ever hold — its ceiling. This is the act that writes the grant.
    2. the **customer** then has its own credential created inside that ceiling.

    Neither act happens through this API, and together they are the whole answer to *why can my
    client mint a token for customer A but not for customer B?* — a grant exists for A and not
    for B.

    ## `customer` selects a context; by itself it narrows nothing

    Naming a customer **selects a grant somebody already wrote for it**. It never trims a wider
    grant down. A client holding only a tenant-wide grant cannot obtain a customer-scoped token
    by naming a customer, and a client granted customer A cannot reach customer B by asking. So
    there is no narrowing step you can forget: omit `customer` and you get the tenant-wide token
    your tenant-wide grant allows; name one and you get that customer's token, or a 403.

    That 403 reads the same for a tenant nobody granted you and for a customer nobody granted
    you. This is deliberate: a different message would let a caller discover which of a
    reseller's customers a client has been enabled for.

    ## Your scopes are an intersection, and a dropped scope is silent

    The scopes on the token are

    ```
    requested ∩ granted ∩ (customer named ? customer-scopeable : everything)
    ```

    **A scope outside that set is dropped, not refused.** You get a 200 carrying a token that
    simply does not hold it. That covers a scope your grant does not carry, a scope no customer
    credential may hold, **and a scope name this platform does not publish at all** — so a typo
    costs you a capability rather than an error.

    So **read `scopes` back off the response** and treat it as the authoritative answer. A call
    made on the assumption that you got what you asked for fails later at the resource instead,
    with a 403 that looks unrelated to this one.

    **`scopes` is optional and you almost always want it.** Leave it out and the intersection is
    empty: the request succeeds and hands you a token that carries no scopes and is refused by
    every resource you spend it on.

    ## Which scopes a customer-scoped token may hold

    Only scopes marked customer-scopeable survive that third intersection. Today they are
    `numbers:read` and `numbers:route`.

    **`numbers:assign` is not one of them and cannot be.** Assignment decides which customer a
    number belongs to, so it is never self-served by that customer's own credential; a token
    carrying it would be refused at every number it tried to assign. Ask for it on a
    customer-scoped token and it is dropped like any other unflagged scope:

    ```
    POST /v1/integration/token
    { \"client_id\": \"…\", \"client_secret\": \"…\", \"tenant\": \"…\", \"customer\": \"…\",
      \"scopes\": [\"numbers:read\", \"numbers:assign\", \"numbers:route\"] }

    200 OK
    { \"token_type\": \"Bearer\", \"expires_in\": 900,
      \"scopes\": [\"numbers:read\", \"numbers:route\"] }
    ```

    A tenant-wide credential is a different case: it may hold `numbers:assign`, and moving
    numbers between customers is exactly what it is for.

    ## Revocation, with its real clock

    Your grant is re-checked on **every** request you make with the token, not only when the
    token is minted. So a reseller who withdraws a grant, or a customer who revokes the
    credential, stops you on your next call rather than at the end of the token's 15 minutes.

    Reaching every region takes a moment: the answer is cached per region. In practice the cut
    lands well under a second, but **30 seconds** is the worst case to design against — never
    \"immediate\".

    Rotating a secret is not a revocation: it stops the old secret minting NEW tokens and leaves
    tokens already minted alive until they expire.

    Args:
        body (IntegrationTokenRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | IntegrationTokenResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
        )
    ).parsed
