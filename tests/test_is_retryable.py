"""`is_retryable()`: the API's retry contract, as one table.

Retry on no answer, 408, 429 and any 5xx; never on any other refusal.
"""

from __future__ import annotations

import httpx
import pytest

from ringivo import ApiError, AuthenticationError, RingivoError, is_retryable


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
