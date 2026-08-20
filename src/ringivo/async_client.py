"""The same client for callers on asyncio, and the connections it owns.

`AsyncRingivo` is a SIBLING of `Ringivo`, not a wrapper around it and not
a subclass of a shared core. The two hold the same three things — the base
URL, one authenticated client, and the resource namespaces hung off it —
against transports that share no code: `httpx.AsyncClient` and
`httpx.Client` are separate implementations, and every method here differs
from its twin by an `await` and nothing else. At this size two obvious
files beat one clever one.

-- NO HOSTNAME IS COMPILED IN HERE EITHER --------------------------------------
`base_url` is required and has no default, for the reason client.py sets
out: this package is grey-label, and a default host would name one
provider in every traceback of another's. tests/test_grey_label.py reads
the installed source and asserts the absence from the other side.

-- AND NO SCOPES IS REFUSED HERE TOO -------------------------------------------
An empty `scopes` — or a single string, which splits into one-character
scopes — is a `ValueError` on this constructor for the reason client.py
sets out in full: the token would carry no scopes, every route would
refuse it, and the client would have no working call in it. The refusal is
written twice because the constructors are twins, not one.

-- ONE CLIENT, ONE AUTH FLOW ---------------------------------------------------
Every request goes through the same `httpx.AsyncClient`, so token caching,
the expiry margin and the single 401 retry apply once and apply everywhere
(see async_auth.py). Pre-signed media downloads are the deliberate
exception: they go through a second, UNAUTHENTICATED client.

The URL is on the tenant's own API host — media is served through their
branded proxy, so it is not somebody else's server — and it is STILL
fetched with no `Authorization` header. A pre-signed URL is already a
capability: it reads ONE document, briefly, and it is the kind of string
that ends up in a browser bar, a ticket or an access log. The bearer token
reads every fax this client can reach, and must never travel attached to
it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import TracebackType
from typing import Any

import httpx

from ._version import __version__
from .async_auth import AsyncClientCredentialsAuth
from .async_faxes import AsyncFaxes
from .auth import USER_AGENT
from .client import JSONAPI_MEDIA_TYPE, _clean_params
from .errors import raise_for_response

__all__ = ["AsyncRingivo"]


class AsyncRingivo:
    """A connection to one provider's API, authenticated for its lifetime.

    The same constructor as `Ringivo`, and the same arguments mean the same
    things:

    Args:
        base_url: The API root you were given, without a trailing slash —
            `https://api.yourprovider.example`. Required: this package
            names no host of its own.
        client_id: The client id issued with your credential.
        client_secret: Its secret.
        tenant: The provider you are acting for. Pass it: today the token
            request needs one, and your credential must already hold a
            grant for that tenant or the platform refuses it. Leave it out
            only where the platform picks the single grant behind your
            credential for you.
        customer: One customer inside that tenant, when your grant names
            one. It SELECTS a context somebody already granted you and
            narrows nothing by itself, so leave it out for the
            tenant-wide token your grant allows.
        scopes: The scopes to ask for, as a list of names. REQUIRED, though
            it is spelled as a keyword: a token minted with no scopes
            carries none and is refused by every route, so an empty list —
            or one bare string, which splits into one-character scopes — is
            a `ValueError` here rather than a puzzle in production.
            `fax:read` and `fax:write`
            are what this client's own calls need. What the token ends up
            carrying is the intersection with what your grant allows, and
            a scope outside that is dropped rather than refused, so an
            over-broad request fails later at the resource rather than
            here.
        timeout: Seconds any single request may take, token requests
            included.

    The token itself never reaches you: it is bought on the first call,
    lives about a quarter of an hour, and is re-minted transparently before
    it expires and again if the platform ever refuses one.

    Use it as an async context manager, or await `aclose()`, so the
    underlying connections are released.
    """

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        *,
        tenant: str | None = None,
        customer: str | None = None,
        scopes: Sequence[str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        if not client_id or not client_secret:
            raise ValueError("client_id and client_secret are required")
        # A str IS a `Sequence[str]`, so `scopes="fax:read"` type-checks and
        # asks for eight one-character scopes — the inert token this guard
        # exists to refuse, walking past it. Shape before content, as in
        # client.py.
        if isinstance(scopes, str):
            raise ValueError(
                "scopes must be a list of scope names, not one string: a str is read "
                "one character at a time, so scopes=\"fax:read\" asks for eight scopes "
                "that do not exist and the platform silently drops every one. Pass "
                'scopes=["fax:read"].'
            )
        # Empty is not "the default" here — it is a token that carries no
        # scopes and is refused by every route (client.py's docstring).
        if not scopes:
            raise ValueError(
                "scopes are required: a token minted without them carries no scopes "
                "at all, and every API route refuses it. Pass the scopes your "
                'integration was granted — the calls this client makes need '
                'scopes=["fax:read", "fax:write"].'
            )

        self._base_url = base_url.rstrip("/")
        self._auth = AsyncClientCredentialsAuth(
            base_url=self._base_url,
            client_id=client_id,
            client_secret=client_secret,
            tenant=tenant,
            customer=customer,
            scopes=scopes,
            timeout=timeout,
        )
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            auth=self._auth,
            headers={"User-Agent": USER_AGENT, "Accept": JSONAPI_MEDIA_TYPE},
        )
        self._downloads = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )

        self.faxes = AsyncFaxes(self)

    @property
    def base_url(self) -> str:
        """The API root every request is built against."""
        return self._base_url

    async def aclose(self) -> None:
        """Release the connections. Idempotent."""
        await self._http.aclose()
        await self._downloads.aclose()
        await self._auth.aclose()

    async def __aenter__(self) -> AsyncRingivo:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    def __repr__(self) -> str:
        return f"<AsyncRingivo base_url={self._base_url!r} version={__version__!r}>"

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        accept: str = JSONAPI_MEDIA_TYPE,
        headers: Mapping[str, str] | None = None,
        json: Any = None,
        data: Mapping[str, Any] | None = None,
        files: Sequence[tuple[str, Any]] | None = None,
    ) -> httpx.Response:
        """Send one authenticated request and hand back the response, or raise.

        The awaited twin of `Ringivo.request`, and the same ESCAPE HATCH:
        this package wraps the fax surface, and an endpoint it does not
        wrap is still reachable with your credential, your timeout, your
        User-Agent and the same typed errors:

            response = await client.request("GET", "/v1/webhook-endpoints")
            endpoints = response.json()["data"]

        `spec/openapi.yaml` in this package's repository is the reference
        for what those endpoints take and answer, and
        `ringivo._generated_types` carries the same shapes as `TypedDict`s
        for a type checker to read.

        WHAT IT CARRIES: the bearer token — bought, cached and re-minted
        for you — one retry against a 401, the base URL, the timeout, the
        User-Agent, and `raise_for_response`, so anything at or above 400
        arrives as `ApiError` (or `AuthenticationError` for a 401 the
        retry did not fix) rather than a status code you must remember to
        check.

        WHAT IT DOES NOT CARRY: any promise about what comes back. You get
        an `httpx.Response`, because you are past this package's boundary:
        the JSON behind it is the API's own — not parsed, not snake_cased,
        not one of the frozen objects in models.py, and not held still by
        this package's version number. The wrapped methods on
        `client.faxes` are where those guarantees live.

        Args:
            method: The HTTP method, uppercase — `"GET"`, `"POST"`.
            path: The path under the base URL, leading slash included.
            params: Query parameters. A `None` value is left off rather
                than sent empty, while `False` and `0` are sent.
            accept: The `Accept` header. JSON:API resource routes want the
                default; the plain-JSON routes want `"application/json"`.
            headers: Anything else to send, merged over `accept`.
            json: A body to send as JSON.
            data: Form fields, for a multipart send.
            files: File parts, for a multipart send.

        Raises:
            AuthenticationError: The credential was refused, and it had
                already been re-minted and retried once.
            ApiError: Any other response at or above 400.
        """
        sent_headers = {"Accept": accept}
        if headers:
            sent_headers.update(headers)

        response = await self._http.request(
            method,
            path,
            params=_clean_params(params),
            headers=sent_headers,
            json=json,
            data=dict(data) if data else None,
            files=list(files) if files else None,
        )
        raise_for_response(response)
        return response

    # The name this method had while it was private, kept pointing at the
    # same object. Before 0.2.2 there was no public escape hatch, so a
    # caller who needed an unwrapped endpoint had nothing else to reach
    # for; renaming without leaving this behind would break exactly the
    # people the public name is meant to serve.
    _request = request

    async def _download(self, url: str) -> bytes:
        """Follow a pre-signed URL and return the bytes behind it.

        Deliberately not through `self._http`: that client carries our
        bearer token. The URL is on the tenant's own API host, but it is a
        capability in its own right — one document, briefly — and attaching
        our credential to it would give whoever ends up holding the URL far
        more than the URL grants.
        """
        response = await self._downloads.get(url)
        raise_for_response(response)
        return response.content
