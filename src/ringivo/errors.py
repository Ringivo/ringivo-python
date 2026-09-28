"""What this client raises, and what each exception carries.

Every failure a caller can act on is a typed exception with the machine-
readable part of the answer attached — the HTTP status and the API's own
error objects — so branching on a failure never means parsing a message
string. The message exists for a log line and a traceback, not for code.

-- TWO ERROR VOCABULARIES MEET HERE --------------------------------------------
The boundary between them runs between the MINT and everything else.

The `/v1` resource surface answers JSON:API error documents
(`{"errors": [...]}`). The token mint — `POST /oauth/token` — answers RFC
6749's flat `{"error": ..., "error_description": ...}` instead, because that
is what an OAuth token endpoint owes its callers. Both fold into `ApiError`,
so a caller still has ONE class to catch and one place to read a machine code
off, whichever door refused them.

WHICH SHAPE ARRIVED IS DECIDED BY WHAT THE BODY CARRIES, never by which URL
was called. The two are disjoint — a JSON:API document has no top-level
`error` member, and an OAuth refusal has no `errors` array — so one parser
reads both without being told where it is. That matters more than the line it
saves: the alternative threads the caller's URL down into the error layer, and
then a surface that changes vocabulary is MIS-read rather than followed.

Unknown members are ignored rather than refused, and the whole document is
kept on `raw`, so a member either surface adds later reaches a caller without
a new release.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

__all__ = [
    "ApiError",
    "ApiErrorDetail",
    "AuthenticationError",
    "RecordingAudioMissingError",
    "RingivoError",
    "SignatureVerificationError",
    "TranscriptRequestLimitedError",
    "TranscriptionCappedError",
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
    """One refusal, as it arrived — a JSON:API error object, or an OAuth one.

    `code` is the stable machine vocabulary to branch on — and it is
    genuinely optional: where no published code names the case, the status
    is the contract and `meta` carries the detail (a fax that cannot be
    cancelled is the documented example).

    A MINT refusal is folded into one of these too, and fills a narrower set
    of fields: `code` is RFC 6749's `error` (`invalid_client`,
    `unauthorized_client`, `invalid_request`, `invalid_scope`,
    `unsupported_grant_type`), `detail` is its `error_description`, `status`
    is the HTTP status as a string, and `raw` is the whole document.
    `title`, `source` and `meta` stay None — that vocabulary has no member
    for them, and inventing one would make an absent fact look like a
    reported one.

    READ `code`, NOT THE STATUS, on a mint refusal. RFC 6749 section 5.2
    gives the token endpoint one status for every error but a bad
    credential, so all but `invalid_client` arrive as 400 and the status
    separates none of them. `raw` matters for the same reason: the mint
    sends a `hint` on some refusals and not others, and it is the only
    thing telling the two `invalid_scope` causes apart.
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
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.errors = errors
        self.body = body
        #: How many seconds the server asked you to wait, when it asked.
        #:
        #: This is `Retry-After` (RFC 9110 section 10.2.3), given to you as
        #: SECONDS whichever of the header's two legal forms arrived — a
        #: count, or an absolute date converted for you. None means the
        #: server said nothing, or said something malformed: use your own
        #: backoff. It is never a number invented here, because a caller
        #: would read that as the server's instruction.
        self.retry_after = retry_after

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


class RecordingAudioMissingError(ApiError):
    """A 409 `recording_audio_missing`: there is no audio for this capture.

    Raised by `pbx.call_records.request_transcript()`. The platform holds no
    audio for the capture, so it cannot be transcribed. Asking again does not
    help.
    """


class TranscriptionCappedError(ApiError):
    """A 429 `transcription_capped`: the daily transcription budget is spent.

    Raised by `pbx.call_records.request_transcript()`. `retry_after` gives
    the seconds until the budget resets at 00:00 UTC. Nothing was started.
    """


class TranscriptRequestLimitedError(ApiError):
    """A 429 `transcript_request_limited`: this call was asked about too often.

    Raised by `pbx.call_records.request_transcript()`. The limit counts asks
    per CALL, across all of its captures (3 a day by default). `retry_after`
    gives the seconds until one more ask is accepted. Nothing was started.
    """


#: The refusals that get a class of their own, by the API's `code`. The code
#: is the stable vocabulary, so it decides — not the status alone, which a
#: 429 shares with the plain rate limiter.
_BY_CODE: Mapping[str, type[ApiError]] = {
    "recording_audio_missing": RecordingAudioMissingError,
    "transcription_capped": TranscriptionCappedError,
    "transcript_request_limited": TranscriptRequestLimitedError,
}


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

    # RFC 6749's flat shape — what the token mint answers. `error` is the
    # machine vocabulary (`invalid_client`, `unauthorized_client`,
    # `invalid_request`, `invalid_scope`, `unsupported_grant_type`),
    # `error_description` the sentence for a human.
    #
    # `title` is deliberately LEFT UNSET rather than filled with the error
    # name: `code` already carries it, and `_message` brackets the code ahead
    # of the text, so naming it twice rendered every mint refusal as
    # "HTTP 400 [unauthorized_client]: unauthorized_client No active
    # integration grant…". The name belongs in one place.
    oauth_error = document.get("error")
    if isinstance(oauth_error, str):
        description = document.get("error_description")
        return (
            ApiErrorDetail(
                status=str(response.status_code),
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


_DELAY_SECONDS = re.compile(r"[0-9]+")


def _retry_after_seconds(value: str | None) -> int | None:
    """The seconds a `Retry-After` asks for, or None if it did not say one.

    RFC 9110 gives the header two forms, `delay-seconds` and an absolute
    `HTTP-date`, and the server picks. Both are read, and both come back as
    seconds. `delay-seconds` must be digits and nothing else — `-5` and
    `1.5` are malformed, and a malformed header is None, never 0, because 0
    reads as "retry now" and the server never said that. A date already past
    is 0, never negative.
    """
    if value is None:
        return None

    trimmed = value.strip()
    if _DELAY_SECONDS.fullmatch(trimmed):
        return int(trimmed)

    try:
        when = parsedate_to_datetime(trimmed)
    except (TypeError, ValueError, IndexError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)

    return max(0, round((when - datetime.now(timezone.utc)).total_seconds()))


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
    code = errors[0].code if errors else None
    failure: type[ApiError]
    if response.status_code == 401:
        failure = AuthenticationError
    else:
        failure = _BY_CODE.get(code or "", ApiError)

    raise failure(
        message,
        status_code=response.status_code,
        errors=errors,
        body=body,
        retry_after=_retry_after_seconds(response.headers.get("retry-after")),
    )
