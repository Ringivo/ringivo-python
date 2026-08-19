"""The integration-token layer, from the caller's side.

Every test here drives the real request path (`Ringivo._request`) against a
mocked transport, because the token is not a thing a caller ever handles: it
is minted, cached, refreshed and retried on their behalf, and the only
evidence any of that happened is the requests that went out.

The mint is `POST /v1/integration/token` — one JSON body carrying the
credential and the selectors, and NO `Authorization` header of its own. The
fixtures here are shaped from spec/openapi.yaml's `IntegrationTokenRequest`
and `IntegrationTokenResponse`, and `expires_in` is read off the response
rather than assumed, so a platform that shortens the token's life is
followed rather than outlived.

THE REFUSALS AND THE COUNTS CARRY THE WEIGHT. An assertion that a call
succeeded passes against an implementation that mints a fresh token every
single time, so the tests that matter are the ones counting how many token
requests were made, and the one proving a 401 is retried exactly ONCE.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import threading
from collections.abc import Sequence
from typing import Any

import httpx
import pytest
import respx

import ringivo.auth
from ringivo import ApiError, AuthenticationError, Ringivo

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/v1/integration/token"
FAX_URL = f"{BASE_URL}/v1/faxes/0198c4a1-2b3c-7d4e-8f50-1a2b3c4d5e6f"
FAX_ID = "0198c4a1-2b3c-7d4e-8f50-1a2b3c4d5e6f"
TENANT = "0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8"
CUSTOMER = "0198c4a1-6f70-7182-93a4-b5c6d7e8f901"


def _token_response(
    access_token: str = "tok-1",
    expires_in: int | None = 900,
    scopes: Sequence[str] = ("fax:read", "fax:write"),
) -> httpx.Response:
    """The mint's documented 200 — see `IntegrationTokenResponse` in the spec.

    `expires_in` is a parameter and not a constant on purpose: 900 is what
    the platform issues today, and the client's whole expiry story has to
    follow the number it was told rather than that one.
    """
    body: dict[str, object] = {
        "token_type": "Bearer",
        "access_token": access_token,
        "scopes": list(scopes),
    }
    if expires_in is not None:
        body["expires_in"] = expires_in
    return httpx.Response(200, json=body)


def _sent(route: respx.Route) -> dict[str, Any]:
    """The JSON body of the last request that reached this route."""
    body = json.loads(route.calls.last.request.content)
    assert isinstance(body, dict)
    return body


def _fax_document() -> dict[str, object]:
    return {"data": {"type": "faxes", "id": FAX_ID, "attributes": {"status": "delivered"}}}


def _client() -> Ringivo:
    return Ringivo(base_url=BASE_URL, client_id="cid", client_secret="csecret", tenant=TENANT)


@respx.mock
def test_the_mint_is_a_json_post_carrying_the_credential_and_the_tenant() -> None:
    # The whole point of 0.2.1. `POST /v1/integration/token` is the mint that
    # issues tokens the /v1 routes accept; 0.2.0 asked the platform's OAuth
    # endpoint instead and every authenticated call it made was refused.
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with _client() as client:
        client.faxes.get(FAX_ID)

    request = token.calls.last.request
    assert request.headers["content-type"] == "application/json"
    assert _sent(token) == {
        "client_id": "cid",
        "client_secret": "csecret",
        "tenant": TENANT,
    }


@respx.mock
def test_the_mint_request_carries_no_authorization_header() -> None:
    """The credential travels in the BODY, and nothing else may travel with it.

    The mint is the one request in this client that is unauthenticated —
    it is what buys the token every other request carries — so it goes
    through the auth object's own `httpx.Client` rather than the one this
    object is the `auth` of. A bearer attached here would be a token sent
    to buy a token: either stale, or a loop.

    Probed by adding `headers={"Authorization": "Bearer probe"}` to the
    mint's `post()` in auth.py: this test fails on the line below with
    `KeyError`-free, readable output naming the header that appeared.
    """
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with _client() as client:
        client.faxes.get(FAX_ID)

    sent_headers = sorted(token.calls.last.request.headers.keys())
    assert "authorization" not in sent_headers, (
        f"the mint carried a credential header: {sent_headers}"
    )
    # The DENOMINATOR: "no Authorization header" and "no request was made"
    # must not look alike.
    assert token.call_count == 1


@respx.mock
def test_the_selectors_are_sent_only_when_the_caller_names_them() -> None:
    # A selector NAMES a grant somebody already wrote; it never narrows one.
    # So an unset selector has to be ABSENT from the body rather than sent
    # empty or null — absence is what asks the platform to choose, and a
    # `customer: null` would be a different question.
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with Ringivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        customer=CUSTOMER,
    ) as client:
        client.faxes.get(FAX_ID)

    assert _sent(token)["customer"] == CUSTOMER

    with Ringivo(base_url=BASE_URL, client_id="cid", client_secret="csecret") as client:
        client.faxes.get(FAX_ID)

    named_nothing = _sent(token)
    assert "customer" not in named_nothing, "an unnamed customer was sent anyway"
    assert "tenant" not in named_nothing, "an unnamed tenant was sent anyway"
    assert named_nothing == {"client_id": "cid", "client_secret": "csecret"}


@respx.mock
def test_scopes_are_sent_as_an_array_and_omitted_when_not_asked_for() -> None:
    # `scopes` is a JSON array on this endpoint, not the space-separated
    # string of an OAuth form post.
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with Ringivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=["fax:read", "fax:write"],
    ) as client:
        client.faxes.get(FAX_ID)

    assert _sent(token)["scopes"] == ["fax:read", "fax:write"]

    with _client() as client:
        client.faxes.get(FAX_ID)

    assert "scopes" not in _sent(token)


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
def test_the_token_is_refreshed_a_minute_before_the_expiry_it_was_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # `expires_in - 60`: the margin exists so a token that is about to expire
    # is replaced BEFORE a request carries it, rather than after the server
    # has already refused one. 59 seconds into a 120-second token the cached
    # copy is still used; 61 seconds in it is not.
    #
    # 120 rather than the platform's 900 on purpose: an implementation that
    # assumed the documented quarter-hour instead of reading `expires_in`
    # would keep this token for 14 minutes and fail the last assertion.
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
    # Defensive rather than documented: `expires_in` is required of this
    # endpoint's 200, so a body without one is a platform not keeping its
    # word. With no expiry to compute against there is nothing to pre-empt,
    # so the token is kept and the 401 retry below is what replaces it —
    # which beats treating "unknown" as "expired" and minting per request.
    token = respx.post(TOKEN_URL).mock(return_value=_token_response(expires_in=None))
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with _client() as client:
        client.faxes.get(FAX_ID)
        client.faxes.get(FAX_ID)

    assert token.call_count == 1


@respx.mock
def test_a_401_forces_a_refresh_and_retries_the_request_once() -> None:
    # A token can stop working before it expires — the grant behind it is
    # re-checked on every request, so a withdrawn grant stops a token that
    # has minutes left. One 401, one forced refresh, one retry carrying the
    # NEW bearer, and the caller sees the success.
    token = respx.post(TOKEN_URL).mock(
        side_effect=[_token_response("stale"), _token_response("fresh")]
    )
    fax = respx.get(FAX_URL).mock(
        side_effect=[
            httpx.Response(401, json={"errors": [{"status": "401", "title": "Unauthorized"}]}),
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
    # reach would otherwise spin, and this endpoint is throttled harder than
    # the rest of the API — 20 attempts a minute per client id. Two attempts
    # total, then the caller is told.
    respx.post(TOKEN_URL).mock(return_value=_token_response())
    fax = respx.get(FAX_URL).mock(
        return_value=httpx.Response(
            401, json={"errors": [{"status": "401", "title": "Unauthorized"}]}
        )
    )

    with _client() as client, pytest.raises(AuthenticationError) as caught:
        client.faxes.get(FAX_ID)

    assert fax.call_count == 2
    assert caught.value.status_code == 401


@respx.mock
def test_two_threads_that_both_see_a_401_mint_exactly_one_replacement() -> None:
    """One dead token costs the server ONE mint, however many callers saw it.

    A 401 is normally seen by every request in flight at once, not by one.
    Each of them asks for a replacement and they queue on the lock; while
    `force_refresh` minted unconditionally, each one in turn bought its own
    token and threw the one in front away. Ten in-flight requests meant ten
    mints for one expired token, which is how a client that is working
    correctly walks into the mint's rate limit.

    The counts are the whole test. Both threads succeed either way — the
    bug wasted tokens, it did not break calls — so an outcome assertion
    proves nothing here.
    """
    minted = itertools.count(1)
    token = respx.post(TOKEN_URL).mock(
        side_effect=lambda request: _token_response(f"tok-{next(minted)}")
    )

    # Neither thread may start refusing until BOTH are holding their 401.
    # Without this the first could finish its whole retry before the second
    # even sent, and the test would pass against the bug it exists for.
    both_refused = threading.Barrier(2, timeout=10)

    def answer(request: httpx.Request) -> httpx.Response:
        if request.headers["authorization"] == "Bearer tok-1":
            both_refused.wait()
            return httpx.Response(401, json={"errors": [{"status": "401"}]})
        return httpx.Response(200, json=_fax_document())

    fax = respx.get(FAX_URL).mock(side_effect=answer)
    outcomes: list[object] = []

    with _client() as client:

        def call() -> None:
            # Recorded rather than raised: an exception on a worker thread
            # is invisible to pytest, so a thread that died would otherwise
            # look like a thread that passed.
            try:
                outcomes.append(client.faxes.get(FAX_ID).id)
            except BaseException as exc:  # noqa: BLE001 - asserted on below
                outcomes.append(exc)

        threads = [threading.Thread(target=call) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

    assert outcomes == [FAX_ID, FAX_ID]
    assert token.call_count == 2, (
        "the first mint, then exactly one replacement for the 401 both threads saw"
    )
    # Order-independent: which thread is recorded first is a race. What
    # matters is that the two retries carried the SAME new token.
    assert sorted(call.request.headers["authorization"] for call in fax.calls) == [
        "Bearer tok-1",
        "Bearer tok-1",
        "Bearer tok-2",
        "Bearer tok-2",
    ]


@respx.mock
def test_a_refused_credential_raises_authentication_error_carrying_the_reason() -> None:
    # The mint answers JSON:API error documents like the rest of the API.
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            401,
            json={
                "errors": [
                    {
                        "status": "401",
                        "title": "Unauthorized",
                        "detail": "Invalid client credentials.",
                    }
                ]
            },
        )
    )
    fax = respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with _client() as client, pytest.raises(AuthenticationError) as caught:
        client.faxes.get(FAX_ID)

    assert caught.value.status_code == 401
    assert caught.value.errors[0].detail == "Invalid client credentials."
    assert fax.call_count == 0, "a request went out on a token that was never minted"


@respx.mock
def test_a_selector_no_grant_covers_is_the_403_and_it_reaches_the_caller_whole() -> None:
    # Good credentials, no grant. The platform answers the same 403 for a
    # tenant nobody granted this client and for a customer nobody granted
    # it — deliberately, so a caller cannot map a reseller's customers by
    # asking. There is nothing for the client to retry, so it does not.
    token = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            403,
            json={
                "errors": [
                    {
                        "status": "403",
                        "title": "Forbidden",
                        "detail": "No active integration grant for this tenant.",
                    }
                ]
            },
        )
    )
    fax = respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with _client() as client, pytest.raises(ApiError) as caught:
        client.faxes.get(FAX_ID)

    assert caught.value.status_code == 403
    assert caught.value.errors[0].detail == "No active integration grant for this tenant."
    assert token.call_count == 1, "the client tried again at an endpoint that had said no"
    assert fax.call_count == 0


@respx.mock
def test_a_malformed_selector_is_the_422_and_it_names_the_member() -> None:
    # A selector that is not a uuid. `source.pointer` names which one, and
    # the caller gets it: this is a bug in their configuration, and the
    # difference between `/tenant` and `/customer` is the whole answer.
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            422,
            json={
                "errors": [
                    {
                        "status": "422",
                        "title": "Unprocessable Entity",
                        "detail": "The customer field must be a valid UUID.",
                        "source": {"pointer": "/customer"},
                    }
                ]
            },
        )
    )

    with Ringivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        customer="not-a-uuid",
    ) as client:
        with pytest.raises(ApiError) as caught:
            client.faxes.get(FAX_ID)

    assert caught.value.status_code == 422
    assert caught.value.errors[0].source == {"pointer": "/customer"}


@respx.mock
def test_a_flat_oauth_error_body_is_folded_into_the_same_exception() -> None:
    # Defensive, and cheap to keep: the mint answers JSON:API, but a
    # platform fronting it with an OAuth-style gateway can still put RFC
    # 6749's flat `{"error": ...}` in front of the caller. Both shapes fold
    # into one exception so a caller has one thing to catch.
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
    assert caught.value.code == "invalid_client"
    assert "invalid_client" in str(caught.value)


@respx.mock
def test_every_request_carries_the_versioned_user_agent() -> None:
    # Including the mint: an operator reading their access log wants to see
    # which SDK asked, and the mint is a request like any other.
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

    Two assertions, one gate. Raising is only half of it; the half that
    matters is that NOTHING WENT OUT — so that half is asserted FIRST.

    Deliberately not `pytest.raises`: with the guard deleted the request
    SUCCEEDS, `pytest.raises` fails on that line, and the counts below
    never run — the test would then report "DID NOT RAISE" rather than the
    failure it is written to catch. Probed by deleting the `raise` in
    `async_auth_flow`: the message that comes back is the one on the next
    line.
    """
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    fax = respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))
    refusal: BaseException | None = None

    async def attempt() -> None:
        nonlocal refusal
        client = Ringivo(
            base_url=BASE_URL, client_id="cid", client_secret="csecret", tenant=TENANT
        )
        try:
            async with httpx.AsyncClient(auth=client._auth) as async_client:
                await async_client.get(FAX_URL)
        except NotImplementedError as caught:
            refusal = caught
        finally:
            client.close()

    asyncio.run(attempt())

    assert fax.call_count == 0, "an unauthenticated request reached the API"
    assert token.call_count == 0
    assert refusal is not None, "an async client was allowed to use the sync-only auth"
    assert "sync-only" in str(refusal)


def test_the_base_url_is_taken_whole_and_normalised() -> None:
    # No hostname is compiled in — the caller's base URL is the only one there
    # is (the grey-label rule, asserted from the other side in
    # tests/test_grey_label.py). A trailing slash is the one thing normalised,
    # so `.../` and `...` build the same request URL.
    with Ringivo(base_url=f"{BASE_URL}/", client_id="c", client_secret="s") as client:
        assert client.base_url == BASE_URL

    with pytest.raises(ValueError):
        Ringivo(base_url="", client_id="c", client_secret="s")
