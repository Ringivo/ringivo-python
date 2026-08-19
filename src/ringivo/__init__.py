"""Ringivo API client for Python.

    from ringivo import Ringivo

    with Ringivo(
        base_url="https://api.yourprovider.example",
        client_id="...",
        client_secret="...",
        tenant="...",
        scopes=["fax:read", "fax:write"],
    ) as client:
        fax = client.faxes.send(
            fax_account="0198c4a1-3c4d-7e5f-9061-2b3c4d5e6f70",
            to="+13025556789",
            file=Path("chart-4471.pdf"),
        )

`AsyncRingivo` is the same client for callers on asyncio — the same
arguments, the same methods, awaited, and `async with` in place of `with`:

    from ringivo import AsyncRingivo

    async with AsyncRingivo(...) as client:
        fax = await client.faxes.get(fax_id)

The base URL has no default and no hostname is compiled into this package:
your provider gives you theirs. `scopes` has no default either, and an
empty one is refused: a token minted without scopes carries none, and every
route refuses it.

Webhook receivers want `ringivo.webhooks.verify()`, which needs no client
and no network — it is pure computation, so both clients share the one.
"""

from . import webhooks
from ._version import __version__
from .async_client import AsyncRingivo
from .async_faxes import AsyncFaxes
from .client import Ringivo
from .errors import (
    ApiError,
    ApiErrorDetail,
    AuthenticationError,
    RingivoError,
    SignatureVerificationError,
)
from .faxes import Faxes
from .models import Fax, FaxDocument, FaxPage, MediaLink

__all__ = [
    "ApiError",
    "ApiErrorDetail",
    "AsyncFaxes",
    "AsyncRingivo",
    "AuthenticationError",
    "Fax",
    "FaxDocument",
    "FaxPage",
    "Faxes",
    "MediaLink",
    "Ringivo",
    "RingivoError",
    "SignatureVerificationError",
    "__version__",
    "webhooks",
]
