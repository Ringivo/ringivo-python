"""The integration-token layer again, from an ASYNC caller's side.

The mirror of tests/test_auth.py, and a mirror on purpose. `AsyncRingivo`
holds its own lock, its own token cache and its own clock seam, so every
count the sync suite proves has to be proved a second time here: an async
twin that quietly re-minted a token on every request, or that dropped a
selector from the body, would pass the sync suite untouched.

That includes the MINT'S SHAPE and its error vocabulary: the body carries a
`client_credentials` grant type, a `tenant` and a space-delimited `scope` —
all three required — and `POST /oauth/token` refuses in RFC 6749's flat
`{"error", …}` while every `/v1` resource keeps answering JSON:API.
`_token_request_body` is shared, but nothing else on this path is, so the
assertions are made a second time here rather than inherited. The
constructor guards especially: `AsyncRingivo` could lose either of them on
its own and the sync suite would stay green.

The last test is the one that is NOT a mirror but an INVERSION. The sync
suite proves the sync auth refuses an `httpx.AsyncClient`; this one proves
the async auth refuses an `httpx.Client`, because the same silent
unauthenticated send is available in that direction too.
"""

from __future__ import annotations

import asyncio
import inspect
import itertools
import json
from collections.abc import Sequence
from typing import Any

import httpx
import pytest
import respx

import ringivo.async_auth
from ringivo import ApiError, AsyncRingivo, AuthenticationError

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
FAX_ID = "0198c4a1-2b3c-7d4e-8f50-1a2b3c4d5e6f"
FAX_URL = f"{BASE_URL}/v1/faxes/{FAX_ID}"
TENANT = "0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8"
CUSTOMER = "0198c4a1-6f70-7182-93a4-b5c6d7e8f901"


def _token_response(
    access_token: str = "tok-1",
    expires_in: int | None = 900,
    scopes: Sequence[str] = ("fax:read", "fax:write"),
) -> httpx.Response:
    """The mint's documented 200 — see `OauthTokenResponse` in the spec.

    Both scope members, because the endpoint sends both: `scope` is RFC
    6749's space-joined effective set and `scopes` is the same names as an
    array. Only `scopes` is required of the response, but a token with no
    scopes is refused rather than issued, so an integrator sees both.
    """
    body: dict[str, object] = {
        "token_type": "Bearer",
        "access_token": access_token,
        "scope": " ".join(scopes),
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


def _oauth_error(
    status: int, error: str, description: str | None = None, hint: str | None = None
) -> httpx.Response:
    """A refusal in the mint's vocabulary — RFC 6749's flat shape.

    `hint` is optional because the platform sends it on some refusals and
    not others — it is the only member that tells the two `invalid_scope`
    causes apart.
    """
    body: dict[str, object] = {"error": error}
    if description is not None:
        body["error_description"] = description
    if hint is not None:
        body["hint"] = hint
    return httpx.Response(status, json=body)


#: Every client here names a tenant and scopes, because a client missing
#: either is refused at construction — see the two tests that prove it,
#: `test_a_client_that_names_no_tenant_is_refused_at_construction` and
#: `test_a_client_that_asks_for_no_scopes_is_refused_at_construction`.
SCOPES = ["fax:read", "fax:write"]


def _client() -> AsyncRingivo:
    return AsyncRingivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=SCOPES,
    )


class _Gate:
    """Hold every arrival until `parties` of them are waiting.

    `asyncio.Barrier` would say this in one line, and it landed in 3.11 —
    this package supports 3.10. The timeout is what turns a task that never
    arrives into a failure instead of a hung suite.
    """

    def __init__(self, parties: int) -> None:
        self._parties = parties
        self._arrived = 0
        self._open = asyncio.Event()

    async def wait(self) -> None:
        self._arrived += 1
        if self._arrived >= self._parties:
            self._open.set()
        await asyncio.wait_for(self._open.wait(), timeout=10)


@pytest.mark.anyio
@respx.mock
async def test_the_mint_is_a_json_post_carrying_the_credential_and_the_tenant() -> None:
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    async with _client() as client:
        await client.faxes.get(FAX_ID)

    request = token.calls.last.request
    assert request.headers["content-type"] == "application/json"
    assert _sent(token) == {
        "grant_type": "client_credentials",
        "client_id": "cid",
        "client_secret": "csecret",
        "tenant": TENANT,
        "scope": "fax:read fax:write",
    }


@pytest.mark.anyio
@respx.mock
async def test_the_mint_request_carries_no_authorization_header() -> None:
    """The credential travels in the BODY, and nothing else may travel with it.

    The async mint has its own `httpx.AsyncClient`, so the sync suite's
    proof of this does not carry over: a bearer added here would be a
    token sent to buy a token, and nothing in the sync client would say so.

    The assertion is on `Authorization` and not on `Bearer` because the
    platform now refuses two credentials on one request — a body
    `client_secret` beside an `Authorization: Basic` header is a 400
    `invalid_request` (RFC 6749 section 2.3). This client sends its secret
    exactly one way, and the line below is what says so.

    Probed by adding `headers={"Authorization": "Bearer probe"}` to the
    mint's `post()` in async_auth.py: this test fails on the line below,
    naming the header that appeared.
    """
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    async with _client() as client:
        await client.faxes.get(FAX_ID)

    sent_headers = sorted(token.calls.last.request.headers.keys())
    assert "authorization" not in sent_headers, (
        f"the mint carried a credential header: {sent_headers}"
    )
    # The DENOMINATOR: "no Authorization header" and "no request was made"
    # must not look alike.
    assert token.call_count == 1


@pytest.mark.anyio
@respx.mock
async def test_the_tenant_is_always_sent_and_the_customer_only_when_named() -> None:
    # THE INVERSION of what this asserted through 0.3.x, and the twin of the
    # sync suite's. `customer` may be absent, and an absent one is left out
    # rather than sent as null — the platform reads both spellings the same
    # way. `tenant` may NOT: the mint used to infer it from the single
    # active grant behind the credential, and with that inference deleted an
    # unnamed tenant is a 400 `invalid_request`.
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    async with AsyncRingivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        customer=CUSTOMER,
        scopes=SCOPES,
    ) as client:
        await client.faxes.get(FAX_ID)

    assert _sent(token)["customer"] == CUSTOMER

    async with AsyncRingivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=SCOPES,
    ) as client:
        await client.faxes.get(FAX_ID)

    tenant_wide = _sent(token)
    assert "customer" not in tenant_wide, "an unnamed customer was sent anyway"
    assert tenant_wide == {
        "grant_type": "client_credentials",
        "client_id": "cid",
        "client_secret": "csecret",
        "tenant": TENANT,
        "scope": "fax:read fax:write",
    }


@pytest.mark.anyio
@respx.mock
async def test_scopes_are_sent_as_one_space_delimited_string_and_not_as_an_array() -> None:
    # The mint does not read the `scopes` array the deleted endpoint took.
    # A body carrying only the array asks for NOTHING, and asking for
    # nothing is refused at the mint — 400 `invalid_scope` — rather than
    # answered with a token that authorises nothing.
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    async with AsyncRingivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=["fax:read", "fax:write"],
    ) as client:
        await client.faxes.get(FAX_ID)

    sent = _sent(token)
    assert sent["scope"] == "fax:read fax:write", "the order the caller asked in, space-joined"
    assert "scopes" not in sent, "the deleted mint's array member, which this endpoint ignores"


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
async def test_the_token_is_refreshed_a_minute_before_the_expiry_it_was_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # `expires_in - 60`, the same margin the sync client keeps, and read off
    # the response rather than assumed: 120 seconds here, so an
    # implementation that took the platform's usual 900 for granted would
    # hold this token for fourteen minutes and fail the last assertion.
    #
    # The seam is this module's own `_monotonic`, not auth.py's — the two
    # clients are twins, not one implementation, so each carries its own
    # alias and patching one does not move the other.
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
    # Defensive rather than documented: `expires_in` is required of this
    # endpoint's 200. With no expiry to compute against there is nothing to
    # pre-empt, so the token is kept and the 401 retry replaces it.
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
            httpx.Response(401, json={"errors": [{"status": "401", "title": "Unauthorized"}]}),
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
            401, json={"errors": [{"status": "401", "title": "Unauthorized"}]}
        )
    )

    async with _client() as client:
        with pytest.raises(AuthenticationError) as caught:
            await client.faxes.get(FAX_ID)

    assert fax.call_count == 2
    assert caught.value.status_code == 401


@pytest.mark.anyio
@respx.mock
async def test_two_tasks_that_both_see_a_401_mint_exactly_one_replacement() -> None:
    """The twin of the sync test, and the same rule: one dead token, one mint.

    Concurrency is the reason the async client is worth having, so this is
    the shape it will meet first: a gather of requests that all carry the
    token the server has just stopped accepting. While `force_refresh`
    minted unconditionally, each task in turn bought its own replacement
    and threw the one in front away.

    The counts are the whole test. Both tasks succeed either way — the bug
    wasted tokens, it did not break calls.
    """
    minted = itertools.count(1)
    token = respx.post(TOKEN_URL).mock(
        side_effect=lambda request: _token_response(f"tok-{next(minted)}")
    )

    # Neither task may start refusing until BOTH are holding their 401.
    # Without this the first could finish its whole retry before the second
    # even sent, and the test would pass against the bug it exists for.
    both_refused = _Gate(2)

    async def answer(request: httpx.Request) -> httpx.Response:
        if request.headers["authorization"] == "Bearer tok-1":
            await both_refused.wait()
            return httpx.Response(401, json={"errors": [{"status": "401"}]})
        return httpx.Response(200, json=_fax_document())

    fax = respx.get(FAX_URL).mock(side_effect=answer)

    async with _client() as client:
        results = await asyncio.gather(client.faxes.get(FAX_ID), client.faxes.get(FAX_ID))

    assert [result.id for result in results] == [FAX_ID, FAX_ID]
    assert token.call_count == 2, (
        "the first mint, then exactly one replacement for the 401 both tasks saw"
    )
    # Order-independent: which task is recorded first is a race. What
    # matters is that the two retries carried the SAME new token.
    assert sorted(call.request.headers["authorization"] for call in fax.calls) == [
        "Bearer tok-1",
        "Bearer tok-1",
        "Bearer tok-2",
        "Bearer tok-2",
    ]


@pytest.mark.anyio
@respx.mock
async def test_a_refused_credential_is_the_401_and_it_carries_the_oauth_code() -> None:
    # The mint answers RFC 6749's flat shape. A 401 is still an
    # `AuthenticationError` — the subclass is chosen by the STATUS, so the
    # vocabulary change does not move it.
    respx.post(TOKEN_URL).mock(
        return_value=_oauth_error(401, "invalid_client", "Client authentication failed")
    )
    fax = respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    async with _client() as client:
        with pytest.raises(AuthenticationError) as caught:
            await client.faxes.get(FAX_ID)

    assert caught.value.status_code == 401
    assert caught.value.code == "invalid_client"
    assert caught.value.errors[0].detail == "Client authentication failed"
    assert fax.call_count == 0, "a request went out on a token that was never minted"


@pytest.mark.anyio
@respx.mock
async def test_a_selector_no_grant_covers_is_a_400_and_it_reaches_the_caller_whole() -> None:
    # Good credentials, no grant. The same BYTES answer a tenant nobody
    # granted this client and a customer nobody granted it — deliberately,
    # so a caller cannot map a reseller's customers by asking. Pinned
    # verbatim rather than by substring: a more specific message from the
    # platform would be a regression, and a substring match sails past it.
    #
    # A 400 rather than the 403 it was through 0.3.x: RFC 6749 section 5.2
    # gives the token endpoint one status for every refusal but a bad
    # credential, which is why `code` is the assertion worth copying.
    token = respx.post(TOKEN_URL).mock(
        return_value=_oauth_error(
            400, "unauthorized_client", "No active integration grant for this tenant."
        )
    )
    fax = respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    async with _client() as client:
        with pytest.raises(ApiError) as caught:
            await client.faxes.get(FAX_ID)

    assert caught.value.status_code == 400
    assert caught.value.code == "unauthorized_client"
    assert caught.value.errors[0].detail == "No active integration grant for this tenant."
    assert token.call_count == 1, "the client tried again at an endpoint that had said no"
    assert fax.call_count == 0


@pytest.mark.parametrize(
    ("status", "error", "description"),
    [
        (
            400,
            "invalid_request",
            "The tenant and customer selectors must be UUIDs, and customer requires a tenant.",
        ),
        # No tenant at all — unreachable through this package's constructor,
        # which is the point of it, but the first refusal a caller who
        # writes the mint by hand meets.
        (400, "invalid_request", "The tenant parameter is required."),
        # Two secrets on one request (RFC 6749 section 2.3). This client
        # sends exactly one, which is asserted directly in
        # test_the_mint_request_carries_no_authorization_header.
        (400, "invalid_request", "Only one authentication method may be used per request."),
        (400, "invalid_scope", "The requested scope is invalid, unknown, or malformed"),
        # The empty intersection: every scope asked for was dropped and
        # nothing is left, so a token is refused rather than issued.
        (
            400,
            "invalid_scope",
            "None of the requested scopes are on this grant. Ask for at least one scope the "
            "grant carries.",
        ),
    ],
    ids=[
        "malformed-selector",
        "missing-tenant",
        "two-secrets",
        "unknown-scope-name",
        "empty-scope-intersection",
    ],
)
@pytest.mark.anyio
@respx.mock
async def test_the_mints_other_refusals_arrive_typed_and_carry_their_code(
    status: int, error: str, description: str
) -> None:
    # `code` is what a caller branches on, and the status cannot tell these
    # apart at all — RFC 6749 section 5.2 gives the token endpoint one
    # status for every refusal but a bad credential, so all five are 400.
    token = respx.post(TOKEN_URL).mock(return_value=_oauth_error(status, error, description))
    fax = respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    async with _client() as client:
        with pytest.raises(ApiError) as caught:
            await client.faxes.get(FAX_ID)

    assert caught.value.status_code == status
    assert caught.value.code == error
    assert caught.value.errors[0].detail == description
    assert token.call_count == 1
    assert fax.call_count == 0


@pytest.mark.anyio
@respx.mock
async def test_the_two_invalid_scope_causes_are_told_apart_by_the_hint_this_client_keeps() -> None:
    # One `code`, two causes: an unpublished scope NAME (a typo, which
    # carries a `hint` naming the offender) and an intersection that came
    # out EMPTY (a permission answer, which carries none). `ApiErrorDetail`
    # has no field for `hint`, so the whole document is kept on `raw` — and
    # the ABSENCE is the half that matters, since a parser that defaulted a
    # missing `hint` would make the two causes indistinguishable again.
    respx.post(TOKEN_URL).mock(
        return_value=_oauth_error(
            400,
            "invalid_scope",
            "The requested scope is invalid, unknown, or malformed",
            hint="fax:reed",
        )
    )

    async with _client() as client:
        with pytest.raises(ApiError) as typo:
            await client.faxes.get(FAX_ID)

    assert typo.value.code == "invalid_scope"
    assert typo.value.errors[0].raw["hint"] == "fax:reed"

    respx.post(TOKEN_URL).mock(
        return_value=_oauth_error(
            400,
            "invalid_scope",
            "None of the requested scopes are on this grant. Ask for at least one scope the "
            "grant carries.",
        )
    )

    async with _client() as client:
        with pytest.raises(ApiError) as nothing_survived:
            await client.faxes.get(FAX_ID)

    assert nothing_survived.value.code == "invalid_scope"
    assert "hint" not in nothing_survived.value.errors[0].raw, (
        "a hint was invented for the refusal that does not carry one, which is the only "
        "thing telling these two causes apart"
    )


@pytest.mark.anyio
@respx.mock
async def test_a_throttled_mint_reaches_the_caller_rather_than_being_retried() -> None:
    # 60 a minute per IP and 20 a minute per client id, whichever is
    # reached first. A client that answered a 429 with another mint would
    # spend the rest of the budget proving it. The throttle answers before
    # the mint runs, so the body is NEITHER vocabulary and is not even
    # JSON — it is the framework's own rate-limit page, as HTML, whatever
    # the request asked to accept. The client must still raise, still carry
    # the status, and still put the body in front of the caller.
    token = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            429,
            html="<!DOCTYPE html><title>Too Many Attempts.</title>",
            headers={"Retry-After": "42"},
        )
    )
    fax = respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    async with _client() as client:
        with pytest.raises(ApiError) as caught:
            await client.faxes.get(FAX_ID)

    assert caught.value.status_code == 429
    assert caught.value.code is None, "no OAuth code was sent, so none may be invented"
    assert caught.value.errors == (), "an HTML page was read as a refusal document"
    assert "Too Many Attempts." in str(caught.value), "the body never reached the caller"
    assert token.call_count == 1, "a throttled client asked again"
    assert fax.call_count == 0


@pytest.mark.anyio
@respx.mock
async def test_the_mint_and_the_resources_speak_different_error_vocabularies() -> None:
    # THE BOUNDARY, from both sides. The mint refuses in RFC 6749's flat
    # shape; every `/v1` resource keeps its JSON:API document. Written as
    # ONE test because the property is a relationship: two separate tests
    # each pass against a client that had quietly stopped reading the other
    # shape.
    respx.post(TOKEN_URL).mock(return_value=_oauth_error(401, "invalid_client", "no"))

    async with _client() as client:
        with pytest.raises(AuthenticationError) as at_the_mint:
            await client.faxes.get(FAX_ID)

    assert at_the_mint.value.code == "invalid_client"
    assert at_the_mint.value.errors[0].source is None, "an OAuth refusal has no JSON:API source"

    respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(
        return_value=httpx.Response(
            422,
            json={
                "errors": [
                    {
                        "status": "422",
                        "title": "Unprocessable Entity",
                        "detail": "The to field format is invalid.",
                        "code": "validation_failed",
                        "source": {"parameter": "to"},
                    }
                ]
            },
        )
    )

    async with _client() as client:
        with pytest.raises(ApiError) as at_the_resource:
            await client.faxes.get(FAX_ID)

    assert at_the_resource.value.code == "validation_failed"
    assert at_the_resource.value.errors[0].source == {"parameter": "to"}
    assert at_the_resource.value.errors[0].title == "Unprocessable Entity"


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
async def test_a_sync_client_refuses_loudly_rather_than_sending_it_unauthenticated() -> None:
    """The INVERSION of tests/test_auth.py's async guard, and the same trap.

    `httpx.Auth.sync_auth_flow` has a default body of one line — `yield
    request` — a PASS-THROUGH. So an `httpx.Client` handed this object
    would send the request verbatim: no token minted, no `Authorization`
    header, no error, and a 401 the caller reads as their credential being
    wrong.

    Reachable rather than theoretical: a caller who has both clients in one
    codebase, and who reaches for `client._auth` to wire up a request the
    wrapper does not cover, does this by hand in a minute.

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
    async with AsyncRingivo(
        base_url=f"{BASE_URL}/", client_id="c", client_secret="s", tenant=TENANT, scopes=SCOPES
    ) as client:
        assert client.base_url == BASE_URL

    with pytest.raises(ValueError):
        AsyncRingivo(base_url="", client_id="c", client_secret="s", tenant=TENANT, scopes=SCOPES)


@pytest.mark.anyio
@respx.mock
async def test_a_client_that_names_no_tenant_is_refused_before_anything_is_built() -> None:
    """The twin of the sync refusal, and the same inversion.

    Through 0.3.x a client built with no tenant was legal here too, and the
    mint resolved the absence to the single active grant behind the
    credential. That inference is deleted — it broke integrations on the day
    a reseller granted a second tenant, in code nobody had touched — so the
    omission is unrepresentable rather than discouraged.

    Two guards, two different mistakes: omitting the argument is a
    `TypeError` from Python and from a type checker, while an EMPTY string
    type-checks perfectly and is refused with a `ValueError` instead,
    because the mint reads a valueless parameter as an absent one.

    The signature is asserted SEPARATELY from the behaviour, for the reason
    the sync twin sets out in full: with a default restored the omitted
    construction still raises, because the emptiness guard catches `None`
    too — so a red test would not have meant the argument was still
    required, and only the signature check means that.

    Written a second time rather than inherited: `AsyncRingivo` could lose
    either guard on its own and the sync suite would stay green.

    Probed both ways: restoring `tenant: str | None = None` fails the
    signature assertion by name, and deleting the `if not tenant` block
    fails the empty-string assertion.
    """
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    signature = inspect.signature(AsyncRingivo)
    assert signature.parameters["tenant"].default is inspect.Parameter.empty, (
        "tenant has a default again, so a caller can omit it and their type checker agrees"
    )

    omitted: BaseException | None = None
    try:
        built = AsyncRingivo(  # type: ignore[call-arg] - the missing argument is the point
            base_url=BASE_URL,
            client_id="cid",
            client_secret="csecret",
            scopes=SCOPES,
        )
    except (TypeError, ValueError) as caught:
        omitted = caught
    else:
        await built.aclose()

    empty: BaseException | None = None
    try:
        built = AsyncRingivo(
            base_url=BASE_URL,
            client_id="cid",
            client_secret="csecret",
            tenant="",
            scopes=SCOPES,
        )
    except ValueError as caught:
        empty = caught
    else:
        await built.aclose()

    # Nothing may reach the network to discover either.
    assert token.call_count == 0, "a refused client still reached the mint"
    assert omitted is not None, "a client with no tenant was built"
    assert isinstance(omitted, TypeError), (
        f"omitting the tenant was refused as {type(omitted).__name__}, which means the "
        "signature stopped requiring it and only the runtime guard is left"
    )
    assert "tenant" in str(omitted), omitted
    assert empty is not None, "a client with an empty tenant was built"
    assert "tenant is required" in str(empty), empty

    # THE CONTROL: one variable changed — a tenant is named — and the same
    # construction works and puts that tenant on the wire.
    async with AsyncRingivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=SCOPES,
    ) as client:
        await client.faxes.get(FAX_ID)

    assert token.call_count == 1
    assert _sent(token)["tenant"] == TENANT


@pytest.mark.anyio
@respx.mock
async def test_a_client_that_asks_for_no_scopes_is_refused_at_construction() -> None:
    """The twin of the sync refusal: a scopeless client is not built.

    Ask for nothing and the intersection is empty, and the mint refuses an
    empty one — 400 `invalid_scope` — rather than issuing a token that
    authorises nothing.

    Written a second time rather than inherited, because the constructors
    are twins: `AsyncRingivo` could lose this guard on its own and the sync
    suite would stay green.

    None and [] are the same mistake and both are refused; the CONTROL
    underneath proves the guard rejects the empty question rather than
    every question.

    Probed by deleting the `if not scopes` block in async_client.py: this
    test fails at `unset is not None` with "a client with no scopes was
    built".
    """
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    async def refusal(scopes: object) -> BaseException | None:
        # Released rather than leaked when the guard is gone: an unclosed
        # httpx.AsyncClient would turn a failing probe into a noisy one.
        try:
            built = AsyncRingivo(
                base_url=BASE_URL,
                client_id="cid",
                client_secret="csecret",
                tenant=TENANT,
                scopes=scopes,  # type: ignore[arg-type] - [] and None are the point
            )
        except ValueError as caught:
            return caught
        await built.aclose()
        return None

    unset = await refusal(None)
    empty = await refusal([])

    # Nothing may reach the network to discover this: the refusal is local,
    # and asserting it first keeps "refused" and "asked the server" apart.
    assert token.call_count == 0, "a refused client still reached the mint"
    assert unset is not None, "a client with no scopes was built"
    assert empty is not None, "a client with an empty scope list was built"
    assert "scopes" in str(unset), unset
    assert "fax:read" in str(unset), "the refusal does not name a scope to pass"

    # THE CONTROL: one variable changed — a scope is named — and the same
    # construction works and mints.
    async with AsyncRingivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=["fax:read"],
    ) as client:
        await client.faxes.get(FAX_ID)

    assert token.call_count == 1
    assert _sent(token)["scope"] == "fax:read"


@pytest.mark.anyio
@respx.mock
async def test_one_bare_string_of_scopes_is_refused_rather_than_split_into_characters() -> None:
    """The twin of the sync bypass test, and it has to be written twice.

    A `str` IS a `Sequence[str]`, so `scopes="fax:read"` type-checks and is
    not empty. It becomes eight one-character scopes, which this client
    space-joins into `"f a x : r e a d"` — eight names the platform does
    not publish, in place of the one it does. The mint refuses an unknown
    scope NAME with `invalid_scope`, so the cost is a puzzling 400 about
    names the caller never typed, on whichever line first needed a token.
    Refused at the constructor instead.

    `AsyncRingivo` could lose this check on its own and the sync suite
    would stay green.

    Probed by deleting the `isinstance(scopes, str)` block in
    async_client.py: this test fails at `refused is not None` — "a bare
    string was accepted as a list of scopes".
    """
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))
    refused: BaseException | None = None

    try:
        built = AsyncRingivo(
            base_url=BASE_URL,
            client_id="cid",
            client_secret="csecret",
            tenant=TENANT,
            scopes="fax:read",  # type: ignore[arg-type] - the bypass is the point
        )
    except ValueError as caught:
        refused = caught
    else:
        await built.aclose()

    assert token.call_count == 0, "a refused client still reached the mint"
    assert refused is not None, "a bare string was accepted as a list of scopes"
    assert "not one string" in str(refused), refused
    assert 'scopes=["fax:read"]' in str(refused), "the refusal does not show the fix"

    # THE CONTROL: the same name, in a list, is accepted and reaches the
    # wire whole — one scope, not eight characters space-joined.
    async with AsyncRingivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=["fax:read"],
    ) as client:
        await client.faxes.get(FAX_ID)

    assert _sent(token)["scope"] == "fax:read"
