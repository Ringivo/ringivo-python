"""The integration token, minted and kept good so a caller never sees it.

A caller hands over a client id, a secret and the selectors naming what they
act for, once, at construction. Everything after that — minting the token,
caching it, replacing it before it expires, and replacing it again when the
server says it is no longer good — happens here, on the way out of every
request.

-- WHERE THE TOKEN COMES FROM --------------------------------------------------
`POST {base_url}/oauth/token`, one JSON body, no `Authorization` header: the
credential and the selectors travel in the body, and the answer is the bearer
every other request carries. That endpoint is the mint for the `/v1` API, and
it is the only one — a token bought anywhere else is refused by every route
this client calls.

`grant_type` is `client_credentials`, and it is REQUIRED rather than a
formality. It is the member that tells the endpoint which exchange this is,
and the endpoint reads the selectors below only when it is present: a body
without it is answered as some other kind of request entirely.

Up to 0.2.x this client minted at `POST /v1/integration/token`, a second
door onto the same grants; 0.3.0 moved here while that one was still served.
The platform has now DELETED it rather than deprecating it any further, so a
release of this package pinned to 0.2.x does not work against the platform
at all. There is one mint, and this is it.

-- WHY THE SCOPES ARE ONE STRING AND NOT AN ARRAY ------------------------------
`scope`, spelled RFC 6749's way: one string of names separated by spaces. The
array member `scopes` that the deleted mint read is NOT read here, and a body
carrying only it asks for nothing at all — which the mint REFUSES, 400
`invalid_scope`, rather than handing back a token that authorises nothing.

The array is not sent alongside the string as a hedge. A member the endpoint
ignores costs the next reader a lookup to discover it does nothing, and two
spellings of one question is exactly how the two drift apart.

-- WHY `tenant` IS ALWAYS SENT AND `customer` ONLY WHEN SET --------------------
`tenant` and `customer` NAME a grant somebody already wrote for this
credential; neither narrows a wider grant down.

`tenant` is REQUIRED, so it is on every body this module builds and no
caller can leave it off. The mint used to resolve an absent `tenant` to the
single active grant behind the credential, and that inference is gone:
omitting it is a 400 `invalid_request`, and so is sending it empty, which
RFC 6749 section 3.2 reads as not sending it. The reason is worth keeping in
mind here rather than only in a changelog — a client with one grant worked
without naming a tenant, and the day its reseller granted it a second one
the integration broke, on a day nobody had touched the code. An explicit
tenant cannot rot that way.

`customer` is the one selector that may be unset, and an unset one is left
out of the body altogether rather than sent as null. The two spellings mean
the same thing — the platform documents an omitted `customer` and a null one
as the same tenant-wide request — so this is a free choice, and one way of
saying nothing beats two.

-- THE SECRET TRAVELS EXACTLY ONE WAY ------------------------------------------
In the body, and never in an `Authorization: Basic` header beside it. The
mint reads either spelling and REFUSES both at once — 400 `invalid_request`,
RFC 6749 section 2.3 — because with two credentials on one request the body
wins silently and nothing on the wire says which one was checked. So the
mint below sends no `Authorization` header at all, which is the same rule
read from the other side.

-- WHY THIS IS AN httpx.Auth AND NOT A WRAPPER METHOD --------------------------
`httpx.Auth` is a request/response GENERATOR: it may look at the response and
yield a second request. That is exactly the shape of "retry once on 401 with a
fresh token", and putting it here means EVERY SYNC request through the shared
client gets it — including the ones a caller sends themselves through
`Ringivo.request`, the public escape hatch, which is the same code path as
`client.faxes` and needs no token handling of its own.

The ASYNC half of that promise is not kept, and is refused rather than
half-kept: see `async_auth_flow`, which raises. Inheriting httpx's default
there sent requests with no `Authorization` header at all.

-- WHY THE EXPIRY MARGIN -------------------------------------------------------
The cached token is replaced `expires_in - 60` seconds after it was minted,
not `expires_in`. Without the margin a token that expires mid-flight is
discovered by the SERVER, which costs a refused request and a retry; with it
the replacement happens before a request ever carries the dying token. The
401 retry stays anyway — a token can also be revoked, or a server restarted,
long before its clock runs out.

-- WHY THE FAILED TOKEN IS PASSED BACK -----------------------------------------
A 401 is normally seen by every request in flight at once, not by one.
Each of them asks for a replacement and they queue on the lock — and a
force-refresh that minted unconditionally gave each one its own token,
throwing the one in front away. Ten in-flight requests meant ten mints for
one dead token, which is how a client that is behaving correctly walks
into the token endpoint's rate limit.

So a caller says WHICH token failed: `access_token(force_refresh=True,
stale=…)`. Under the lock, a caller whose stale token has already been
replaced takes the replacement instead of buying its own. One dead token
costs one mint.

-- WHY A MONOTONIC CLOCK -------------------------------------------------------
Expiry is measured with `time.monotonic()`, which cannot be moved by an NTP
correction or a daylight-saving jump. Wall-clock arithmetic would treat a
one-hour clock step as an hour of elapsed token life.
"""

from __future__ import annotations

import threading
import time
from collections.abc import AsyncGenerator, Generator, Sequence

import httpx

from ._version import __version__
from .errors import AuthenticationError, raise_for_response

__all__ = ["USER_AGENT", "ClientCredentialsAuth"]

USER_AGENT = f"Ringivo/Python {__version__}"

# How long before a token's stated expiry it is treated as spent.
EXPIRY_MARGIN_SECONDS = 60

# Module-level alias so tests can drive the clock without patching `time`
# itself, which every other library in the process is also reading.
_monotonic = time.monotonic

# The one path that issues tokens the /v1 API accepts.
TOKEN_PATH = "/oauth/token"

# The exchange this client performs, and the member that names it. A mint
# without it is not read as a credential exchange at all.
GRANT_TYPE = "client_credentials"


def _token_request_body(
    *,
    client_id: str,
    client_secret: str,
    tenant: str,
    customer: str | None,
    scopes: tuple[str, ...] | None,
) -> dict[str, object]:
    """The JSON the mint reads, with every unset OPTIONAL member ABSENT.

    Shared by the sync and async auth, which share no other machinery: the
    lifecycle around this differs down to the lock, but the body does not,
    and a body that diverged between the two clients would send one of them
    to the wrong context with nothing to show for it.

    `grant_type` and `tenant` are not optional and are on every body this
    builds: the first names the exchange, the second names the grant, and
    the mint refuses a request missing either.

    `scope` is one space-delimited string, which is the only spelling this
    endpoint reads — see the module docstring for why the array is not sent
    with it.
    """
    body: dict[str, object] = {
        "grant_type": GRANT_TYPE,
        "client_id": client_id,
        "client_secret": client_secret,
        "tenant": tenant,
    }
    if customer is not None:
        body["customer"] = customer
    if scopes:
        body["scope"] = " ".join(scopes)
    return body


class ClientCredentialsAuth(httpx.Auth):
    """Signs requests with a bearer token, and keeps that token good."""

    def __init__(
        self,
        *,
        base_url: str,
        client_id: str,
        client_secret: str,
        tenant: str,
        customer: str | None = None,
        scopes: Sequence[str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._token_url = f"{base_url.rstrip('/')}{TOKEN_PATH}"
        self._client_id = client_id
        self._client_secret = client_secret
        self._tenant = tenant
        self._customer = customer
        self._scopes = tuple(scopes) if scopes is not None else None
        self._lock = threading.Lock()
        self._access_token: str | None = None
        self._expires_at: float | None = None
        # Its own client: the token request is unauthenticated, so it must not
        # travel through the client this object is the `auth` of.
        self._http = httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT})

    def sync_auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response]:
        sent = self.access_token()
        request.headers["Authorization"] = f"Bearer {sent}"
        response = yield request

        if response.status_code != 401:
            return

        # ONCE. A second 401 is answered by the caller's exception, not by
        # another mint: a credential that has lost its reach would otherwise
        # spin, and every attempt costs the server a token.
        #
        # `stale=sent` names the token that was refused, so a thread that
        # queued behind another thread's refresh takes ITS replacement
        # rather than buying a second one.
        replacement = self.access_token(force_refresh=True, stale=sent)
        request.headers["Authorization"] = f"Bearer {replacement}"
        yield request

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        """Refuse, loudly, rather than send the request unauthenticated.

        THIS OVERRIDE EXISTS BECAUSE ITS ABSENCE WAS A SILENT FAILURE, shipped
        in 0.1.0. httpx's base `async_auth_flow` defers to `auth_flow`, whose
        default body is a single line — `yield request` — a PASS-THROUGH. So
        an `httpx.AsyncClient(auth=…)` holding this object sent the request
        verbatim: no token minted, no `Authorization` header, no error. The
        server answers 401, and the caller reads that as their credential
        being wrong. A refusal that names the cause costs them a minute; the
        pass-through cost them an afternoon.

        Not implemented rather than made to work, because the token mint below
        is blocking I/O behind a `threading.Lock`, and an async flow needs its
        own client and its own lock to be honest. This auth is sync-only.

        The unreachable `yield` is load-bearing: without it this is a
        coroutine rather than an async generator, and httpx would fail on
        `.__anext__()` with an `AttributeError` naming nothing useful.
        """
        raise NotImplementedError(
            "ringivo's authentication is sync-only, and an async client would "
            "otherwise send this request with NO Authorization header. Use the sync "
            "ringivo.Ringivo client, or mint a token yourself and set the header on your "
            "own async requests."
        )
        yield request  # pragma: no cover - unreachable; makes this an async generator

    def access_token(self, *, force_refresh: bool = False, stale: str | None = None) -> str:
        """The token to send, minting or replacing it if that is what it takes.

        Args:
            force_refresh: Replace the cached token even though it still
                looks fresh — what a 401 asks for.
            stale: The token that was refused, when a caller knows. Callers
                that see the same 401 queue here, and without this each one
                mints a replacement for a token the caller in front has
                already replaced. Given it, a caller holding a stale token
                that is no longer the cached one takes the cached one and
                mints nothing. Omitting it keeps the old unconditional
                behaviour, which is right when there is no failed token to
                name.
        """
        with self._lock:
            cached = self._access_token
            if force_refresh:
                if stale is not None and cached is not None and cached != stale:
                    return cached
                return self._mint()
            if cached is None or not self._is_fresh():
                return self._mint()
            return cached

    def close(self) -> None:
        self._http.close()

    def _is_fresh(self) -> bool:
        if self._access_token is None:
            return False
        if self._expires_at is None:
            # The server did not say when it expires, so there is nothing to
            # pre-empt. The 401 retry is what replaces this one.
            return True
        return _monotonic() < self._expires_at

    def _mint(self) -> str:
        body = _token_request_body(
            client_id=self._client_id,
            client_secret=self._client_secret,
            tenant=self._tenant,
            customer=self._customer,
            scopes=self._scopes,
        )

        response = self._http.post(self._token_url, json=body)
        raise_for_response(response)

        payload = response.json()
        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token:
            raise AuthenticationError(
                "HTTP 200 [invalid_token_response]: the token endpoint answered success "
                "with no access_token",
                status_code=response.status_code,
                body=response.content,
            )

        expires_in = payload.get("expires_in")
        self._access_token = token
        self._expires_at = (
            _monotonic() + max(int(expires_in) - EXPIRY_MARGIN_SECONDS, 0)
            if isinstance(expires_in, (int, float)) and not isinstance(expires_in, bool)
            else None
        )
        return token
