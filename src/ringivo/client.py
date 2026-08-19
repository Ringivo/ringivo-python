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
        scopes: The scopes to ask for. What the token carries is the
            intersection with what your grant allows, and a scope outside
            it is dropped rather than refused — so read the scopes back
            rather than assuming the request was honoured in full.
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

    def _request(
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
        """Send one request and hand back the response, or raise.

        Anything at or above 400 becomes a typed exception here, so no
        caller of this method has to check a status code — including the
        401 that has already been retried once by the auth flow.
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
