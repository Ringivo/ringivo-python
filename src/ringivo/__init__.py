"""Ringivo API client for Python.

    from ringivo import Ringivo

    with Ringivo(
        base_url="https://api.yourprovider.example",
        client_id="...",
        client_secret="...",
    ) as client:
        fax = client.faxes.send(
            fax_account="0198c4a1-3c4d-7e5f-9061-2b3c4d5e6f70",
            to="+13025556789",
            file=Path("chart-4471.pdf"),
        )

The base URL has no default and no hostname is compiled into this package:
your provider gives you theirs.

Webhook receivers want `ringivo.webhooks.verify()`, which needs no client
and no network.
"""

from . import webhooks
from ._version import __version__
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
