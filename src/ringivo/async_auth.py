"""The same integration token, for a caller on asyncio.

This is the deliberate TWIN of auth.py and not a layer over it. The token
lifecycle is identical — mint once, keep it until a minute before it
expires, replace it once when the server refuses one — but none of the
machinery can be shared: `httpx.AsyncClient` drives `async_auth_flow` and
needs an awaitable mint behind an `asyncio.Lock`, while `httpx.Client`
drives `sync_auth_flow` and needs a blocking one behind a
`threading.Lock`. Bridging the two would put blocking I/O on the event
loop, which is the failure auth.py already refuses out loud.

-- READ auth.py FIRST ----------------------------------------------------------
Every "why" behind this file is written out there and is NOT repeated
here: why an `httpx.Auth` rather than a wrapper method, why the mint is
`POST /v1/integration/token` with the credential in the body, why an
unset selector is left out of that body altogether, why the token is
replaced `expires_in - 60` seconds in, and why expiry is measured on a
monotonic clock. What follows is only what is different.

-- THE BODY IS THE ONE THING SHARED --------------------------------------------
`_token_request_body` is imported rather than written twice. The
lifecycle around it differs down to the lock, but the request does not,
and a body that drifted between the two clients would send one of them to
a context its caller never asked for.

-- THE GUARD POINTS THE OTHER WAY ----------------------------------------------
auth.py's `async_auth_flow` refuses an async client. This file's
`sync_auth_flow` refuses a SYNC one, for the same reason and against the
same trap: httpx's default flow is a pass-through, so the wrong pairing
sends the request with no `Authorization` header and no error at all.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator, Generator, Sequence

import httpx

from .auth import EXPIRY_MARGIN_SECONDS, TOKEN_PATH, USER_AGENT, _token_request_body
from .errors import AuthenticationError, raise_for_response

__all__ = ["AsyncClientCredentialsAuth"]

# This module's OWN clock seam, so a test can drive the async client's
# expiry without moving the sync client's. auth.py carries the same alias:
# the two are twins, so patching one does not patch the other.
_monotonic = time.monotonic


class AsyncClientCredentialsAuth(httpx.Auth):
    """Signs requests with a bearer token, and keeps that token good."""

    def __init__(
        self,
        *,
        base_url: str,
        client_id: str,
        client_secret: str,
        tenant: str | None = None,
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
        # Constructed here rather than on first use: since 3.10 an
        # `asyncio.Lock` binds to a loop lazily, on the first `await`, so
        # building one outside a running loop is safe and the client stays
        # constructible from ordinary synchronous code.
        self._lock = asyncio.Lock()
        self._access_token: str | None = None
        self._expires_at: float | None = None
        # Its own client: the token request is unauthenticated, so it must not
        # travel through the client this object is the `auth` of.
        self._http = httpx.AsyncClient(timeout=timeout, headers={"User-Agent": USER_AGENT})

    def sync_auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response]:
        """Refuse, loudly, rather than send the request unauthenticated.

        The mirror of auth.py's `async_auth_flow`, pointing the other way.
        `httpx.Auth.sync_auth_flow` defers to `auth_flow`, whose default
        body is a single line — `yield request` — a PASS-THROUGH. So an
        `httpx.Client` holding THIS object would send the request verbatim:
        no token minted, no `Authorization` header, no error. The server
        answers 401 and the caller reads that as their credential being
        wrong.

        Not made to work, because the mint below is awaited: driving it
        from a sync flow means running an event loop inside somebody
        else's call stack, and there is already a sync client that does
        this properly.

        The unreachable `yield` is NOT load-bearing in this direction —
        httpx calls `sync_auth_flow(request)` and then `next(...)`, so a
        plain function that raises surfaces the same exception before any
        request is built (verified both ways against httpx 0.28.1). It is
        kept so the declared `Generator` return type is honest, and so
        this guard reads as the mirror of the one in auth.py, where the
        yield IS required.
        """
        raise NotImplementedError(
            "ringivo's AsyncRingivo authentication is async-only, and a sync httpx.Client "
            "would otherwise send this request with NO Authorization header. Use the sync "
            "ringivo.Ringivo client, or mint a token yourself and set the header on your "
            "own sync requests."
        )
        yield request  # pragma: no cover - unreachable; makes this a generator

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        sent = await self.access_token()
        request.headers["Authorization"] = f"Bearer {sent}"
        response = yield request

        if response.status_code != 401:
            return

        # ONCE. A second 401 is answered by the caller's exception, not by
        # another mint: a credential that has lost its reach would otherwise
        # spin, and every attempt costs the server a token.
        #
        # `stale=sent` names the token that was refused, so a task that
        # queued behind another task's refresh takes ITS replacement rather
        # than buying a second one. This matters more here than in the sync
        # client: concurrency is the reason to reach for this one, so a
        # gather of in-flight requests all meeting the same 401 is the
        # normal case rather than the unlucky one.
        replacement = await self.access_token(force_refresh=True, stale=sent)
        request.headers["Authorization"] = f"Bearer {replacement}"
        yield request

    async def access_token(self, *, force_refresh: bool = False, stale: str | None = None) -> str:
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
        async with self._lock:
            cached = self._access_token
            if force_refresh:
                if stale is not None and cached is not None and cached != stale:
                    return cached
                return await self._mint()
            if cached is None or not self._is_fresh():
                return await self._mint()
            return cached

    async def aclose(self) -> None:
        await self._http.aclose()

    def _is_fresh(self) -> bool:
        if self._access_token is None:
            return False
        if self._expires_at is None:
            # The server did not say when it expires, so there is nothing to
            # pre-empt. The 401 retry is what replaces this one.
            return True
        return _monotonic() < self._expires_at

    async def _mint(self) -> str:
        body = _token_request_body(
            client_id=self._client_id,
            client_secret=self._client_secret,
            tenant=self._tenant,
            customer=self._customer,
            scopes=self._scopes,
        )

        response = await self._http.post(self._token_url, json=body)
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
