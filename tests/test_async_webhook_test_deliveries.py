"""Test events again, awaited, and asserted on the WIRE.

The mirror of tests/test_webhook_test_deliveries.py. `AsyncWebhookEndpoints`
and `AsyncWebhookTestDeliveries` are siblings of the sync classes rather
than wrappers around them, so the requests they build and the waiting they
do are their own code and get their own assertions. `wait()` here sleeps
through `ringivo.async_webhook_test_deliveries._sleep`, which every waiting
test replaces, so no test sleeps for real.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

import ringivo.async_webhook_test_deliveries
from ringivo import (
    ApiError,
    AsyncRingivo,
    WebhookTestDelivery,
    WebhookTestDeliveryPage,
    WebhookTestTimeoutError,
    is_retryable,
)

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
ENDPOINT_ID = "0198c4a1-8192-73b4-e5b6-708192031425"
SEND_URL = f"{BASE_URL}/v1/webhook-endpoints/{ENDPOINT_ID}/test"
TESTS_URL = f"{BASE_URL}/v1/webhook-test-deliveries"
TEST_ID = "019a0b3c-5d6e-7f80-9a1b-2c3d4e5f6071"
TEST_URL = f"{TESTS_URL}/{TEST_ID}"
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


class _Clock:
    """A fake `time.monotonic` and `asyncio.sleep` that share one timeline."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> _Clock:
    fake = _Clock()
    monkeypatch.setattr(ringivo.async_webhook_test_deliveries, "_sleep", fake.sleep)
    monkeypatch.setattr(ringivo.async_webhook_test_deliveries, "_monotonic", fake.monotonic)
    return fake


def _resource(**attribute_overrides: object) -> dict[str, object]:
    attributes: dict[str, object] = {
        "eventType": "fax.delivered",
        "status": "pending",
        "statusCode": None,
        "durationMs": None,
        "responseBody": None,
        "error": None,
        "attemptedAt": None,
        "createdAt": "2026-10-22T15:04:05.000000Z",
        "updatedAt": "2026-10-22T15:04:05.000000Z",
    }
    attributes.update(attribute_overrides)
    return {
        "type": "webhook-test-deliveries",
        "id": TEST_ID,
        "attributes": attributes,
        "relationships": {"endpoint": {"data": {"type": "webhook-endpoints", "id": ENDPOINT_ID}}},
    }


def _document(**attribute_overrides: object) -> dict[str, object]:
    return {"data": _resource(**attribute_overrides)}


_DELIVERED: dict[str, object] = {
    "status": "delivered",
    "statusCode": 200,
    "durationMs": 87,
    "responseBody": '{"received":true}',
    "attemptedAt": "2026-10-22T15:04:06.000000Z",
}


def _refusal(status: int, title: str, *, retry_after: str | None = None, **extra: Any) -> Any:
    error: dict[str, Any] = {"status": str(status), "title": title, "detail": f"{title}."}
    error.update(extra)
    return httpx.Response(
        status,
        json={"errors": [error]},
        headers={"Retry-After": retry_after} if retry_after is not None else None,
    )


@pytest.mark.anyio
async def test_send_test_posts_a_flat_json_body_naming_the_type(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.post(SEND_URL).mock(return_value=httpx.Response(202, json=_document()))

    async with client:
        test = await client.webhook_endpoints.send_test(ENDPOINT_ID, type="webhook.test")

    request = route.calls.last.request
    assert json.loads(request.content) == {"eventType": "webhook.test"}
    assert request.headers["content-type"] == "application/json"
    assert request.headers["accept"] == JSONAPI
    assert "idempotency-key" not in request.headers
    assert isinstance(test, WebhookTestDelivery)
    assert test.status == "pending"
    assert test.endpoint_id == ENDPOINT_ID


@pytest.mark.anyio
async def test_send_test_without_a_type_sends_an_empty_object(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.post(SEND_URL).mock(return_value=httpx.Response(202, json=_document()))

    async with client:
        await client.webhook_endpoints.send_test(ENDPOINT_ID)

    assert json.loads(route.calls.last.request.content) == {}


@pytest.mark.anyio
async def test_send_test_reads_a_202_that_already_failed(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.post(SEND_URL).mock(
        return_value=httpx.Response(202, json=_document(status="failed", error="Not queued."))
    )

    async with client:
        test = await client.webhook_endpoints.send_test(ENDPOINT_ID)

    assert test.status == "failed"
    assert test.error == "Not queued."


@pytest.mark.anyio
async def test_a_disabled_endpoint_is_a_409(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.post(SEND_URL).mock(return_value=_refusal(409, "Endpoint disabled"))

    async with client:
        with pytest.raises(ApiError) as caught:
            await client.webhook_endpoints.send_test(ENDPOINT_ID)

    assert caught.value.status_code == 409
    assert is_retryable(caught.value) is False


@pytest.mark.anyio
async def test_a_type_the_endpoint_cannot_receive_is_a_422(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.post(SEND_URL).mock(
        return_value=_refusal(422, "Unprocessable Entity", source={"pointer": "/eventType"})
    )

    async with client:
        with pytest.raises(ApiError) as caught:
            await client.webhook_endpoints.send_test(ENDPOINT_ID, type="nope")

    assert caught.value.status_code == 422
    assert caught.value.errors[0].source == {"pointer": "/eventType"}


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status", "header", "seconds"),
    [(429, "42", 42), (503, "60", 60)],
    ids=["rate-limited", "limiter-unavailable"],
)
async def test_a_429_or_503_carries_its_retry_after_and_is_not_resent(
    respx_mock: respx.MockRouter, client: AsyncRingivo, status: int, header: str, seconds: int
) -> None:
    route = respx_mock.post(SEND_URL).mock(
        return_value=_refusal(status, "Refused", retry_after=header)
    )

    async with client:
        with pytest.raises(ApiError) as caught:
            await client.webhook_endpoints.send_test(ENDPOINT_ID)

    assert caught.value.status_code == status
    assert caught.value.retry_after == seconds
    assert is_retryable(caught.value) is True
    assert route.call_count == 1


@pytest.mark.anyio
async def test_get_reads_a_delivered_result(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.get(TEST_URL).mock(return_value=httpx.Response(200, json=_document(**_DELIVERED)))

    async with client:
        test = await client.webhook_test_deliveries.get(TEST_ID)

    assert test.status == "delivered"
    assert test.status_code == 200
    assert test.response_body == '{"received":true}'


@pytest.mark.anyio
async def test_list_builds_the_filter_and_page_query(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.get(TESTS_URL).mock(
        return_value=httpx.Response(
            200,
            json={"data": [_resource()], "meta": {"page": {"nextCursor": "nxt"}}},
        )
    )

    async with client:
        page = await client.webhook_test_deliveries.list(
            endpoint=ENDPOINT_ID, ids=["a", "b"], before="cur", page_size=10
        )

    params = route.calls.last.request.url.params
    assert params["filter[endpoint]"] == ENDPOINT_ID
    assert params.get_list("filter[id][]") == ["a", "b"]
    assert params["page[before]"] == "cur"
    assert params["page[size]"] == "10"
    assert isinstance(page, WebhookTestDeliveryPage)
    assert [t.id for t in page] == [TEST_ID]
    assert page.next_cursor == "nxt"


@pytest.mark.anyio
async def test_wait_polls_until_the_result_is_no_longer_pending(
    respx_mock: respx.MockRouter, client: AsyncRingivo, clock: _Clock
) -> None:
    route = respx_mock.get(TEST_URL).mock(
        side_effect=[
            httpx.Response(200, json=_document()),
            httpx.Response(200, json=_document(**_DELIVERED)),
        ]
    )
    pending = WebhookTestDelivery._from_resource(_resource())

    async with client:
        result = await client.webhook_test_deliveries.wait(pending, interval=3.0)

    assert result.status == "delivered"
    assert route.call_count == 2
    assert clock.slept == [3.0, 3.0]


@pytest.mark.anyio
async def test_wait_returns_a_result_that_is_not_pending_without_a_request(
    respx_mock: respx.MockRouter, client: AsyncRingivo, clock: _Clock
) -> None:
    route = respx_mock.get(TEST_URL).mock(return_value=httpx.Response(200, json=_document()))
    failed = WebhookTestDelivery._from_resource(_resource(status="failed", error="Not queued."))

    async with client:
        result = await client.webhook_test_deliveries.wait(failed)

    assert result is failed
    assert route.call_count == 0
    assert clock.slept == []


@pytest.mark.anyio
async def test_wait_takes_an_id_and_reads_it_first(
    respx_mock: respx.MockRouter, client: AsyncRingivo, clock: _Clock
) -> None:
    route = respx_mock.get(TEST_URL).mock(
        return_value=httpx.Response(200, json=_document(**_DELIVERED))
    )

    async with client:
        result = await client.webhook_test_deliveries.wait(TEST_ID)

    assert result.status == "delivered"
    assert route.call_count == 1
    assert clock.slept == []


@pytest.mark.anyio
async def test_wait_raises_with_the_last_read_when_the_timeout_runs_out(
    respx_mock: respx.MockRouter, client: AsyncRingivo, clock: _Clock
) -> None:
    route = respx_mock.get(TEST_URL).mock(return_value=httpx.Response(200, json=_document()))
    pending = WebhookTestDelivery._from_resource(_resource())

    async with client:
        with pytest.raises(WebhookTestTimeoutError) as caught:
            await client.webhook_test_deliveries.wait(pending, interval=4.0, timeout=10.0)

    assert clock.slept == [4.0, 4.0, 2.0]
    assert route.call_count == 3
    assert caught.value.delivery.status == "pending"


@pytest.mark.anyio
async def test_wait_has_the_same_defaults_as_the_sync_twin() -> None:
    import inspect

    from ringivo import AsyncWebhookTestDeliveries, WebhookTestDeliveries

    sync = inspect.signature(WebhookTestDeliveries.wait).parameters
    awaited = inspect.signature(AsyncWebhookTestDeliveries.wait).parameters
    assert awaited["timeout"].default == sync["timeout"].default
    assert awaited["interval"].default == sync["interval"].default


@pytest.mark.anyio
async def test_wait_refuses_an_interval_that_is_not_positive(client: AsyncRingivo) -> None:
    async with client:
        with pytest.raises(ValueError, match="interval"):
            await client.webhook_test_deliveries.wait(TEST_ID, interval=0)


@pytest.mark.anyio
async def test_send_test_refuses_an_empty_type_before_any_request(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.post(SEND_URL)

    async with client:
        with pytest.raises(ValueError, match="type"):
            await client.webhook_endpoints.send_test(ENDPOINT_ID, type="")

    assert not route.called


@pytest.mark.anyio
async def test_send_test_reads_the_endpoint_id_the_server_always_sends(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.post(SEND_URL).mock(return_value=httpx.Response(202, json=_document()))

    async with client:
        test = await client.webhook_endpoints.send_test(ENDPOINT_ID)

    assert test.endpoint_id == ENDPOINT_ID


@pytest.mark.anyio
@pytest.mark.parametrize(
    "refusal",
    [
        _refusal(503, "Service Unavailable", retry_after="5"),
        _refusal(404, "Not Found"),
        _refusal(429, "Too Many Requests"),
    ],
    ids=["503-with-retry-after", "404", "429-without-retry-after"],
)
async def test_wait_lets_any_other_refused_read_propagate_at_once(
    respx_mock: respx.MockRouter, client: AsyncRingivo, clock: _Clock, refusal: httpx.Response
) -> None:
    route = respx_mock.get(TEST_URL).mock(return_value=refusal)
    pending = WebhookTestDelivery._from_resource(_resource())

    async with client:
        with pytest.raises(ApiError) as caught:
            await client.webhook_test_deliveries.wait(pending, interval=2.0)

    assert caught.value.status_code == refusal.status_code
    assert route.call_count == 1
    assert clock.slept == [2.0]


@pytest.mark.anyio
async def test_wait_sleeps_through_a_429_on_a_read_and_keeps_polling(
    respx_mock: respx.MockRouter, client: AsyncRingivo, clock: _Clock
) -> None:
    route = respx_mock.get(TEST_URL).mock(
        side_effect=[
            _refusal(429, "Too Many Requests", retry_after="5"),
            httpx.Response(200, json=_document(**_DELIVERED)),
        ]
    )
    pending = WebhookTestDelivery._from_resource(_resource())

    async with client:
        result = await client.webhook_test_deliveries.wait(pending, interval=2.0)

    assert result.status == "delivered"
    assert route.call_count == 2
    assert clock.slept == [2.0, 5]


@pytest.mark.anyio
async def test_wait_sleeps_through_a_429_on_the_first_read_of_an_id(
    respx_mock: respx.MockRouter, client: AsyncRingivo, clock: _Clock
) -> None:
    route = respx_mock.get(TEST_URL).mock(
        side_effect=[
            _refusal(429, "Too Many Requests", retry_after="3"),
            httpx.Response(200, json=_document(**_DELIVERED)),
        ]
    )

    async with client:
        result = await client.webhook_test_deliveries.wait(TEST_ID)

    assert result.status == "delivered"
    assert route.call_count == 2
    assert clock.slept == [3]


@pytest.mark.anyio
async def test_wait_cuts_a_429_sleep_to_the_deadline_and_then_raises_the_429(
    respx_mock: respx.MockRouter, client: AsyncRingivo, clock: _Clock
) -> None:
    route = respx_mock.get(TEST_URL).mock(
        return_value=_refusal(429, "Too Many Requests", retry_after="30")
    )
    pending = WebhookTestDelivery._from_resource(_resource())

    async with client:
        with pytest.raises(ApiError) as caught:
            await client.webhook_test_deliveries.wait(pending, interval=2.0, timeout=10.0)

    assert clock.slept == [2.0, 8.0]
    assert route.call_count == 2
    assert caught.value.status_code == 429


@pytest.mark.anyio
@pytest.mark.parametrize("timeout", [-1.0, float("nan")], ids=["minus-one", "nan"])
async def test_wait_refuses_a_timeout_that_is_not_zero_or_more(
    respx_mock: respx.MockRouter, client: AsyncRingivo, timeout: float
) -> None:
    route = respx_mock.get(url__startswith=TESTS_URL)

    async with client:
        with pytest.raises(ValueError, match="timeout"):
            await client.webhook_test_deliveries.wait(TEST_ID, timeout=timeout)

    assert not route.called
