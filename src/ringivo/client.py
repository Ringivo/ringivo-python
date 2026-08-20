"""The client a caller constructs, and the one connection everything shares.

`Ringivo` owns three things: the base URL (there is no default — see below),
one `httpx.Client` with the auth flow attached, and the resource namespaces
hung off it (`client.faxes`).

-- NO HOSTNAME IS COMPILED IN --------------------------------------------------
`base_url` is required and has no default. This package is grey-label: the
same wheel is installed by integrators of different providers, and a default
host would name one of them in every traceback, every log line and every
`--help`. tests/test_grey_label.py asserts the absence from the other side,
by reading the installed source.

-- WHY A CLIENT WITH NO SCOPES IS REFUSED AT CONSTRUCTION ----------------------
The token carries exactly the scopes it was asked for, intersected with what
the grant behind the credential allows. Ask for none and that intersection
is EMPTY: the mint answers 200, hands back a real token, and every route
then refuses it. So a client built without scopes has no working call in it —
not a narrower client, an inert one.

That failure is cheap here and expensive anywhere else. A `ValueError` on
the constructor line names the missing argument while the developer is
looking at it; the alternative is a 403 from a resource that has nothing
wrong with it, read as an access problem, hours or a deployment later. Same
reasoning as the empty-upload refusal in faxes.py: refuse what cannot work,
at the first moment it can be seen.

A single string is refused beside the empty one, because `scopes="fax:read"`
is the same failure wearing a type the checker accepts: a str is a
`Sequence[str]`, so it splits into eight one-character scopes that the
platform drops one by one, and the caller is handed the very token this
guard exists to refuse.

The SDK still names no scope of its own — WHICH scopes a credential may hold
is the platform's to decide and the grant's to answer. This only refuses the
questions that cannot have an answer.

-- ONE CLIENT, ONE AUTH FLOW ---------------------------------------------------
Every request goes through the same `httpx.Client`, so token caching, the
expiry margin and the single 401 retry apply once and apply everywhere
(see auth.py). Pre-signed media downloads are the deliberate exception: they
go through a second, UNAUTHENTICATED client.

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
from .auth import USER_AGENT, ClientCredentialsAuth
from .errors import raise_for_response
from .faxes import Faxes

__all__ = ["Ringivo"]

#: What the JSON:API resource endpoints send and accept.
JSONAPI_MEDIA_TYPE = "application/vnd.api+json"

#: What the four non-JSON:API endpoints send and accept — `POST /v1/faxes`,
#: the two media links, and `POST /v1/faxes/{fax}/cancel`.
JSON_MEDIA_TYPE = "application/json"


class Ringivo:
    """A connection to one provider's API, authenticated for its lifetime.

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

    Use it as a context manager, or call `close()`, so the underlying
    connections are released.
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
        # A str IS a `Sequence[str]`, to the type checker and to `tuple()`:
        # `scopes="fax:read"` type-checks, passes the emptiness check below,
        # and asks for eight one-character scopes the platform drops one by
        # one. That is the inert token this whole guard exists to refuse,
        # walking straight past it, so the shape is checked before the
        # content.
        if isinstance(scopes, str):
            raise ValueError(
                "scopes must be a list of scope names, not one string: a str is read "
                "one character at a time, so scopes=\"fax:read\" asks for eight scopes "
                "that do not exist and the platform silently drops every one. Pass "
                'scopes=["fax:read"].'
            )
        # Empty is not "the default" here — it is a token that carries no
        # scopes and is refused by every route (module docstring, above).
        if not scopes:
            raise ValueError(
                "scopes are required: a token minted without them carries no scopes "
                "at all, and every API route refuses it. Pass the scopes your "
                'integration was granted — the calls this client makes need '
                'scopes=["fax:read", "fax:write"].'
            )

        self._base_url = base_url.rstrip("/")
        self._auth = ClientCredentialsAuth(
            base_url=self._base_url,
            client_id=client_id,
            client_secret=client_secret,
            tenant=tenant,
            customer=customer,
            scopes=scopes,
            timeout=timeout,
        )
        self._http = httpx.Client(
            base_url=self._base_url,
            timeout=timeout,
            auth=self._auth,
            headers={"User-Agent": USER_AGENT, "Accept": JSONAPI_MEDIA_TYPE},
        )
        self._downloads = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )

        self.faxes = Faxes(self)

    @property
    def base_url(self) -> str:
        """The API root every request is built against."""
        return self._base_url

    def close(self) -> None:
        """Release the connections. Idempotent."""
        self._http.close()
        self._downloads.close()
        self._auth.close()

    def __enter__(self) -> Ringivo:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"<Ringivo base_url={self._base_url!r} version={__version__!r}>"

    def request(
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

        This is the ESCAPE HATCH, and it is public for that reason. This
        package wraps the fax surface; an endpoint it does not wrap is
        still reachable with your credential, your timeout, your
        User-Agent and the same typed errors:

            response = client.request("GET", "/v1/webhook-endpoints")
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

        response = self._http.request(
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

    def _download(self, url: str) -> bytes:
        """Follow a pre-signed URL and return the bytes behind it.

        Deliberately not through `self._http`: that client carries our
        bearer token. The URL is on the tenant's own API host, but it is a
        capability in its own right — one document, briefly — and attaching
        our credential to it would give whoever ends up holding the URL far
        more than the URL grants.
        """
        response = self._downloads.get(url)
        raise_for_response(response)
        return response.content


def _clean_params(params: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Drop unset query parameters, keeping `False` and `0`.

    `if not value` would drop `filter[read]=false` and `page[size]=0`,
    which mean something. Only None means "not asked for".
    """
    if not params:
        return None
    return {key: value for key, value in params.items() if value is not None}
