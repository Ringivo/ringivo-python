"""The webhook-delivery surface, asserted on the WIRE.

Read-only, two methods, and the same discipline as the fax-account tests:
`list()`'s whole job is to build a query string, and that is not observable
from the return value.

What is worth asserting beyond the query is the READING of the collection. It
is evidence of failure and not a history — a delivery that lands leaves no
row — so an empty page is the good news, `status` is `pending` or `dead` and
nothing else, and `delivered` is a 400 rather than an empty result. A test
that treated the empty page as "nothing to see" would have nothing to say
about any of that.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
import respx

from ringivo import ApiError, Ringivo, WebhookDelivery, WebhookDeliveryPage

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
DELIVERIES_URL = f"{BASE_URL}/v1/webhook-deliveries"
DELIVERY_ID = "0198c4a1-9203-74c5-f6c7-819203142536"
DELIVERY_URL = f"{DELIVERIES_URL}/{DELIVERY_ID}"
ENDPOINT_ID = "0198c4a1-8192-73b4-e5b6-708192031425"
EVENT_ID = "0198c4a1-a314-75d6-07d8-92031425364a"
DIGEST = "e" * 64
TENANT = "0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8"
JSONAPI = "application/vnd.api+json"


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
def client() -> Ringivo:
    # Reads only: this whole surface is read-only, and a delivery borrows its
    # endpoint's reach, so `webhooks:read` is what reaches all of them.
    return Ringivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=["webhooks:read"],
    )


def _delivery_resource(
    *, relationships: dict[str, object] | None = None, **attribute_overrides: object
) -> dict[str, object]:
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
        "relationships": (
            relationships
            if relationships is not None
            else {"endpoint": {"data": {"type": "webhook-endpoints", "id": ENDPOINT_ID}}}
        ),
    }


# -- list ------------------------------------------------------------------


def test_list_builds_the_filter_and_page_query(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(DELIVERIES_URL).mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    with client:
        client.webhook_deliveries.list(
            endpoint=ENDPOINT_ID,
            event_type="fax.received",
            status="dead",
            page_size=100,
            after="0198c4a1",
        )

    params = route.calls.last.request.url.params

    assert params["filter[endpoint]"] == ENDPOINT_ID
    assert params["filter[eventType]"] == "fax.received"
    assert params["filter[status]"] == "dead"
    assert params["page[size]"] == "100"
    assert params["page[after]"] == "0198c4a1"
    # An unset filter is absent, not empty: `filter[status]=` would be a 400
    # rather than "no opinion".
    assert "page[before]" not in params
    assert route.calls.last.request.headers["accept"] == JSONAPI


def test_list_reads_the_deliveries_and_the_next_cursor_from_page_meta(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(DELIVERIES_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [_delivery_resource()],
                "links": {"next": f"{DELIVERIES_URL}?page%5Bafter%5D=0198c4a1-next"},
                "meta": {"page": {"size": 25, "nextCursor": "0198c4a1-next"}},
            },
        )
    )

    with client:
        page = client.webhook_deliveries.list(status="dead")

    assert isinstance(page, WebhookDeliveryPage)
    assert len(page) == 1
    assert list(page)[0].id == DELIVERY_ID
    assert page[0].status == "dead"
    assert page.next_cursor == "0198c4a1-next"
    assert page.next_url is not None and "page%5Bafter%5D" in page.next_url


def test_an_empty_page_is_the_good_news_rather_than_a_missing_history(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # Nothing owed and nothing given up on. A delivery that lands leaves no
    # row at all, so an empty collection here is a healthy integration — the
    # reading this docstring exists to stop anybody getting backwards.
    respx_mock.get(DELIVERIES_URL).mock(
        return_value=httpx.Response(
            200, json={"data": [], "meta": {"page": {"size": 25, "nextCursor": None}}}
        )
    )

    with client:
        page = client.webhook_deliveries.list(status="pending")

    assert len(page) == 0
    assert list(page) == []
    assert page.next_cursor is None
    assert page.next_url is None


def test_a_status_this_collection_does_not_publish_is_refused_by_the_api(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # `delivered` is the one a caller reaches for, and the one that no longer
    # exists: the collection used to publish it. The API answers 400 rather
    # than returning an empty page, and this client passes the value through
    # so the refusal reaches the caller instead of being second-guessed by a
    # copy of the enum that would go stale here.
    route = respx_mock.get(DELIVERIES_URL).mock(
        return_value=httpx.Response(
            400,
            json={
                "errors": [
                    {
                        "status": "400",
                        "code": "invalid_query",
                        "title": "Bad query",
                        "detail": "filter[status] must be one of: pending, dead.",
                        "source": {"parameter": "filter[status]"},
                    }
                ]
            },
        )
    )

    with client, pytest.raises(ApiError) as caught:
        client.webhook_deliveries.list(status="delivered")

    assert route.calls.last.request.url.params["filter[status]"] == "delivered"
    assert caught.value.status_code == 400
    assert caught.value.errors[0].source == {"parameter": "filter[status]"}


# -- get -------------------------------------------------------------------


def test_get_reads_a_jsonapi_document_into_the_public_dataclass(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(DELIVERY_URL).mock(
        return_value=httpx.Response(200, json={"data": _delivery_resource()})
    )

    with client:
        delivery = client.webhook_deliveries.get(DELIVERY_ID)

    assert isinstance(delivery, WebhookDelivery)
    assert delivery.id == DELIVERY_ID
    assert delivery.endpoint_id == ENDPOINT_ID
    assert delivery.event_id == EVENT_ID
    assert delivery.event_type == "fax.received"
    assert delivery.payload_sha256 == DIGEST
    assert delivery.status == "dead"
    assert delivery.attempt_no == 7
    assert delivery.status_code == 500
    assert delivery.duration_ms == 812
    assert delivery.error is None
    assert delivery.next_attempt_at is None
    assert delivery.dead_at == datetime(2026, 8, 16, 19, 45, 0, tzinfo=timezone.utc)
    assert delivery.created_at == datetime(2026, 8, 16, 11, 2, 31, tzinfo=timezone.utc)
    # The whole resource object is kept, so a member the API adds after this
    # release still reaches the caller — `deliveredAt`, which this model
    # deliberately does not read, included.
    assert delivery.raw["type"] == "webhook-deliveries"
    assert "deliveredAt" in delivery.raw["attributes"]


def test_a_pending_delivery_carries_its_next_attempt_and_no_status_code(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The other status, and the shape it arrives in: we never reached the
    # server, so `statusCode` is null and `error` says why.
    respx_mock.get(DELIVERY_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": _delivery_resource(
                    status="pending",
                    attemptNo=2,
                    statusCode=None,
                    error="Connection timed out",
                    nextAttemptAt="2026-08-16T11:12:31.000000Z",
                    deadAt=None,
                )
            },
        )
    )

    with client:
        delivery = client.webhook_deliveries.get(DELIVERY_ID)

    assert delivery.status == "pending"
    assert delivery.attempt_no == 2
    assert delivery.status_code is None
    assert delivery.error == "Connection timed out"
    assert delivery.next_attempt_at == datetime(2026, 8, 16, 11, 12, 31, tzinfo=timezone.utc)
    assert delivery.dead_at is None


def test_a_relationship_without_linkage_is_no_endpoint_id_rather_than_a_crash(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # A JSON:API server may answer a relationship with `links` alone. That is
    # legal, it says nothing about the delivery, and it must not raise.
    respx_mock.get(DELIVERY_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": _delivery_resource(
                    relationships={
                        "endpoint": {"links": {"self": f"{DELIVERY_URL}/relationships/endpoint"}}
                    }
                )
            },
        )
    )

    with client:
        delivery = client.webhook_deliveries.get(DELIVERY_ID)

    assert delivery.endpoint_id is None
    assert delivery.id == DELIVERY_ID


def test_a_webhook_delivery_id_stays_inside_its_own_path_segment(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(200, json={"data": _delivery_resource()})
    )

    with client:
        client.webhook_deliveries.get("../faxes/secret")

    assert route.calls.last.request.url.raw_path == b"/v1/webhook-deliveries/..%2Ffaxes%2Fsecret"


def test_an_empty_webhook_delivery_id_is_refused_by_its_own_name(client: Ringivo) -> None:
    with client, pytest.raises(ValueError, match="a webhook delivery id is required"):
        client.webhook_deliveries.get("")


def test_a_delivery_that_is_not_there_raises_a_typed_404(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # Three things answer 404 here and they are indistinguishable on purpose:
    # an id that names nothing, a delivery of an endpoint this token cannot
    # reach, and one that has since succeeded — a success leaves no row.
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

    with client, pytest.raises(ApiError) as caught:
        client.webhook_deliveries.get(DELIVERY_ID)

    assert caught.value.status_code == 404
    assert caught.value.code == "not_found"
