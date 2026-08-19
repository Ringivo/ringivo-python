"""The OAuth client-credentials layer again, from an ASYNC caller's side.

The mirror of tests/test_auth.py, and a mirror on purpose. `AsyncRingivo`
holds its own lock, its own token cache and its own clock seam, so every
count the sync suite proves has to be proved a second time here: an async
twin that quietly refetched a token on every request would pass the sync
suite untouched.

The last test is the one that is NOT a mirror but an INVERSION. The sync
suite proves the sync auth refuses an `httpx.AsyncClient`; this one proves
the async auth refuses an `httpx.Client`, because the same silent
unauthenticated send is available in that direction too.
"""

from __future__ import annotations

from urllib.parse import parse_qs

import httpx
import pytest
import respx

import ringivo.async_auth
from ringivo import AsyncRingivo, AuthenticationError

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
FAX_ID = "0198c4a1-2b3c-7d4e-8f50-1a2b3c4d5e6f"
FAX_URL = f"{BASE_URL}/v1/faxes/{FAX_ID}"


def _token_response(access_token: str = "tok-1", expires_in: int | None = 3600) -> httpx.Response:
    body: dict[str, object] = {"token_type": "Bearer", "access_token": access_token}
    if expires_in is not None:
        body["expires_in"] = expires_in
    return httpx.Response(200, json=body)


def _fax_document() -> dict[str, object]:
    return {"data": {"type": "faxes", "id": FAX_ID, "attributes": {"status": "delivered"}}}


def _client() -> AsyncRingivo:
    return AsyncRingivo(base_url=BASE_URL, client_id="cid", client_secret="csecret")


@pytest.mark.anyio
@respx.mock
async def test_the_token_request_is_the_documented_client_credentials_form() -> None:
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    async with _client() as client:
        await client.faxes.get(FAX_ID)

    request = token.calls.last.request
    assert request.headers["content-type"] == "application/x-www-form-urlencoded"
    assert parse_qs(request.content.decode()) == {
        "grant_type": ["client_credentials"],
        "client_id": ["cid"],
        "client_secret": ["csecret"],
    }


@pytest.mark.anyio
@respx.mock
async def test_scopes_are_sent_space_separated_and_omitted_when_not_asked_for() -> None:
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    async with AsyncRingivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        scopes=["fax:read", "fax:write"],
    ) as client:
        await client.faxes.get(FAX_ID)

    assert parse_qs(token.calls.last.request.content.decode())["scope"] == ["fax:read fax:write"]


@pytest.mark.anyio
@respx.mock
async def test_the_token_is_fetched_once_and_reused() -> None:
    # The point of the cache, asserted on the COUNT: an outcome assertion
    # passes against an implementation with no cache at all.
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    async with _client() as client:
        await client.faxes.get(FAX_ID)
        await client.faxes.get(FAX_ID)
        await client.faxes.get(FAX_ID)

    assert token.call_count == 1


@pytest.mark.anyio
@respx.mock
async def test_the_token_is_refreshed_a_minute_before_it_expires(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # `expires_in - 60`, the same margin the sync client keeps. 59 seconds
    # into a 120-second token the cached copy is still used; 61 seconds in it
    # is not. The seam is this module's own `_monotonic`, not auth.py's —
    # the two clients are twins, not one implementation, so each carries its
    # own alias and patching one does not move the other.
    clock = [1000.0]
    monkeypatch.setattr(ringivo.async_auth, "_monotonic", lambda: clock[0])

    token = respx.post(TOKEN_URL).mock(return_value=_token_response(expires_in=120))
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    async with _client() as client:
        await client.faxes.get(FAX_ID)
        assert token.call_count == 1

        clock[0] = 1000.0 + 59
        await client.faxes.get(FAX_ID)
        assert token.call_count == 1

        clock[0] = 1000.0 + 61
        await client.faxes.get(FAX_ID)
        assert token.call_count == 2


@pytest.mark.anyio
@respx.mock
async def test_a_token_with_no_expiry_is_cached_and_left_to_the_401_retry() -> None:
    token = respx.post(TOKEN_URL).mock(return_value=_token_response(expires_in=None))
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    async with _client() as client:
        await client.faxes.get(FAX_ID)
        await client.faxes.get(FAX_ID)

    assert token.call_count == 1


@pytest.mark.anyio
@respx.mock
async def test_a_401_forces_a_refresh_and_retries_the_request_once() -> None:
    token = respx.post(TOKEN_URL).mock(
        side_effect=[_token_response("stale"), _token_response("fresh")]
    )
    fax = respx.get(FAX_URL).mock(
        side_effect=[
            httpx.Response(401, json={"errors": [{"status": "401", "title": "Unauthenticated"}]}),
            httpx.Response(200, json=_fax_document()),
        ]
    )

    async with _client() as client:
        result = await client.faxes.get(FAX_ID)

    assert result.id == FAX_ID
    assert token.call_count == 2
    assert fax.call_count == 2
    assert fax.calls[0].request.headers["authorization"] == "Bearer stale"
    assert fax.calls[1].request.headers["authorization"] == "Bearer fresh"


@pytest.mark.anyio
@respx.mock
async def test_a_second_401_is_not_retried_again() -> None:
    # ONCE, not "until it works". Two attempts total, then the caller is told.
    respx.post(TOKEN_URL).mock(return_value=_token_response())
    fax = respx.get(FAX_URL).mock(
        return_value=httpx.Response(
            401, json={"errors": [{"status": "401", "title": "Unauthenticated"}]}
        )
    )

    async with _client() as client:
        with pytest.raises(AuthenticationError) as caught:
            await client.faxes.get(FAX_ID)

    assert fax.call_count == 2
    assert caught.value.status_code == 401


@pytest.mark.anyio
@respx.mock
async def test_a_refused_credential_raises_authentication_error_carrying_the_oauth_reason() -> None:
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            401,
            json={
                "error": "invalid_client",
                "error_description": "Client authentication failed",
            },
        )
    )

    async with _client() as client:
        with pytest.raises(AuthenticationError) as caught:
            await client.faxes.get(FAX_ID)

    assert caught.value.status_code == 401
    assert "invalid_client" in str(caught.value)


@pytest.mark.anyio
@respx.mock
async def test_every_request_carries_the_versioned_user_agent() -> None:
    # One User-Agent for both clients: an operator reading their access log
    # sees which SDK asked, not which of its two front doors was used.
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    fax = respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    async with _client() as client:
        await client.faxes.get(FAX_ID)

    expected = f"Ringivo/Python {ringivo.__version__}"
    assert token.calls.last.request.headers["user-agent"] == expected
    assert fax.calls.last.request.headers["user-agent"] == expected


@pytest.mark.anyio
@respx.mock
async def test_a_sync_client_refuses_loudly_rather_than_sending_an_unauthenticated_request() -> None:
    """The INVERSION of tests/test_auth.py's async guard, and the same trap.

    `httpx.Auth.sync_auth_flow` has a default body of one line — `yield
    request` — a PASS-THROUGH. So an `httpx.Client` handed this object
    would send the request verbatim: no token minted, no `Authorization`
    header, no error, and a 401 the caller reads as their credential being
    wrong.

    Reachable rather than theoretical: a caller who has both clients in one
    codebase, or who reaches for the vendored generated client's `sync`
    functions, wires this by hand in a minute.

    Two assertions, one gate. Raising is only half of it; the half that
    matters is that NOTHING WENT OUT — so that half is asserted FIRST.

    Deliberately not `pytest.raises`: with the guard deleted the request
    SUCCEEDS, `pytest.raises` fails on that line, and the counts below
    never run — the test would then report "DID NOT RAISE" rather than the
    failure it is written to catch. Probed by deleting `sync_auth_flow`:
    the message that comes back is the one on the next line.
    """
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    fax = respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))
    refusal: BaseException | None = None

    async with _client() as client:
        with httpx.Client(auth=client._auth) as sync_client:
            try:
                sync_client.get(FAX_URL)
            except NotImplementedError as caught:
                refusal = caught

    assert fax.call_count == 0, "an unauthenticated request reached the API"
    assert token.call_count == 0
    assert refusal is not None, "a sync client was allowed to use the async auth"
    assert "async-only" in str(refusal)


@pytest.mark.anyio
async def test_the_base_url_is_taken_whole_and_normalised() -> None:
    # No hostname is compiled in here either — the caller's base URL is the
    # only one there is. A trailing slash is the one thing normalised.
    async with AsyncRingivo(base_url=f"{BASE_URL}/", client_id="c", client_secret="s") as client:
        assert client.base_url == BASE_URL

    with pytest.raises(ValueError):
        AsyncRingivo(base_url="", client_id="c", client_secret="s")
