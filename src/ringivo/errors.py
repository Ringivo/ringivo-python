"""What this client raises, and what each exception carries.

Every failure a caller can act on is a typed exception with the machine-
readable part of the answer attached — the HTTP status and the API's own
error objects — so branching on a failure never means parsing a message
string. The message exists for a log line and a traceback, not for code.

The API answers errors as JSON:API error documents (`{"errors": [...]}`),
including on the four endpoints whose SUCCESS bodies are plain JSON. The
token endpoint is the one exception: it answers RFC 6749's flat
`{"error": ..., "error_description": ...}`, and both shapes are folded into
`ApiError` here so a caller has one thing to catch.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx

__all__ = [
    "ApiError",
    "ApiErrorDetail",
    "AuthenticationError",
    "RingivoError",
    "SignatureVerificationError",
]


class RingivoError(Exception):
    """Base class for everything this package raises deliberately.

    Catch this to catch the SDK. Transport-level failures — a connection
    refused, a TLS error, a timeout — are httpx's own exceptions and are
    deliberately not wrapped: re-labelling them would hide which layer
    failed while adding nothing a caller can branch on.
    """


@dataclass(frozen=True)
class ApiErrorDetail:
    """One JSON:API error object, as it arrived.

    `code` is the stable machine vocabulary to branch on — and it is
    genuinely optional: where no published code names the case, the status
    is the contract and `meta` carries the detail (a fax that cannot be
    cancelled is the documented example).
    """

    status: str | None = None
    title: str | None = None
    detail: str | None = None
    code: str | None = None
    source: Mapping[str, Any] | None = None
    meta: Mapping[str, Any] | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _from_json(cls, value: Mapping[str, Any]) -> ApiErrorDetail:
        def text(key: str) -> str | None:
            found = value.get(key)
            return found if isinstance(found, str) else None

        def mapping(key: str) -> Mapping[str, Any] | None:
            found = value.get(key)
            return found if isinstance(found, Mapping) else None

        return cls(
            status=text("status"),
            title=text("title"),
            detail=text("detail"),
            code=text("code"),
            source=mapping("source"),
            meta=mapping("meta"),
            raw=value,
        )


class ApiError(RingivoError):
    """The API answered, and the answer was a refusal."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        errors: tuple[ApiErrorDetail, ...] = (),
        body: bytes = b"",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.errors = errors
        self.body = body

    @property
    def code(self) -> str | None:
        """The first error's machine code, when the answer carried one."""
        return self.errors[0].code if self.errors else None


class AuthenticationError(ApiError):
    """The credential was refused, or the token it bought no longer works.

    Raised both for a token request the server rejected and for a request
    that answered 401 twice — once on its own, and once more after the
    token was force-refreshed and the request retried. A second 401 means
    the credential, not the token, is the problem.
    """


class SignatureVerificationError(RingivoError):
    """A webhook body did not prove it came from us, recently.

    One exception for every failure — a missing header, a malformed one, a
    stale timestamp, a wrong secret — because a receiver has exactly one
    useful reaction to all of them, and telling a stranger WHICH check
    their forgery failed is help they should not get.
    """


def _errors_from_response(response: httpx.Response) -> tuple[ApiErrorDetail, ...]:
    try:
        document = response.json()
    except ValueError:
        return ()

    if not isinstance(document, Mapping):
        return ()

    errors = document.get("errors")
    if isinstance(errors, list):
        return tuple(ApiErrorDetail._from_json(e) for e in errors if isinstance(e, Mapping))

    # RFC 6749's flat shape, from the token endpoint.
    oauth_error = document.get("error")
    if isinstance(oauth_error, str):
        description = document.get("error_description")
        return (
            ApiErrorDetail(
                status=str(response.status_code),
                title=oauth_error,
                detail=description if isinstance(description, str) else None,
                code=oauth_error,
                raw=document,
            ),
        )

    return ()


def _message(status_code: int, errors: tuple[ApiErrorDetail, ...], body: bytes) -> str:
    prefix = f"HTTP {status_code}"

    if errors:
        first = errors[0]
        said = " ".join(part for part in (first.title, first.detail) if part)
        coded = f" [{first.code}]" if first.code else ""
        more = f" (+{len(errors) - 1} more)" if len(errors) > 1 else ""
        return f"{prefix}{coded}: {said or 'the API refused the request'}{more}"

    excerpt = body[:200].decode("utf-8", "replace").strip()
    return f"{prefix}: {excerpt}" if excerpt else prefix


def raise_for_response(response: httpx.Response) -> None:
    """Raise the typed exception this response deserves, or return.

    One place decides, so every call in the package fails the same way —
    and so a 401 is an `AuthenticationError` whether it came from the token
    endpoint or from a resource that refused a token twice.
    """
    if response.status_code < 400:
        return

    body = response.content
    errors = _errors_from_response(response)
    message = _message(response.status_code, errors, body)
    failure = AuthenticationError if response.status_code == 401 else ApiError

    raise failure(message, status_code=response.status_code, errors=errors, body=body)
