"""The integration-token layer, from the caller's side.

Every test here drives the real request path (`Ringivo.request`) against a
mocked transport, because the token is not a thing a caller ever handles: it
is minted, cached, refreshed and retried on their behalf, and the only
evidence any of that happened is the requests that went out.

The mint is `POST /oauth/token` — one JSON body carrying a
`client_credentials` grant type, the credential, the selectors and a
space-delimited `scope`, and NO `Authorization` header of its own. The
fixtures here are shaped from spec/openapi.yaml's `OauthTokenRequest` and
`OauthTokenResponse`, and `expires_in` is read off the response rather than
assumed, so a platform that shortens the token's life is followed rather
than outlived.

`tenant` AND `scope` ARE BOTH REQUIRED OF THAT BODY, which is what most of
the construction tests below are about. There is no inference behind either:
a mint naming no tenant is refused, and one asking for no scopes is refused,
so this package refuses both on the constructor line rather than buying a
400 on the caller's first call.

THE MINT SPEAKS A DIFFERENT ERROR VOCABULARY FROM THE REST OF THE API, and
that boundary is asserted here rather than assumed: refusals from
`/oauth/token` are RFC 6749's flat `{"error", "error_description"}`, while
every `/v1` resource keeps answering JSON:API `{"errors": [...]}`. Both
reach the caller as `ApiError`, so the tests read the CODE to prove which
parser ran.

THE REFUSALS AND THE COUNTS CARRY THE WEIGHT. An assertion that a call
succeeded passes against an implementation that mints a fresh token every
single time, so the tests that matter are the ones counting how many token
requests were made, and the one proving a 401 is retried exactly ONCE.
"""

from __future__ import annotations

import asyncio
import inspect
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
TOKEN_URL = f"{BASE_URL}/oauth/token"
FAX_URL = f"{BASE_URL}/v1/faxes/0198c4a1-2b3c-7d4e-8f50-1a2b3c4d5e6f"
FAX_ID = "0198c4a1-2b3c-7d4e-8f50-1a2b3c4d5e6f"
TENANT = "0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8"
CUSTOMER = "0198c4a1-6f70-7182-93a4-b5c6d7e8f901"


def _token_response(
    access_token: str = "tok-1",
    expires_in: int | None = 900,
    scopes: Sequence[str] = ("fax:read", "fax:write"),
) -> httpx.Response:
    """The mint's documented 200 — see `OauthTokenResponse` in the spec.

    `expires_in` is a parameter and not a constant on purpose: 900 is what
    the platform issues today, and the client's whole expiry story has to
    follow the number it was told rather than that one.

    BOTH scope members are here because the endpoint sends both: `scope` is
    RFC 6749's space-joined effective set, and `scopes` is the same names as
    an array. They always agree. Only `scopes` is required of the response —
    `scope` is left out rather than sent empty when a token carries none —
    but an integrator can never see that case, because an empty scope set is
    refused at the mint instead of issued.
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

    `application/json`, and NOT a JSON:API document: `/oauth/token` is an
    OAuth token endpoint and answers like one. The `/v1` resources on the
    other side of that boundary keep their `{"errors": [...]}` documents,
    which is why the tests below read `code` rather than only the status.

    `hint` is optional because the platform sends it on some refusals and
    not others — it is the ONLY member that tells the two `invalid_scope`
    causes apart, so a fixture that always carried one would hide the case
    that has none.
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


def _client() -> Ringivo:
    return Ringivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=SCOPES,
    )


@respx.mock
def test_the_mint_is_a_json_post_carrying_the_credential_and_the_tenant() -> None:
    # `POST /oauth/token` is the ONE mint: the endpoint 0.2.x used has been
    # deleted from the platform, so there is no second door to get wrong.
    #
    # The body is asserted WHOLE rather than member by member, because every
    # way of getting it half-right is refused rather than half-obeyed: no
    # `grant_type` is read as some other kind of request, no `tenant` is a
    # 400, and a `scopes` array in place of the `scope` string asks for
    # nothing, which is a 400 as well.
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with _client() as client:
        client.faxes.get(FAX_ID)

    request = token.calls.last.request
    assert request.headers["content-type"] == "application/json"
    assert _sent(token) == {
        "grant_type": "client_credentials",
        "client_id": "cid",
        "client_secret": "csecret",
        "tenant": TENANT,
        "scope": "fax:read fax:write",
    }


@respx.mock
def test_the_mint_request_carries_no_authorization_header() -> None:
    """The credential travels in the BODY, and nothing else may travel with it.

    The mint is the one request in this client that is unauthenticated —
    it is what buys the token every other request carries — so it goes
    through the auth object's own `httpx.Client` rather than the one this
    object is the `auth` of. A bearer attached here would be a token sent
    to buy a token: either stale, or a loop.

    THE PLATFORM NOW ENFORCES THE OTHER HALF OF THIS, which is why the
    assertion is on `Authorization` rather than on `Bearer`. A request
    carrying a `client_secret` in the body while an `Authorization: Basic`
    header carries one too is refused with a 400 `invalid_request` (RFC 6749
    section 2.3) — otherwise the body silently wins, the header goes
    unchecked, and nothing on the wire says which secret was read. This
    client sends its secret exactly one way, and the line below is what says
    so: any `Authorization` header at all on the mint fails it.

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
def test_the_tenant_is_always_sent_and_the_customer_only_when_named() -> None:
    """`customer` is the one selector a body may leave out. `tenant` is not.

    THIS TEST USED TO ASSERT THE OPPOSITE. Until 0.4.0 a client built with
    no tenant sent no `tenant` member, on purpose: the mint resolved an
    absent one to the single active grant behind the credential, and leaving
    the member out was the only spelling that could mean "pick the grant I
    have". The platform deleted that inference — an unnamed tenant is a 400
    `invalid_request` now — so the body that test pinned is a request that
    can no longer succeed.

    A selector still NAMES a grant somebody already wrote and never narrows
    one. What changed is which of the two may be silent.
    """
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with Ringivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        customer=CUSTOMER,
        scopes=SCOPES,
    ) as client:
        client.faxes.get(FAX_ID)

    assert _sent(token)["customer"] == CUSTOMER

    # No customer named. The tenant is STILL on the body — that is the half
    # this test exists for — and the customer is absent rather than null,
    # because the platform reads an omitted `customer` and a null one the
    # same way and one spelling of "nothing" beats two.
    with Ringivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=SCOPES,
    ) as client:
        client.faxes.get(FAX_ID)

    tenant_wide = _sent(token)
    assert "customer" not in tenant_wide, "an unnamed customer was sent anyway"
    assert tenant_wide == {
        "grant_type": "client_credentials",
        "client_id": "cid",
        "client_secret": "csecret",
        "tenant": TENANT,
        "scope": "fax:read fax:write",
    }


@respx.mock
def test_scopes_are_sent_as_one_space_delimited_string_and_not_as_an_array() -> None:
    """`scope`, RFC 6749's spelling — and the array is NOT sent beside it.

    This endpoint does not read the `scopes` array the deleted mint took. A
    body carrying only the array asks for NOTHING, and asking for nothing is
    now refused at the mint — 400 `invalid_scope` — rather than answered
    with a token that authorises nothing.

    So both halves are asserted. Sending the string is one bug away from
    sending both, and sending both is one release away from someone
    trusting the member the platform ignores.
    """
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

    sent = _sent(token)
    assert sent["scope"] == "fax:read fax:write", "the order the caller asked in, space-joined"
    assert "scopes" not in sent, "the deleted mint's array member, which this endpoint ignores"


def test_the_body_builder_leaves_scope_out_rather_than_sending_an_empty_member() -> None:
    # Not reachable through `Ringivo` any more — that constructor refuses an
    # empty scope set outright — so it is asserted at the layer that can
    # still produce it. `ringivo.auth.ClientCredentialsAuth` takes
    # `scopes=None` by default, and an absent member has to stay absent: a
    # `scope: null` or a `scope: ""` on the wire is a different question
    # from asking nothing, and only one of the three is what this means.
    #
    # `grant_type` and `tenant` are NOT optional the same way — the first
    # names the exchange and the second names the grant, and the mint
    # refuses a body missing either — so both are on every body this builder
    # makes. `tenant` has no default here at all, which is why it is passed
    # below rather than left off.
    body = ringivo.auth._token_request_body(
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        customer=None,
        scopes=None,
    )

    assert body == {
        "grant_type": "client_credentials",
        "client_id": "cid",
        "client_secret": "csecret",
        "tenant": TENANT,
    }


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
def test_a_refused_credential_is_the_401_and_it_carries_the_oauth_code() -> None:
    # The mint answers RFC 6749's flat shape, not a JSON:API document. A 401
    # is still an `AuthenticationError` — the subclass is chosen by the
    # STATUS, so the vocabulary change does not move it.
    respx.post(TOKEN_URL).mock(
        return_value=_oauth_error(401, "invalid_client", "Client authentication failed")
    )
    fax = respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with _client() as client, pytest.raises(AuthenticationError) as caught:
        client.faxes.get(FAX_ID)

    assert caught.value.status_code == 401
    assert caught.value.code == "invalid_client"
    assert caught.value.errors[0].detail == "Client authentication failed"
    assert fax.call_count == 0, "a request went out on a token that was never minted"


@respx.mock
def test_a_selector_no_grant_covers_is_a_400_and_it_reaches_the_caller_whole() -> None:
    """Good credentials, no grant — and the answer says no more than that.

    The platform answers the SAME bytes for a tenant nobody granted this
    client and for a customer nobody granted it, deliberately: a message
    that told them apart would let a caller map which of a reseller's
    customers it has been enabled for, one request at a time. So the
    description asserted here is the whole answer the caller gets, and this
    test pins it verbatim rather than by substring — a helpfully more
    specific message from the platform is a REGRESSION, and a substring
    match would sail past it.

    THE STATUS MOVED FROM 403 TO 400 with the mint's OAuth conformance: RFC
    6749 section 5.2 gives the token endpoint 400 for every error but
    `invalid_client`. That is exactly why the assertion a caller should copy
    is `code` and not the status — the status no longer separates this from
    a malformed request, and four different refusals now share it.

    There is nothing for the client to retry, so it does not: the count
    below is what says so.
    """
    token = respx.post(TOKEN_URL).mock(
        return_value=_oauth_error(
            400, "unauthorized_client", "No active integration grant for this tenant."
        )
    )
    fax = respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with _client() as client, pytest.raises(ApiError) as caught:
        client.faxes.get(FAX_ID)

    assert caught.value.status_code == 400
    assert caught.value.code == "unauthorized_client"
    assert caught.value.errors[0].detail == "No active integration grant for this tenant."
    assert token.call_count == 1, "the client tried again at an endpoint that had said no"
    assert fax.call_count == 0


@pytest.mark.parametrize(
    ("status", "error", "description"),
    [
        # A selector that is not a uuid, or a customer with no tenant beside
        # it. This is a bug in the caller's configuration and says so.
        (
            400,
            "invalid_request",
            "The tenant and customer selectors must be UUIDs, and customer requires a tenant.",
        ),
        # No tenant at all. Unreachable through this package's constructors,
        # which is the point of them — but it is the refusal a caller who
        # writes the mint by hand meets first, and it must arrive readable
        # rather than as a bare 400.
        (
            400,
            "invalid_request",
            "The tenant parameter is required.",
        ),
        # Two secrets on one request — a `client_secret` in the body while
        # an `Authorization: Basic` header carries one too (RFC 6749 section
        # 2.3). This client sends exactly one, which is asserted directly in
        # test_the_mint_request_carries_no_authorization_header.
        (
            400,
            "invalid_request",
            "Only one authentication method may be used per request.",
        ),
        # A scope NAME the platform does not publish — a typo, refused
        # loudly. A scope the platform knows but the grant does not carry is
        # DROPPED instead, silently, as long as something else survives.
        (400, "invalid_scope", "The requested scope is invalid, unknown, or malformed"),
        # The empty intersection: every scope asked for was dropped and
        # nothing is left. Refused rather than issued, because a token that
        # authorises nothing only moves the failure somewhere harder to read.
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
@respx.mock
def test_the_mints_other_refusals_arrive_typed_and_carry_their_code(
    status: int, error: str, description: str
) -> None:
    """The rest of the mint's vocabulary, each reaching the caller intact.

    `code` is what a caller branches on, so `code` is what is asserted. The
    status cannot do it: RFC 6749 section 5.2 gives the token endpoint one
    status for every refusal but a bad credential, so ALL FIVE of these are
    400 and two pairs even share a `code`.
    """
    token = respx.post(TOKEN_URL).mock(return_value=_oauth_error(status, error, description))
    fax = respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with _client() as client, pytest.raises(ApiError) as caught:
        client.faxes.get(FAX_ID)

    assert caught.value.status_code == status
    assert caught.value.code == error
    assert caught.value.errors[0].detail == description
    # A refusal about the request is not a token problem, so nothing is
    # re-minted and nothing is spent on the resource.
    assert token.call_count == 1
    assert fax.call_count == 0


@respx.mock
def test_the_two_invalid_scope_causes_are_told_apart_by_the_hint_this_client_keeps() -> None:
    """One `code`, two causes — and the member that separates them survives.

    `invalid_scope` answers a scope NAME the platform does not publish (a
    typo, which carries a `hint` naming the offender) and an intersection
    that came out EMPTY (a permission answer, which carries none). A caller
    has to tell those apart: the first is fixed by correcting a string, the
    second by asking their reseller for a grant.

    Nothing in this package's typed surface has a field for `hint` — it is
    not a JSON:API member and `ApiErrorDetail` invents nothing — so the
    whole document is kept on `raw` and this is what proves it reaches a
    caller. Asserting the ABSENCE on the second refusal is the half that
    matters: a parser that defaulted a missing `hint` to something would
    make the two causes indistinguishable again.
    """
    respx.post(TOKEN_URL).mock(
        return_value=_oauth_error(
            400,
            "invalid_scope",
            "The requested scope is invalid, unknown, or malformed",
            hint="fax:reed",
        )
    )

    with _client() as client, pytest.raises(ApiError) as typo:
        client.faxes.get(FAX_ID)

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

    with _client() as client, pytest.raises(ApiError) as nothing_survived:
        client.faxes.get(FAX_ID)

    assert nothing_survived.value.code == "invalid_scope"
    assert "hint" not in nothing_survived.value.errors[0].raw, (
        "a hint was invented for the refusal that does not carry one, which is the only "
        "thing telling these two causes apart"
    )


@respx.mock
def test_the_mints_message_names_the_error_once_and_then_says_what_happened() -> None:
    """The line an operator reads out of a log, and it used to stutter.

    `_message` brackets the machine code ahead of the text, so folding the
    OAuth `error` into BOTH `title` and `code` rendered every mint refusal
    as "HTTP 400 [unauthorized_client]: unauthorized_client No active…".
    The name belongs in one place.

    Probed by restoring `title=oauth_error` in errors.py: this test fails on
    the equality below, showing the doubled name.
    """
    respx.post(TOKEN_URL).mock(
        return_value=_oauth_error(
            400, "unauthorized_client", "No active integration grant for this tenant."
        )
    )

    with _client() as client, pytest.raises(ApiError) as caught:
        client.faxes.get(FAX_ID)

    assert str(caught.value) == (
        "HTTP 400 [unauthorized_client]: No active integration grant for this tenant."
    )


@respx.mock
def test_a_throttled_mint_reaches_the_caller_rather_than_being_retried() -> None:
    """429, and the client does NOT try again — it has no budget to spend.

    The mint is throttled harder than the rest of the API because every
    attempt costs a password check: 60 a minute per IP address and 20 a
    minute per client id, whichever is reached first. A client that
    answered a 429 with another mint would spend the rest of the budget
    proving it.

    The body is deliberately NEITHER vocabulary and is not even JSON — a
    throttle answers before the mint runs, so what comes back is the
    framework's own rate-limit page, as HTML, whatever the request asked to
    accept. What the parser does with a body it cannot read at all matters
    here: it must still raise, still carry the status, and still put the
    body in front of the caller rather than swallowing it.
    """
    token = respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            429,
            html="<!DOCTYPE html><title>Too Many Attempts.</title>",
            headers={"Retry-After": "42"},
        )
    )
    fax = respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    with _client() as client, pytest.raises(ApiError) as caught:
        client.faxes.get(FAX_ID)

    assert caught.value.status_code == 429
    assert caught.value.code is None, "no OAuth code was sent, so none may be invented"
    assert caught.value.errors == (), "an HTML page was read as a refusal document"
    assert "Too Many Attempts." in str(caught.value), "the body never reached the caller"
    assert token.call_count == 1, "a throttled client asked again"
    assert fax.call_count == 0


@respx.mock
def test_the_mint_and_the_resources_speak_different_error_vocabularies() -> None:
    """THE BOUNDARY, asserted from both sides in one test.

    The consolidation moved the mint onto an OAuth token endpoint, and an
    OAuth token endpoint answers RFC 6749's flat shape. Everything under
    `/v1` kept its JSON:API documents. One parser reads both, and it decides
    by what the BODY carries rather than by which URL was called.

    Written as one test because the property is a RELATIONSHIP: two
    separate tests each pass against a client that had quietly stopped
    parsing the other shape. Here the same `code` accessor is read on both
    sides, so a parser that lost either vocabulary reports None on one of
    these lines.
    """
    respx.post(TOKEN_URL).mock(return_value=_oauth_error(401, "invalid_client", "no"))

    with _client() as client, pytest.raises(AuthenticationError) as at_the_mint:
        client.faxes.get(FAX_ID)

    # The mint's side: a flat OAuth refusal, and `code` is RFC 6749's error.
    assert at_the_mint.value.code == "invalid_client"
    assert at_the_mint.value.errors[0].source is None, "an OAuth refusal has no JSON:API source"

    # The resource side: the mint succeeds, and the FAX refuses with a
    # JSON:API document carrying members the flat shape has no room for.
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

    with _client() as client, pytest.raises(ApiError) as at_the_resource:
        client.faxes.get(FAX_ID)

    assert at_the_resource.value.code == "validation_failed"
    assert at_the_resource.value.errors[0].source == {"parameter": "to"}
    assert at_the_resource.value.errors[0].title == "Unprocessable Entity"


@respx.mock
def test_a_refusal_carrying_members_this_client_never_heard_of_still_parses() -> None:
    # Tolerated, not refused: the mint may grow a member. `hint` is already
    # one it sends — see the invalid_scope pair above — and `error_uri` is
    # RFC 6749's, which this platform does not send today. A parser that
    # insisted on the members it knew would turn a routine platform addition
    # into a client that cannot read any refusal at all.
    respx.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            400,
            json={
                "error": "unauthorized_client",
                "error_description": "No active integration grant for this tenant.",
                "hint": "something the platform added later",
                "error_uri": "https://example.invalid/errors/unauthorized_client",
            },
        )
    )

    with _client() as client, pytest.raises(ApiError) as caught:
        client.faxes.get(FAX_ID)

    assert caught.value.code == "unauthorized_client"
    assert caught.value.errors[0].detail == "No active integration grant for this tenant."
    # The unknown members are not dropped on the floor — `raw` is the whole
    # document, so a caller can read a member this release has never heard of.
    assert caught.value.errors[0].raw["hint"] == "something the platform added later"


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

    That is reachable, not theoretical: this object is reachable as
    `client._auth`, and a caller who wants an endpoint the wrapper does not
    cover has every reason to reach for it — `Ringivo.request` is the
    supported way to do that, and handing the SYNC auth object to an
    `httpx.AsyncClient` is the mistake next door to it.

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
            base_url=BASE_URL,
            client_id="cid",
            client_secret="csecret",
            tenant=TENANT,
            scopes=SCOPES,
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
    with Ringivo(
        base_url=f"{BASE_URL}/", client_id="c", client_secret="s", tenant=TENANT, scopes=SCOPES
    ) as client:
        assert client.base_url == BASE_URL

    with pytest.raises(ValueError):
        Ringivo(base_url="", client_id="c", client_secret="s", tenant=TENANT, scopes=SCOPES)


@respx.mock
def test_a_client_that_names_no_tenant_is_refused_before_anything_is_built() -> None:
    """The inference is gone, so the argument that replaced it is REQUIRED.

    THE OPPOSITE OF WHAT THIS SUITE USED TO PROVE. Through 0.3.x a client
    built with no tenant was legal and sent no `tenant` member, because the
    mint resolved an absent one to the single active grant behind the
    credential. That convenience planted a failure for a future unrelated
    event — the day the reseller granted the client a SECOND tenant, an
    integration nobody had touched started answering 400 — so the platform
    deleted it, and this package makes the omission unrepresentable rather
    than merely discouraged.

    TWO GUARDS, AND THEY CATCH DIFFERENT MISTAKES — which is why the
    signature is asserted separately from the behaviour. Omitting the
    argument is a `TypeError` from Python, and a type checker says so before
    anything runs. Passing an EMPTY string is not — it type-checks
    perfectly — and the mint reads a valueless parameter as an absent one
    (RFC 6749 section 3.2), so it is refused here with a `ValueError`.

    The signature assertion is the half a runtime probe CANNOT see. Restore
    `tenant: str | None = None` and the omitted construction still raises,
    because the emptiness guard below catches `None` too — just later, and
    as the wrong class. So "this test goes red" would not have meant "the
    argument is still required", and the check that does mean it is the
    first one.

    Probed all three ways: restoring the default fails the signature
    assertion by name; deleting the `if not tenant` block fails the
    empty-string assertion; and making the signature required while the
    guard is gone still passes, which is correct — that combination refuses
    both inputs.
    """
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    assert inspect.signature(Ringivo).parameters["tenant"].default is inspect.Parameter.empty, (
        "tenant has a default again, so a caller can omit it and their type checker agrees"
    )

    omitted: BaseException | None = None
    try:
        built = Ringivo(  # type: ignore[call-arg] - the missing argument is the point
            base_url=BASE_URL,
            client_id="cid",
            client_secret="csecret",
            scopes=SCOPES,
        )
    except (TypeError, ValueError) as caught:
        omitted = caught
    else:
        built.close()

    empty: BaseException | None = None
    try:
        built = Ringivo(
            base_url=BASE_URL,
            client_id="cid",
            client_secret="csecret",
            tenant="",
            scopes=SCOPES,
        )
    except ValueError as caught:
        empty = caught
    else:
        built.close()

    # Nothing may reach the network to discover either: the refusal is
    # local, and asserting it first keeps "refused" and "asked the server"
    # apart.
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
    with Ringivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=SCOPES,
    ) as client:
        client.faxes.get(FAX_ID)

    assert token.call_count == 1
    assert _sent(token)["tenant"] == TENANT


@respx.mock
def test_a_client_that_asks_for_no_scopes_is_refused_at_construction() -> None:
    """A scopeless client has no working call in it, so it is not built.

    The token carries what it asked for, intersected with the grant behind
    the credential. Ask for nothing and that intersection is empty, and the
    mint refuses an empty one: 400 `invalid_scope`, because a token that
    authorises nothing would only move the failure to the first route it
    was spent on.

    Refused on the constructor line instead, while the missing argument is
    on screen. None and [] are the same mistake and both are refused; the
    CONTROL underneath is what proves the guard rejects the empty question
    rather than every question.

    Probed by deleting the `if not scopes` block in client.py: this test
    fails at `unset is not None` with "a client with no scopes was built".
    """
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))

    def refusal(scopes: object) -> BaseException | None:
        # Closed rather than leaked when the guard is gone: an unclosed
        # httpx.Client would turn a failing probe into a noisy one.
        try:
            built = Ringivo(
                base_url=BASE_URL,
                client_id="cid",
                client_secret="csecret",
                tenant=TENANT,
                scopes=scopes,  # type: ignore[arg-type] - [] and None are the point
            )
        except ValueError as caught:
            return caught
        built.close()
        return None

    unset = refusal(None)
    empty = refusal([])

    # Nothing may reach the network to discover this: the refusal is local,
    # and asserting it first keeps "refused" and "asked the server" apart.
    assert token.call_count == 0, "a refused client still reached the mint"
    assert unset is not None, "a client with no scopes was built"
    assert empty is not None, "a client with an empty scope list was built"
    assert "scopes" in str(unset), unset
    assert "fax:read" in str(unset), "the refusal does not name a scope to pass"

    # THE CONTROL: one variable changed — a scope is named — and the same
    # construction works and mints.
    with Ringivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=["fax:read"],
    ) as client:
        client.faxes.get(FAX_ID)

    assert token.call_count == 1
    assert _sent(token)["scope"] == "fax:read"


@respx.mock
def test_one_bare_string_of_scopes_is_refused_rather_than_split_into_characters() -> None:
    """The guard above, walked past by a caller who wrote `scopes="fax:read"`.

    A `str` IS a `Sequence[str]`: the annotation accepts it, pyright is
    happy, and it is not empty. `tuple("fax:read")` is eight one-character
    scopes, which this client space-joins into the `scope` string
    `"f a x : r e a d"` — eight names the platform does not publish, in
    place of the one it does.

    The mint refuses an unknown scope NAME loudly, with `invalid_scope`, so
    the cost of this bug is not a silent scopeless token: it is a 400 about
    scope names the caller never typed, on whichever line first happened to
    need one. Refused at the constructor instead, while the offending
    argument is still on screen.

    Probed by deleting the `isinstance(scopes, str)` block in client.py:
    this test fails at `refused is not None` — "a bare string was accepted
    as a list of scopes".
    """
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    respx.get(FAX_URL).mock(return_value=httpx.Response(200, json=_fax_document()))
    refused: BaseException | None = None

    try:
        built = Ringivo(
            base_url=BASE_URL,
            client_id="cid",
            client_secret="csecret",
            tenant=TENANT,
            scopes="fax:read",  # type: ignore[arg-type] - the bypass is the point
        )
    except ValueError as caught:
        refused = caught
    else:
        built.close()

    assert token.call_count == 0, "a refused client still reached the mint"
    assert refused is not None, "a bare string was accepted as a list of scopes"
    assert "not one string" in str(refused), refused
    assert 'scopes=["fax:read"]' in str(refused), "the refusal does not show the fix"

    # THE CONTROL: the same name, in a list, is accepted and reaches the
    # wire whole — one scope, not eight characters space-joined.
    with Ringivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=["fax:read"],
    ) as client:
        client.faxes.get(FAX_ID)

    assert _sent(token)["scope"] == "fax:read"


@respx.mock
def test_request_is_a_public_escape_hatch_that_carries_the_credential() -> None:
    """The unwrapped-endpoint path, and why it lost its underscore in 0.2.2.

    Before 0.2.2 there was no public way to reach an endpoint the fax
    wrapper does not cover, so a caller who needed one reached for
    `_request` — a private name this package never promised to keep, or
    for the vendored generated client, which could not authenticate itself.
    Both are gone. What this pins is the PROMISE rather than the plumbing:
    the public name exists, a call through it goes out authenticated
    exactly like a wrapped one, and a refusal comes back as this package's
    typed error rather than a status code the caller must remember to
    check.

    `/v1/webhook-endpoints` is deliberately an endpoint this client does
    NOT wrap. A route the wrapper already covers would exercise the
    transport but prove nothing about the hatch.
    """
    token = respx.post(TOKEN_URL).mock(return_value=_token_response())
    listing = respx.get(f"{BASE_URL}/v1/webhook-endpoints").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    with _client() as client:
        response = client.request("GET", "/v1/webhook-endpoints")

        assert response.status_code == 200
        assert response.json() == {"data": []}
        assert token.call_count == 1
        sent = listing.calls.last.request
        assert sent.headers["authorization"] == "Bearer tok-1"
        assert sent.headers["accept"] == "application/vnd.api+json"
        assert sent.headers["user-agent"] == f"Ringivo/Python {ringivo.__version__}"

        # The same object under both names, so a caller who reached for the
        # private one before 0.2.2 is not broken by the promotion.
        assert Ringivo.request is Ringivo._request

        # And the refusal half of the promise: past the boundary the body is
        # the API's own, but the FAILURE is still this package's.
        respx.get(f"{BASE_URL}/v1/webhook-deliveries").mock(
            return_value=httpx.Response(403, json={"errors": [{"detail": "no"}]})
        )
        with pytest.raises(ApiError) as refused:
            client.request("GET", "/v1/webhook-deliveries")
        assert refused.value.status_code == 403
