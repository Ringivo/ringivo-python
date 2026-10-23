"""`is_retryable()`: the API's retry contract, as one table.

Retry on no answer, 408, 429, any 5xx and a 409 `idempotency_key_in_use`;
never on any other refusal.
"""

from __future__ import annotations

import httpx
import pytest

from ringivo import ApiError, AuthenticationError, RingivoError, is_retryable
from ringivo.errors import raise_for_response


def _api_error(status: int) -> ApiError:
    return ApiError(f"HTTP {status}", status_code=status)


@pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504, 599])
def test_retryable_statuses(status: int) -> None:
    assert is_retryable(_api_error(status)) is True


@pytest.mark.parametrize("status", [400, 403, 404, 409, 410, 413, 415, 422])
def test_refusals_no_retry_can_fix(status: int) -> None:
    assert is_retryable(_api_error(status)) is False


def test_a_refused_credential_is_not_retryable() -> None:
    assert is_retryable(AuthenticationError("HTTP 401", status_code=401)) is False


@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectError("refused"),
        httpx.ReadTimeout("slow"),
        httpx.ConnectTimeout("slow"),
        httpx.RemoteProtocolError("cut"),
    ],
)
def test_no_answer_is_retryable(error: Exception) -> None:
    assert is_retryable(error) is True


@pytest.mark.parametrize("error", [ValueError("bad"), RingivoError("x"), RuntimeError("x")])
def test_anything_this_package_did_not_raise_for_the_api_is_not_retryable(error: Exception) -> None:
    assert is_retryable(error) is False


@pytest.mark.parametrize(
    "error",
    [
        httpx.UnsupportedProtocol("ftp://"),
        httpx.LocalProtocolError("invalid header"),
    ],
)
def test_a_transport_error_this_client_caused_is_not_retryable(error: Exception) -> None:
    """Raised before the server said anything, about a request this client
    built wrongly: an unchanged retry fails the same way."""
    assert isinstance(error, httpx.TransportError)
    assert is_retryable(error) is False


def _refusal(status: int, code: str) -> ApiError:
    """The typed error the client raises for this answer, built the way the
    client builds it — from the wire, not by hand."""
    response = httpx.Response(
        status,
        json={"errors": [{"status": str(status), "code": code, "title": "Refused"}]},
        headers={"Retry-After": "15"},
    )
    with pytest.raises(ApiError) as caught:
        raise_for_response(response)
    return caught.value


def test_a_key_still_in_use_is_retryable_with_the_same_key() -> None:
    # 409 `idempotency_key_in_use`: the first request with this key still
    # runs. The API's own answer says to retry after `Retry-After` WITH THE
    # SAME KEY to get the first request's result — a new key could do the act
    # twice. So "try this call again, unchanged" is exactly the contract.
    error = _refusal(409, "idempotency_key_in_use")

    assert is_retryable(error) is True
    assert error.retry_after == 15


@pytest.mark.parametrize(
    "code",
    ["fax_account_suspended", "recording_audio_missing", "idempotency_key_reused", "conflict"],
)
def test_every_other_409_stays_not_retryable(code: str) -> None:
    # Only the one code is carved out. A suspended account, missing audio or
    # a key reused for another request answers the same however often it is
    # sent.
    assert is_retryable(_refusal(409, code)) is False
