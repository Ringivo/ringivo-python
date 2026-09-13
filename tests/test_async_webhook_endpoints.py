"""The webhook-endpoint surface again, awaited, and asserted on the WIRE.

The mirror of tests/test_webhook_endpoints.py. `AsyncWebhookEndpoints` is a
sibling of `WebhookEndpoints` rather than a wrapper around it, so the
documents it builds and the query strings it writes are its own code and get
their own assertions — the three `events` states and the once-only secret
included, because those are the two places where being wrong costs a caller
something they cannot get back.
"""

from __future__ import annotations

import json as jsonlib
from datetime import datetime, timezone

import httpx
import pytest
import respx

from ringivo import ApiError, AsyncRingivo, WebhookEndpoint, WebhookEndpointPage

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
    """Every test here needs a credential to have been minted, not tested."""
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
def client() -> AsyncRingivo:
    return AsyncRingivo(
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


@pytest.mark.anyio
async def test_list_builds_the_filter_and_page_query(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.get(ENDPOINTS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    async with client:
        page = await client.webhook_endpoints.list(
            scope_type="customer", scope_id=ACCOUNT_ID, active=False, page_size=50
        )

    params = route.calls.last.request.url.params

    assert isinstance(page, WebhookEndpointPage)
    assert params["filter[scope_type]"] == "customer"
    assert params["filter[scope_id]"] == ACCOUNT_ID
    # `False` is a question, not an omission: "which endpoints are off?".
    assert params["filter[active]"] == "false"
    assert params["page[size]"] == "50"
    assert "page[after]" not in params


@pytest.mark.anyio
async def test_get_reads_a_jsonapi_document_into_the_public_dataclass(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.get(ENDPOINT_URL).mock(
        return_value=httpx.Response(200, json={"data": _endpoint_resource()})
    )

    async with client:
        endpoint = await client.webhook_endpoints.get(ENDPOINT_ID)

    assert isinstance(endpoint, WebhookEndpoint)
    assert endpoint.scope_type == "fax_account"
    assert endpoint.events == ("fax.received", "fax.delivered")
    assert endpoint.active is True
    assert endpoint.secret is None
    assert endpoint.created_at == datetime(2026, 8, 10, 8, 0, 0, tzinfo=timezone.utc)


@pytest.mark.anyio
async def test_a_webhook_endpoint_id_stays_inside_its_own_path_segment(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(200, json={"data": _endpoint_resource()})
    )

    async with client:
        await client.webhook_endpoints.get("../faxes/secret")

    assert route.calls.last.request.url.raw_path == b"/v1/webhook-endpoints/..%2Ffaxes%2Fsecret"


@pytest.mark.anyio
async def test_create_posts_a_jsonapi_document_and_hands_back_the_secret(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.post(ENDPOINTS_URL).mock(
        return_value=httpx.Response(201, json={"data": _endpoint_resource(secret=SECRET)})
    )

    async with client:
        endpoint = await client.webhook_endpoints.create(
            url=HOOK_URL,
            scope_type="fax_account",
            scope_id=ACCOUNT_ID,
            events=["fax.received"],
        )

    request = route.calls.last.request
    body = jsonlib.loads(request.content)

    assert request.headers["content-type"] == JSONAPI
    assert body == {
        "data": {
            "type": "webhook-endpoints",
            "attributes": {
                "url": HOOK_URL,
                "scopeType": "fax_account",
                "scopeId": ACCOUNT_ID,
                "events": ["fax.received"],
            },
        }
    }
    assert endpoint.secret == SECRET


@pytest.mark.anyio
async def test_create_keeps_the_three_event_states_apart(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    # Absent, `[]` and `null` are three different requests: leave it to the
    # platform, every event in scope written as an empty list, every event in
    # scope written as null. BOTH calls happen inside ONE `async with`:
    # leaving the block closes the client for good.
    route = respx_mock.post(ENDPOINTS_URL).mock(
        side_effect=[
            httpx.Response(201, json={"data": _endpoint_resource(secret=SECRET)}),
            httpx.Response(201, json={"data": _endpoint_resource(events=[], secret=SECRET)}),
            httpx.Response(201, json={"data": _endpoint_resource(events=None, secret=SECRET)}),
        ]
    )

    async with client:
        await client.webhook_endpoints.create(
            url=HOOK_URL, scope_type="fax_account", scope_id=ACCOUNT_ID
        )
        empty = await client.webhook_endpoints.create(
            url=HOOK_URL, scope_type="fax_account", scope_id=ACCOUNT_ID, events=[]
        )
        cleared = await client.webhook_endpoints.create(
            url=HOOK_URL, scope_type="fax_account", scope_id=ACCOUNT_ID, events=None
        )

    unnamed, listed, nulled = (
        jsonlib.loads(call.request.content)["data"]["attributes"] for call in route.calls
    )

    assert "events" not in unnamed
    assert listed["events"] == []
    assert nulled["events"] is None
    assert empty.events == ()
    assert cleared.events is None


@pytest.mark.anyio
async def test_update_sends_only_what_was_named(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.patch(ENDPOINT_URL).mock(
        return_value=httpx.Response(
            200, json={"data": _endpoint_resource(events=["fax.received", "fax.failed"])}
        )
    )

    async with client:
        endpoint = await client.webhook_endpoints.update(
            ENDPOINT_ID, events=["fax.received", "fax.failed"]
        )

    body = jsonlib.loads(route.calls.last.request.content)

    assert body["data"]["id"] == ENDPOINT_ID
    assert body["data"]["attributes"] == {"events": ["fax.received", "fax.failed"]}
    assert endpoint.events == ("fax.received", "fax.failed")


@pytest.mark.anyio
async def test_update_refuses_a_change_that_changes_nothing(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    async with client:
        with pytest.raises(ValueError, match="at least one member to change"):
            await client.webhook_endpoints.update(ENDPOINT_ID)

    assert respx_mock.calls.call_count == 0, "an empty update reached the wire"


@pytest.mark.anyio
async def test_both_writes_refuse_one_bare_string_of_events_before_sending_anything(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    # `events="fax.received"` type-checks and would ask for twelve
    # one-character event names. The guard lives in `_events`, which this
    # class imports rather than copies, so both writes inherit it — asserted
    # here rather than assumed, because a shared helper reached through two
    # call sites is two chances to have wired it up wrongly.
    #
    # BOTH calls happen inside ONE `async with`: leaving the block closes the
    # client for good.
    respx_mock.post(ENDPOINTS_URL).mock(return_value=httpx.Response(201, json={"data": {}}))
    respx_mock.patch(ENDPOINT_URL).mock(return_value=httpx.Response(200, json={"data": {}}))

    async with client:
        with pytest.raises(ValueError, match="not one string") as created:
            await client.webhook_endpoints.create(
                url=HOOK_URL,
                scope_type="fax_account",
                scope_id=ACCOUNT_ID,
                events="fax.received",  # type: ignore[arg-type]
            )

        with pytest.raises(ValueError, match="not one string"):
            await client.webhook_endpoints.update(
                ENDPOINT_ID,
                events="fax.received",  # type: ignore[arg-type]
            )

    assert 'events=["fax.received"]' in str(created.value)
    assert respx_mock.calls.call_count == 0, "a bare string of events reached the wire"


@pytest.mark.anyio
async def test_delete_returns_none_and_surfaces_an_unreachable_endpoint_as_404(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    # BOTH calls happen inside ONE `async with`: leaving the block closes the
    # client for good, so a second one would meet a closed transport rather
    # than the refusal this test is about. The two answers are queued on the
    # route instead — 204 first, then the 404 a scope you cannot reach gets.
    respx_mock.delete(ENDPOINT_URL).mock(
        side_effect=[
            httpx.Response(204),
            httpx.Response(
                404,
                json={
                    "errors": [
                        {
                            "status": "404",
                            "code": "not_found",
                            "title": "Not found",
                            "detail": "No.",
                        }
                    ]
                },
            ),
        ]
    )

    async with client:
        assert await client.webhook_endpoints.delete(ENDPOINT_ID) is None

        with pytest.raises(ApiError) as caught:
            await client.webhook_endpoints.delete(ENDPOINT_ID)

    assert caught.value.status_code == 404
    assert caught.value.code == "not_found"


@pytest.mark.anyio
async def test_rotate_secret_posts_no_body_and_returns_the_new_secret(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.post(ROTATE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": _endpoint_resource(
                    secret=NEW_SECRET, secretPreviousExpiresAt="2026-08-17T08:00:00.000000Z"
                )
            },
        )
    )

    async with client:
        endpoint = await client.webhook_endpoints.rotate_secret(ENDPOINT_ID)

    request = route.calls.last.request

    assert request.method == "POST"
    assert request.content == b""
    assert request.headers["accept"] == JSONAPI
    assert endpoint.secret == NEW_SECRET
    assert endpoint.secret_previous_expires_at == datetime(
        2026, 8, 17, 8, 0, 0, tzinfo=timezone.utc
    )
