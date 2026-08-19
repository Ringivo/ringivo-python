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

-- ONE CLIENT, ONE AUTH FLOW ---------------------------------------------------
Every request goes through the same `httpx.AsyncClient`, so token caching,
the expiry margin and the single 401 retry apply once and apply everywhere
(see async_auth.py). Pre-signed media downloads are the deliberate
exception: they go through a second, UNAUTHENTICATED client, because the
download URL points at an object store that is not us and must never
receive our bearer token.
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
        scopes: The scopes to ask for, or None to take your credential's
            default. A scope outside your client's ceiling is dropped by
            the server rather than refused, so read the scopes back rather
            than assuming the request was honoured in full.
        timeout: Seconds any single request may take, token requests
            included.

    Use it as an async context manager, or await `aclose()`, so the
    underlying connections are released.
    """

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        *,
        scopes: Sequence[str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        if not client_id or not client_secret:
            raise ValueError("client_id and client_secret are required")

        self._base_url = base_url.rstrip("/")
        self._auth = AsyncClientCredentialsAuth(
            base_url=self._base_url,
            client_id=client_id,
            client_secret=client_secret,
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

    async def _request(
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

    async def _download(self, url: str) -> bytes:
        """Follow a pre-signed URL and return the bytes behind it.

        Deliberately not through `self._http`: that client carries our
        bearer token, and this URL is somebody else's host.
        """
        response = await self._downloads.get(url)
        raise_for_response(response)
        return response.content
