"""The OAuth client-credentials layer, from the caller's side.

Every test here drives the real request path (`Ringivo._request`) against a
mocked transport, because the token is not a thing a caller ever handles: it
is fetched, cached, refreshed and retried on their behalf, and the only
evidence any of that happened is the requests that went out.

THE REFUSALS AND THE COUNTS CARRY THE WEIGHT. An assertion that a call
succeeded passes against an implementation that fetches a fresh token every
single time, so the tests that matter are the ones counting how many token
requests were made, and the one proving a 401 is retried exactly ONCE.
"""

from __future__ import annotations

import asyncio
from urllib.parse import parse_qs

import httpx
import pytest
import respx

import ringivo.auth
from ringivo import AuthenticationError, Ringivo

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
FAX_URL = f"{BASE_URL}/v1/faxes/0198c4a1-2b3c-7d4e-8f50-1a2b3c4d5e6f"
FAX_ID = "0198c4a1-2b3c-7d4e-8f50-1a2b3c4d5e6f"


def _token_response(access_token: str = "tok-1", expires_in: int | None = 3600) -> httpx.Response:
    body: dict[str, object] = {"token_type": "Bearer", "access_token": access_token}
    if expires_in is not None:
        body["expires_in"] = expires_in
    return httpx.Response(200, json=body)


def _fax_document() -> dict[str, object]:
    return {"data": {"type": "faxes", "id": FAX_ID, "attributes": {"status": "delivered"}}}


def _client() -> Ringivo:
    return Ringivo(base_url=BASE_URL, client_id="cid", client_secret="csecret")


@respx.mock
def test_the_token_request_is_the_documented_client_credentials_form() -> None:
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with _client() as client:
        client.faxes.get(FAX_ID)

    request = token.calls.last.request
    assert request.headers["content-type"] == "application/x-www-form-urlencoded"
    assert parse_qs(request.content.decode()) == {
        "grant_type": ["client_credentials"],
        "client_id": ["cid"],
        "client_secret": ["csecret"],
    }


@respx.mock
def test_scopes_are_sent_space_separated_and_omitted_when_not_asked_for() -> None:
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with Ringivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        scopes=["fax:read", "fax:write"],
    ) as client:
        client.faxes.get(FAX_ID)

    assert parse_qs(token.calls.last.request.content.decode())["scope"] == ["fax:read fax:write"]


@respx.mock
def test_the_token_is_fetched_once_and_reused() -> None:
    # The point of the cache. Passes against an implementation with no cache
    # at all only if this assertion is on the COUNT, not on the outcome.
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with _client() as client:
        client.faxes.get(FAX_ID)
        client.faxes.get(FAX_ID)
        client.faxes.get(FAX_ID)

    assert token.call_count == 1


@respx.mock
def test_the_token_is_refreshed_a_minute_before_it_expires(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # `expires_in - 60`: the margin exists so a token that is about to expire
    # is replaced BEFORE a request carries it, rather than after the server
    # has already refused one. 59 seconds into a 120-second token the cached
    # copy is still used; 61 seconds in it is not.
    clock = [1000.0]
    monkeypatch.setattr(ringivo.auth, "_monotonic", lambda: clock[0])

    token = respx.post(TOKEN_URL).mock(return_value=_token_response(expires_in=120))
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with _client() as client:
        client.faxes.get(FAX_ID)
        assert token.call_count == 1

        clock[0] = 1000.0 + 59
        client.faxes.get(FAX_ID)
        assert token.call_count == 1

        clock[0] = 1000.0 + 61
        client.faxes.get(FAX_ID)
        assert token.call_count == 2


@respx.mock
def test_a_token_with_no_expiry_is_cached_and_left_to_the_401_retry() -> None:
    # `expires_in` is optional in the spec. With no expiry to compute against
    # there is nothing to pre-empt, so the token is kept and the 401 retry
    # below is what replaces it.
    token = respx.post(TOKEN_URL).mock(return_value=_token_response(expires_in=None))
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with _client() as client:
        client.faxes.get(FAX_ID)
        client.faxes.get(FAX_ID)

    assert token.call_count == 1


@respx.mock
def test_a_401_forces_a_refresh_and_retries_the_request_once() -> None:
    # A token can stop working before it expires — revoked, rotated, or the
    # server restarted. One 401, one forced refresh, one retry carrying the
    # NEW bearer, and the caller sees the success.
    token = respx.post(TOKEN_URL).mock(
        side_effect=[_token_response("stale"), _token_response("fresh")]
    )
    fax = respx.get(FAX_URL).mock(
        side_effect=[
            httpx.Response(401, json={"errors": [{"status": "401", "title": "Unauthenticated"}]}),
            httpx.Response(200, json=_fax_document()),
        ]
    )

    with _client() as client:
        result = client.faxes.get(FAX_ID)

    assert result.id == FAX_ID
    assert token.call_count == 2
    assert fax.call_count == 2
    assert fax.calls[0].request.headers["authorization"] == "Bearer stale"
    assert fax.calls[1].request.headers["authorization"] == "Bearer fresh"


@respx.mock
def test_a_second_401_is_not_retried_again() -> None:
    # ONCE, not "until it works". A credential that has genuinely lost its
    # reach would otherwise spin, and every retry costs the server a token
    # mint. Two attempts total, then the caller is told.
    respx.post(TOKEN_URL).mock(return_value=_token_response())
    fax = respx.get(FAX_URL).mock(
        return_value=httpx.Response(
            401, json={"errors": [{"status": "401", "title": "Unauthenticated"}]}
        )
    )

    with _client() as client, pytest.raises(AuthenticationError) as caught:
        client.faxes.get(FAX_ID)

    assert fax.call_count == 2
    assert caught.value.status_code == 401


@respx.mock
def test_a_refused_credential_raises_authentication_error_carrying_the_oauth_reason() -> None:
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            401,
            json={
                "error": "invalid_client",
                "error_description": "Client authentication failed",
            },
        )
    )

    with _client() as client, pytest.raises(AuthenticationError) as caught:
        client.faxes.get(FAX_ID)

    assert caught.value.status_code == 401
    assert "invalid_client" in str(caught.value)


@respx.mock
def test_every_request_carries_the_versioned_user_agent() -> None:
    # Including the token request: an operator reading their access log wants
    # to see which SDK asked, and the token call is a request like any other.
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    fax = respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with _client() as client:
        client.faxes.get(FAX_ID)

    expected = f"Ringivo/Python {ringivo.__version__}"
    assert token.calls.last.request.headers["user-agent"] == expected
    assert fax.calls.last.request.headers["user-agent"] == expected


@respx.mock
def test_an_async_client_refuses_loudly_rather_than_sending_an_unauthenticated_request() -> None:
    """0.1.0 shipped this as a SILENT unauthenticated send, and this is the fix.

    httpx's base `Auth.async_auth_flow` defers to `Auth.auth_flow`, whose
    default body is one line — `yield request` — a PASS-THROUGH. So an async
    caller who handed this object to an `httpx.AsyncClient` got the request
    sent verbatim: no token minted, no `Authorization` header, no exception.
    The server answers 401 and the caller reads it as their credential being
    wrong.

    That is reachable, not theoretical: auth.py's own docstring advertises
    that every request through the shared client is covered "including any a
    caller makes through the vendored generated client" — and that client
    publishes `asyncio` functions beside its `sync` ones.

    So the two assertions below are one gate. Raising is only half of it; the
    half that matters is that NOTHING WENT OUT.
    """
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    fax = respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    async def attempt() -> None:
        client = Ringivo(base_url=BASE_URL, client_id="cid", client_secret="csecret")
        try:
            async with httpx.AsyncClient(auth=client._auth) as async_client:
                await async_client.get(FAX_URL)
        finally:
            client.close()

    with pytest.raises(NotImplementedError, match="sync-only"):
        asyncio.run(attempt())

    assert fax.call_count == 0, "an unauthenticated request reached the API"
    assert token.call_count == 0


def test_the_base_url_is_taken_whole_and_normalised() -> None:
    # No hostname is compiled in — the caller's base URL is the only one there
    # is (the grey-label rule, asserted from the other side in
    # tests/test_grey_label.py). A trailing slash is the one thing normalised,
    # so `.../` and `...` build the same request URL.
    with Ringivo(base_url=f"{BASE_URL}/", client_id="c", client_secret="s") as client:
        assert client.base_url == BASE_URL

    with pytest.raises(ValueError):
        Ringivo(base_url="", client_id="c", client_secret="s")
