"""The webhook-endpoint surface, asserted on the WIRE.

Every test here checks the request that went out or the object that came
back, never an internal call — the same discipline as
tests/test_fax_accounts.py, and for the same reason: `list()`'s whole job is
to build a query string, `create()`'s and `update()`'s is to build a JSON:API
document, and none of that is observable from the return value alone.

Two things on this surface get more attention than their fax-account
equivalents, because getting them wrong is expensive rather than merely
wrong:

- THE SECRET. It is readable exactly once per secret — in the answer to the
  create or the rotate that minted it — so a client that dropped it off the
  returned object would lose the only copy, silently, with a 201 in hand.
- `events`. A WRITE requires a non-empty list now — `None` and `[]` are each
  refused locally, before a request exists, on both `create()` and
  `update()` — but a READ can still answer `null` or `[]`, from an endpoint
  registered before the platform tightened this on 2026-09-14. So the write
  guards and the three read states each get their own tests: the read side
  did not change, and collapsing any of its three states would change what a
  caller believes an endpoint hears.
"""

from __future__ import annotations

import json as jsonlib
from datetime import datetime, timezone

import httpx
import pytest
import respx

from ringivo import ApiError, Ringivo, WebhookEndpoint, WebhookEndpointPage

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
ENDPOINTS_URL = f"{BASE_URL}/v1/webhook-endpoints"
ENDPOINT_ID = "0198c4a1-8192-73b4-e5b6-708192031425"
ENDPOINT_URL = f"{ENDPOINTS_URL}/{ENDPOINT_ID}"
ROTATE_URL = f"{ENDPOINT_URL}/rotate-secret"
ACCOUNT_ID = "0198c4a1-3c4d-7e5f-9061-2b3c4d5e6f70"
TENANT = "0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8"
HOOK_URL = "https://hooks.acme-vet.example/faxes"
JSONAPI = "application/vnd.api+json"
SECRET = "whsec_Zm9vYmFyYmF6cXV4MTIzNDU2Nzg5MGFiY2RlZmdo"
NEW_SECRET = "whsec_bmV3c2VjcmV0dmFsdWUwMTIzNDU2Nzg5YWJjZGVm"


@pytest.fixture(autouse=True)
def _token(respx_mock: respx.MockRouter) -> None:
    """Every test here needs a credential to have been minted, not tested.

    respx's own `respx_mock` fixture, rather than the `@respx.mock`
    decorator, because a decorator starts AFTER fixtures run — routes
    registered here would then survive into the next test.
    """
    respx_mock.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "token_type": "Bearer",
                "access_token": "tok",
                "expires_in": 900,
                "scope": "webhooks:read webhooks:write",
                "scopes": ["webhooks:read", "webhooks:write"],
            },
        )
    )


@pytest.fixture
def client() -> Ringivo:
    # The scopes this module's calls need. A `fax:*` token reaches the
    # fax-account-scoped endpoints only, which is a platform rule rather than
    # a client one, so these tests ask for the wider pair.
    return Ringivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=["webhooks:read", "webhooks:write"],
    )


def _endpoint_resource(**attribute_overrides: object) -> dict[str, object]:
    attributes: dict[str, object] = {
        "scopeType": "fax_account",
        "scopeId": ACCOUNT_ID,
        "url": HOOK_URL,
        "events": ["fax.received", "fax.delivered"],
        "active": True,
        "secret": None,
        "secretPreviousExpiresAt": None,
        "createdAt": "2026-08-10T08:00:00.000000Z",
        "updatedAt": "2026-08-10T08:00:00.000000Z",
    }
    attributes.update(attribute_overrides)
    return {"type": "webhook-endpoints", "id": ENDPOINT_ID, "attributes": attributes}


# -- list ------------------------------------------------------------------


def test_list_builds_the_filter_and_page_query(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(ENDPOINTS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    with client:
        client.webhook_endpoints.list(
            scope_type="fax_account",
            scope_id=ACCOUNT_ID,
            active=True,
            page_size=50,
            after="0198c4a1",
        )

    params = route.calls.last.request.url.params

    assert params["filter[scope_type]"] == "fax_account"
    assert params["filter[scope_id]"] == ACCOUNT_ID
    assert params["filter[active]"] == "true"
    assert params["page[size]"] == "50"
    assert params["page[after]"] == "0198c4a1"
    # An unset filter is absent, not empty: `filter[scope_type]=` would be a
    # 400 rather than "no opinion".
    assert "page[before]" not in params
    assert route.calls.last.request.headers["accept"] == JSONAPI


def test_list_sends_active_false_rather_than_dropping_it(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # `False` is a QUESTION — "which endpoints are switched off?" — and it is
    # exactly the value a truthiness check would silently discard, leaving the
    # caller reading every endpoint as if they had asked for nothing.
    route = respx_mock.get(ENDPOINTS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    with client:
        client.webhook_endpoints.list(active=False)

    assert route.calls.last.request.url.params["filter[active]"] == "false"


def test_list_reads_the_endpoints_and_the_next_cursor_from_page_meta(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(ENDPOINTS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [_endpoint_resource()],
                "links": {"next": f"{ENDPOINTS_URL}?page%5Bafter%5D=0198c4a1-next"},
                "meta": {"page": {"size": 25, "nextCursor": "0198c4a1-next"}},
            },
        )
    )

    with client:
        page = client.webhook_endpoints.list()

    assert isinstance(page, WebhookEndpointPage)
    assert len(page) == 1
    assert list(page)[0].id == ENDPOINT_ID
    assert page[0].url == HOOK_URL
    assert page[0].events == ("fax.received", "fax.delivered")
    # No listed endpoint ever carries a secret.
    assert page[0].secret is None
    assert page.next_cursor == "0198c4a1-next"
    assert page.next_url is not None and "page%5Bafter%5D" in page.next_url


def test_the_last_page_has_no_cursor_to_follow(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(ENDPOINTS_URL).mock(
        return_value=httpx.Response(
            200, json={"data": [], "meta": {"page": {"size": 25, "nextCursor": None}}}
        )
    )

    with client:
        page = client.webhook_endpoints.list()

    assert len(page) == 0
    assert page.next_cursor is None
    assert page.next_url is None


# -- get -------------------------------------------------------------------


def test_get_reads_a_jsonapi_document_into_the_public_dataclass(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(ENDPOINT_URL).mock(
        return_value=httpx.Response(200, json={"data": _endpoint_resource()})
    )

    with client:
        endpoint = client.webhook_endpoints.get(ENDPOINT_ID)

    assert isinstance(endpoint, WebhookEndpoint)
    assert endpoint.id == ENDPOINT_ID
    assert endpoint.scope_type == "fax_account"
    assert endpoint.scope_id == ACCOUNT_ID
    assert endpoint.url == HOOK_URL
    assert endpoint.events == ("fax.received", "fax.delivered")
    assert endpoint.active is True
    # A read never carries the secret. None here is the platform saying it
    # holds no readable copy, not a field this client failed to parse.
    assert endpoint.secret is None
    assert endpoint.secret_previous_expires_at is None
    assert endpoint.created_at == datetime(2026, 8, 10, 8, 0, 0, tzinfo=timezone.utc)
    assert endpoint.updated_at == datetime(2026, 8, 10, 8, 0, 0, tzinfo=timezone.utc)
    # The whole resource object is kept, so a member the API adds after this
    # release still reaches the caller.
    assert endpoint.raw["type"] == "webhook-endpoints"


def test_a_null_event_list_is_every_event_rather_than_an_empty_one(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # A WRITE must name at least one event type now, but a READ can still
    # answer either spelling — from a row registered before the platform
    # tightened this, on 2026-09-14 — and the platform treats both as "every
    # event in scope". They stay distinguishable here — None for the null,
    # `()` for the empty list — so `raw` carries the exact shape the read
    # returned rather than this client guessing which one it meant.
    respx_mock.get(ENDPOINT_URL).mock(
        side_effect=[
            httpx.Response(200, json={"data": _endpoint_resource(events=None)}),
            httpx.Response(200, json={"data": _endpoint_resource(events=[])}),
        ]
    )

    with client:
        null_events = client.webhook_endpoints.get(ENDPOINT_ID)
        empty_events = client.webhook_endpoints.get(ENDPOINT_ID)

    assert null_events.events is None
    assert empty_events.events == ()


def test_a_webhook_endpoint_id_stays_inside_its_own_path_segment(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # An id is whatever the caller's own system handed them, and one carrying
    # `/` or `..` must not steer the request at a DIFFERENT endpoint.
    # Asserted on `raw_path`, which is what goes on the wire — `url.path` is
    # a DECODED view and shows the traversal even when the escaping is right.
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(200, json={"data": _endpoint_resource()})
    )

    with client:
        client.webhook_endpoints.get("../faxes/secret")

    assert route.calls.last.request.url.raw_path == b"/v1/webhook-endpoints/..%2Ffaxes%2Fsecret"


def test_an_empty_webhook_endpoint_id_is_refused_by_its_own_name(client: Ringivo) -> None:
    with client, pytest.raises(ValueError, match="a webhook endpoint id is required"):
        client.webhook_endpoints.get("")


def test_an_endpoint_your_token_cannot_reach_raises_a_typed_404(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # A customer- or tenant-scoped endpoint answers 404 to a `fax:*` token,
    # exactly as an id that names nothing does. Both arrive here as the same
    # typed error, which is the platform's intention and not a loss.
    respx_mock.get(ENDPOINT_URL).mock(
        return_value=httpx.Response(
            404,
            json={
                "errors": [
                    {"status": "404", "code": "not_found", "title": "Not found", "detail": "No."}
                ]
            },
        )
    )

    with client, pytest.raises(ApiError) as caught:
        client.webhook_endpoints.get(ENDPOINT_ID)

    assert caught.value.status_code == 404
    assert caught.value.code == "not_found"


# -- create ----------------------------------------------------------------


def test_create_posts_a_jsonapi_document_and_hands_back_the_secret(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.post(ENDPOINTS_URL).mock(
        return_value=httpx.Response(201, json={"data": _endpoint_resource(secret=SECRET)})
    )

    with client:
        endpoint = client.webhook_endpoints.create(
            url=HOOK_URL,
            scope_type="fax_account",
            scope_id=ACCOUNT_ID,
            events=["fax.received", "fax.delivered"],
        )

    request = route.calls.last.request
    body = jsonlib.loads(request.content)

    # The content type is the assertion that matters: httpx stamps
    # `application/json` on a `json=` body, and this surface answers 415 to
    # that. The explicit header wins because httpx only fills in what the
    # caller left unset.
    assert request.headers["content-type"] == JSONAPI
    assert request.headers["accept"] == JSONAPI
    assert body == {
        "data": {
            "type": "webhook-endpoints",
            "attributes": {
                "url": HOOK_URL,
                "scopeType": "fax_account",
                "scopeId": ACCOUNT_ID,
                "events": ["fax.received", "fax.delivered"],
            },
        }
    }
    # The whole point of the call: this is the only copy of the secret that
    # will ever exist outside the signer.
    assert endpoint.secret == SECRET
    assert endpoint.id == ENDPOINT_ID


def test_create_leaves_out_active_when_nobody_named_it(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # `active` is the only member left that can be omitted: `events` is
    # required now, so this test names it and checks the member that is
    # still optional.
    route = respx_mock.post(ENDPOINTS_URL).mock(
        return_value=httpx.Response(201, json={"data": _endpoint_resource(secret=SECRET)})
    )

    with client:
        client.webhook_endpoints.create(
            url=HOOK_URL,
            scope_type="fax_account",
            scope_id=ACCOUNT_ID,
            events=["fax.received"],
        )

    attributes = jsonlib.loads(route.calls.last.request.content)["data"]["attributes"]

    assert attributes == {
        "url": HOOK_URL,
        "scopeType": "fax_account",
        "scopeId": ACCOUNT_ID,
        "events": ["fax.received"],
    }
    assert "active" not in attributes


def test_create_requires_events(client: Ringivo) -> None:
    # No default: a caller who names every OTHER argument but this one meets
    # Python's own refusal, before this client's code runs at all.
    with pytest.raises(TypeError, match="events"):
        client.webhook_endpoints.create(  # type: ignore[call-arg]
            url=HOOK_URL, scope_type="fax_account", scope_id=ACCOUNT_ID
        )


def test_create_refuses_an_empty_event_list_before_sending_anything(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # `[]` used to mean "every event in scope"; the platform refuses it now,
    # so this client refuses it locally rather than spending a round trip on
    # the 422.
    route = respx_mock.post(ENDPOINTS_URL).mock(
        return_value=httpx.Response(201, json={"data": _endpoint_resource(secret=SECRET)})
    )

    with client, pytest.raises(ValueError, match="at least one event type"):
        client.webhook_endpoints.create(
            url=HOOK_URL, scope_type="fax_account", scope_id=ACCOUNT_ID, events=[]
        )

    assert route.call_count == 0
    assert respx_mock.calls.call_count == 0, "an empty event list reached the wire"


def test_create_refuses_a_null_event_list_before_sending_anything(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The other spelling that used to mean "every event in scope". Refused
    # the same way, with the same message, as `[]` above.
    route = respx_mock.post(ENDPOINTS_URL).mock(
        return_value=httpx.Response(201, json={"data": _endpoint_resource(secret=SECRET)})
    )

    with client, pytest.raises(ValueError, match="at least one event type"):
        client.webhook_endpoints.create(
            url=HOOK_URL,
            scope_type="fax_account",
            scope_id=ACCOUNT_ID,
            events=None,  # type: ignore[arg-type]
            active=False,
        )

    assert route.call_count == 0
    assert respx_mock.calls.call_count == 0, "a null event list reached the wire"


def test_create_refuses_an_empty_generator_of_events(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # A one-shot iterator (a generator here) is ALWAYS truthy, whatever it
    # would yield: `not events` on the argument itself cannot tell an empty
    # one from a full one, and would let `create(events=(e for e in []))`
    # sail through to `list(events)` and put `"events": []` on the wire —
    # exactly the value this guard exists to refuse. The list has to be
    # built first, and the emptiness check run on THAT.
    route = respx_mock.post(ENDPOINTS_URL).mock(
        return_value=httpx.Response(201, json={"data": _endpoint_resource(secret=SECRET)})
    )

    with client, pytest.raises(ValueError, match="at least one event type"):
        client.webhook_endpoints.create(
            url=HOOK_URL,
            scope_type="fax_account",
            scope_id=ACCOUNT_ID,
            events=(e for e in ()),  # type: ignore[arg-type]
        )

    assert route.call_count == 0
    assert respx_mock.calls.call_count == 0, "an empty generator of events reached the wire"


def test_a_scope_a_fax_token_may_not_register_is_a_typed_422(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # Naming a customer or tenant scope with a `fax:*` token is refused at
    # registration. A scope you may not use and a scope that does not exist
    # are refused with the SAME message on purpose, so there is nothing to
    # branch on but the status and the code.
    respx_mock.post(ENDPOINTS_URL).mock(
        return_value=httpx.Response(
            422,
            json={
                "errors": [
                    {
                        "status": "422",
                        "code": "validation_failed",
                        "title": "Unprocessable",
                        "detail": "The scope is invalid.",
                        "source": {"pointer": "/data/attributes/scopeType"},
                    }
                ]
            },
        )
    )

    with client, pytest.raises(ApiError) as caught:
        client.webhook_endpoints.create(
            url=HOOK_URL, scope_type="tenant", scope_id=TENANT, events=["fax.received"]
        )

    assert caught.value.status_code == 422
    assert caught.value.errors[0].source == {"pointer": "/data/attributes/scopeType"}


# -- update ----------------------------------------------------------------


def test_update_sends_only_what_was_named(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # THE CASE THIS SURFACE WAS WRAPPED FOR: an integrator registered for
    # `fax.received` alone and then asked why the outbound lifecycle events
    # never arrived. Adding them must not disturb the URL or the switch, and
    # the spec's `url: required` on the PATCH body is the defect noted in
    # webhook_endpoints.py — the server merges over the stored attributes.
    route = respx_mock.patch(ENDPOINT_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": _endpoint_resource(
                    events=["fax.received", "fax.sending", "fax.delivered", "fax.failed"]
                )
            },
        )
    )

    with client:
        endpoint = client.webhook_endpoints.update(
            ENDPOINT_ID, events=["fax.received", "fax.sending", "fax.delivered", "fax.failed"]
        )

    request = route.calls.last.request
    body = jsonlib.loads(request.content)

    assert request.headers["content-type"] == JSONAPI
    assert body["data"]["type"] == "webhook-endpoints"
    # The id travels in the document as well as in the path — a JSON:API
    # PATCH names the resource it is changing, and the raw id goes here while
    # the ESCAPED one goes in the URL.
    assert body["data"]["id"] == ENDPOINT_ID
    assert body["data"]["attributes"] == {
        "events": ["fax.received", "fax.sending", "fax.delivered", "fax.failed"]
    }
    assert "url" not in body["data"]["attributes"]
    assert "active" not in body["data"]["attributes"]
    assert endpoint.events == ("fax.received", "fax.sending", "fax.delivered", "fax.failed")


def test_update_switches_an_endpoint_off_without_touching_its_events(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.patch(ENDPOINT_URL).mock(
        return_value=httpx.Response(200, json={"data": _endpoint_resource(active=False)})
    )

    with client:
        endpoint = client.webhook_endpoints.update(ENDPOINT_ID, active=False)

    attributes = jsonlib.loads(route.calls.last.request.content)["data"]["attributes"]

    assert attributes == {"active": False}
    assert endpoint.active is False


def test_update_never_sends_null_events_whatever_an_untyped_caller_passes(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # `null` USED TO BE A VALUE on this member — "every event in scope" —
    # and the platform answers 422 to it now. The type hint stops a caller
    # who reads it; this is what a caller who does not meets: the key is
    # dropped rather than sent, and a bare `events=None` with nothing else
    # named is the same as naming nothing at all.
    route = respx_mock.patch(ENDPOINT_URL).mock(
        return_value=httpx.Response(200, json={"data": _endpoint_resource(active=False)})
    )

    # BOTH calls happen inside ONE `with`: leaving the block closes the
    # client for good.
    with client:
        with pytest.raises(ValueError, match="at least one member to change"):
            client.webhook_endpoints.update(ENDPOINT_ID, events=None)  # type: ignore[arg-type]

        assert respx_mock.calls.call_count == 0, "a null event list reached the wire"

        # Beside a member that IS sendable, the patch goes out without
        # `events`.
        endpoint = client.webhook_endpoints.update(
            ENDPOINT_ID, events=None, active=False  # type: ignore[arg-type]
        )

    attributes = jsonlib.loads(route.calls.last.request.content)["data"]["attributes"]

    assert attributes == {"active": False}
    assert "events" not in attributes
    assert endpoint.active is False


def test_update_refuses_an_empty_event_list_before_sending_anything(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # `[]` REPLACES the list with nothing, which would reach — one request
    # later — the every-event state a registration refuses. Refused here,
    # unlike `None`, because `[]` is unambiguously a caller asking to change
    # `events` rather than a value that collapses into "not given".
    route = respx_mock.patch(ENDPOINT_URL).mock(
        return_value=httpx.Response(200, json={"data": _endpoint_resource()})
    )

    with client, pytest.raises(ValueError, match="at least one event type"):
        client.webhook_endpoints.update(ENDPOINT_ID, events=[])

    assert route.call_count == 0
    assert respx_mock.calls.call_count == 0, "an empty event list reached the wire"


def test_update_refuses_a_change_that_changes_nothing(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # A PATCH with an empty attributes object is a request the server would
    # accept and act on in no way, spending a round trip and an audit entry
    # to do nothing. It is far more likely a caller building the call from a
    # form that came back empty, so it is refused here, before anything is
    # sent.
    route = respx_mock.patch(ENDPOINT_URL).mock(
        return_value=httpx.Response(200, json={"data": {}})
    )

    with client, pytest.raises(ValueError, match="at least one member to change"):
        client.webhook_endpoints.update(ENDPOINT_ID)

    assert route.call_count == 0
    assert respx_mock.calls.call_count == 0, "an empty update reached the wire"


# -- the bare-string refusal -----------------------------------------------


def test_create_refuses_one_bare_string_of_events_before_sending_anything(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # `events="fax.received"` TYPE-CHECKS: a str is a `Sequence[str]`, and
    # `list()` reads it one character at a time. Sent, it would subscribe the
    # endpoint to twelve one-character event names and earn a 422 naming
    # events the caller never typed — the same failure client.py refuses for
    # `scopes="fax:read"`. It is refused here, before the request exists.
    route = respx_mock.post(ENDPOINTS_URL).mock(
        return_value=httpx.Response(201, json={"data": _endpoint_resource(secret=SECRET)})
    )

    with client, pytest.raises(ValueError, match="not one string"):
        client.webhook_endpoints.create(
            url=HOOK_URL,
            scope_type="fax_account",
            scope_id=ACCOUNT_ID,
            events="fax.received",  # type: ignore[arg-type]
        )

    assert route.call_count == 0
    # Nothing at all went out — not even the token mint.
    assert respx_mock.calls.call_count == 0, "a bare string of events reached the wire"


def test_the_refusal_names_the_fix_rather_than_the_mistake(client: Ringivo) -> None:
    # A caller reading this message must be able to act on it without
    # reading the source, so it carries the corrected call.
    with client, pytest.raises(ValueError) as caught:
        client.webhook_endpoints.create(
            url=HOOK_URL,
            scope_type="fax_account",
            scope_id=ACCOUNT_ID,
            events="fax.received",  # type: ignore[arg-type]
        )

    assert 'events=["fax.received"]' in str(caught.value)


def test_update_refuses_one_bare_string_of_events_before_sending_anything(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The same guard on the other write, because `_events` is the one place
    # that shapes the member and both calls go through it.
    route = respx_mock.patch(ENDPOINT_URL).mock(
        return_value=httpx.Response(200, json={"data": _endpoint_resource()})
    )

    with client, pytest.raises(ValueError, match="not one string"):
        client.webhook_endpoints.update(
            ENDPOINT_ID,
            events="fax.received",  # type: ignore[arg-type]
        )

    assert route.call_count == 0
    assert respx_mock.calls.call_count == 0, "a bare string of events reached the wire"


# -- delete ----------------------------------------------------------------


def test_delete_answers_nothing_and_returns_none(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.delete(ENDPOINT_URL).mock(return_value=httpx.Response(204))

    with client:
        answer = client.webhook_endpoints.delete(ENDPOINT_ID)

    assert answer is None
    assert route.calls.last.request.method == "DELETE"


# -- rotate_secret ---------------------------------------------------------


def test_rotate_secret_posts_no_body_and_returns_the_new_secret(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # A verb, not a PATCH: it mints a credential and starts a clock. The
    # answer is the only place the new secret exists, and
    # `secretPreviousExpiresAt` is the deadline the OLD one stops signing at
    # — during that window a delivery carries two `v1` signatures and
    # `webhooks.verify()` accepts either.
    route = respx_mock.post(ROTATE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": _endpoint_resource(
                    secret=NEW_SECRET,
                    secretPreviousExpiresAt="2026-08-17T08:00:00.000000Z",
                    updatedAt="2026-08-16T08:00:00.000000Z",
                )
            },
        )
    )

    with client:
        endpoint = client.webhook_endpoints.rotate_secret(ENDPOINT_ID)

    request = route.calls.last.request

    assert request.method == "POST"
    assert request.content == b""
    assert request.headers["accept"] == JSONAPI
    assert endpoint.secret == NEW_SECRET
    assert endpoint.secret_previous_expires_at == datetime(
        2026, 8, 17, 8, 0, 0, tzinfo=timezone.utc
    )


def test_rotating_an_endpoint_that_is_not_there_raises_a_typed_404(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.post(ROTATE_URL).mock(
        return_value=httpx.Response(
            404,
            json={
                "errors": [
                    {"status": "404", "code": "not_found", "title": "Not found", "detail": "No."}
                ]
            },
        )
    )

    with client, pytest.raises(ApiError) as caught:
        client.webhook_endpoints.rotate_secret(ENDPOINT_ID)

    assert caught.value.status_code == 404
    assert caught.value.code == "not_found"
