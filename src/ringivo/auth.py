"""The OAuth 2.0 client-credentials grant, held so a caller never sees it.

A caller hands over a client id and secret once, at construction. Everything
after that — minting the token, caching it, replacing it before it expires,
and replacing it again when the server says it is no longer good — happens
here, on the way out of every request.

-- WHY THIS IS AN httpx.Auth AND NOT A WRAPPER METHOD --------------------------
`httpx.Auth` is a request/response GENERATOR: it may look at the response and
yield a second request. That is exactly the shape of "retry once on 401 with a
fresh token", and putting it here means EVERY SYNC request through the shared
client gets it — including any a caller makes through the vendored generated
client, which knows nothing about tokens.

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


class ClientCredentialsAuth(httpx.Auth):
    """Signs requests with a bearer token, and keeps that token good."""

    def __init__(
        self,
        *,
        base_url: str,
        client_id: str,
        client_secret: str,
        scopes: Sequence[str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._token_url = f"{base_url.rstrip('/')}/oauth/token"
        self._client_id = client_id
        self._client_secret = client_secret
        self._scopes = tuple(scopes) if scopes is not None else None
        self._lock = threading.Lock()
        self._access_token: str | None = None
        self._expires_at: float | None = None
        # Its own client: the token request is unauthenticated, so it must not
        # travel through the client this object is the `auth` of.
        self._http = httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT})

    def sync_auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response]:
        request.headers["Authorization"] = f"Bearer {self.access_token()}"
        response = yield request

        if response.status_code != 401:
            return

        # ONCE. A second 401 is answered by the caller's exception, not by
        # another mint: a credential that has lost its reach would otherwise
        # spin, and every attempt costs the server a token.
        request.headers["Authorization"] = f"Bearer {self.access_token(force_refresh=True)}"
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
        own client and its own lock to be honest. 0.1.x is sync-only.

        The unreachable `yield` is load-bearing: without it this is a
        coroutine rather than an async generator, and httpx would fail on
        `.__anext__()` with an `AttributeError` naming nothing useful.
        """
        raise NotImplementedError(
            "ringivo's authentication is sync-only in 0.1.x, and an async client would "
            "otherwise send this request with NO Authorization header. Use the sync "
            "ringivo.Ringivo client, or mint a token yourself and set the header on your "
            "own async requests."
        )
        yield request  # pragma: no cover - unreachable; makes this an async generator

    def access_token(self, *, force_refresh: bool = False) -> str:
        """The token to send, minting or replacing it if that is what it takes."""
        with self._lock:
            cached = self._access_token
            if force_refresh or cached is None or not self._is_fresh():
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
        form = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        if self._scopes:
            form["scope"] = " ".join(self._scopes)

        response = self._http.post(self._token_url, data=form)
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
