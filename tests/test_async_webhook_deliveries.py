"""The webhook-delivery surface again, awaited, and asserted on the WIRE.

The mirror of tests/test_webhook_deliveries.py. `AsyncWebhookDeliveries` is a
sibling of `WebhookDeliveries` rather than a wrapper around it, so the query
strings it writes are its own code and get their own assertions.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
import respx

from ringivo import ApiError, AsyncRingivo, WebhookDelivery, WebhookDeliveryPage

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
DELIVERIES_URL = f"{BASE_URL}/v1/webhook-deliveries"
DELIVERY_ID = "0198c4a1-9203-74c5-f6c7-819203142536"
DELIVERY_URL = f"{DELIVERIES_URL}/{DELIVERY_ID}"
ENDPOINT_ID = "0198c4a1-8192-73b4-e5b6-708192031425"
EVENT_ID = "0198c4a1-a314-75d6-07d8-92031425364a"
DIGEST = "e" * 64
TENANT = "0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8"


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
                "scope": "webhooks:read",
                "scopes": ["webhooks:read"],
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
        scopes=["webhooks:read"],
    )


def _delivery_resource(**attribute_overrides: object) -> dict[str, object]:
    attributes: dict[str, object] = {
        "eventId": EVENT_ID,
        "eventType": "fax.received",
        "payloadSha256": DIGEST,
        "status": "dead",
        "attemptNo": 7,
        "statusCode": 500,
        "durationMs": 812,
        "error": None,
        "nextAttemptAt": None,
        "deliveredAt": None,
        "deadAt": "2026-08-16T19:45:00.000000Z",
        "createdAt": "2026-08-16T11:02:31.000000Z",
        "updatedAt": "2026-08-16T19:45:00.000000Z",
    }
    attributes.update(attribute_overrides)
    return {
        "type": "webhook-deliveries",
        "id": DELIVERY_ID,
        "attributes": attributes,
        "relationships": {"endpoint": {"data": {"type": "webhook-endpoints", "id": ENDPOINT_ID}}},
    }


@pytest.mark.anyio
async def test_list_builds_the_filter_and_page_query(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.get(DELIVERIES_URL).mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    async with client:
        page = await client.webhook_deliveries.list(
            endpoint=ENDPOINT_ID, event_type="fax.delivered", status="pending", page_size=100
        )

    params = route.calls.last.request.url.params

    assert isinstance(page, WebhookDeliveryPage)
    assert params["filter[endpoint]"] == ENDPOINT_ID
    assert params["filter[event_type]"] == "fax.delivered"
    assert params["filter[status]"] == "pending"
    assert params["page[size]"] == "100"
    assert "page[after]" not in params


@pytest.mark.anyio
async def test_list_reads_what_an_outage_cost_you(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    # `status="dead"` is the query this collection exists for, and the page it
    # answers with is the only list of what was given up on.
    respx_mock.get(DELIVERIES_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [_delivery_resource()],
                "meta": {"page": {"size": 25, "nextCursor": None}},
            },
        )
    )

    async with client:
        page = await client.webhook_deliveries.list(status="dead")

    assert len(page) == 1
    assert page[0].status == "dead"
    assert page[0].event_id == EVENT_ID
    assert page.next_cursor is None


@pytest.mark.anyio
async def test_get_reads_a_jsonapi_document_into_the_public_dataclass(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.get(DELIVERY_URL).mock(
        return_value=httpx.Response(200, json={"data": _delivery_resource()})
    )

    async with client:
        delivery = await client.webhook_deliveries.get(DELIVERY_ID)

    assert isinstance(delivery, WebhookDelivery)
    assert delivery.endpoint_id == ENDPOINT_ID
    assert delivery.payload_sha256 == DIGEST
    assert delivery.attempt_no == 7
    assert delivery.status_code == 500
    assert delivery.dead_at == datetime(2026, 8, 16, 19, 45, 0, tzinfo=timezone.utc)


@pytest.mark.anyio
async def test_a_webhook_delivery_id_stays_inside_its_own_path_segment(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(200, json={"data": _delivery_resource()})
    )

    async with client:
        await client.webhook_deliveries.get("../faxes/secret")

    assert route.calls.last.request.url.raw_path == b"/v1/webhook-deliveries/..%2Ffaxes%2Fsecret"


@pytest.mark.anyio
async def test_a_delivery_that_is_not_there_raises_a_typed_404(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.get(DELIVERY_URL).mock(
        return_value=httpx.Response(
            404,
            json={
                "errors": [
                    {"status": "404", "code": "not_found", "title": "Not found", "detail": "No."}
                ]
            },
        )
    )

    async with client:
        with pytest.raises(ApiError) as caught:
            await client.webhook_deliveries.get(DELIVERY_ID)

    assert caught.value.status_code == 404
    assert caught.value.code == "not_found"
