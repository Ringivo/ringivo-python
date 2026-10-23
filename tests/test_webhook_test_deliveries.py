"""Test events: send one, read its result, wait for it — asserted on the WIRE.

`webhook_endpoints.send_test()` is a process endpoint, so what matters is
what goes out (a flat JSON body, not a JSON:API document) and how each
refusal comes back: 409, 422, and the 429 and 503 whose `Retry-After` a
caller must honour. A send is never retried by this client — each send is a
new test — so no test here expects a second POST.

`webhook_test_deliveries.wait()` re-reads one result until it is no longer
`pending`. It sleeps through the module's own `_sleep` and reads time
through its own `_monotonic`; every test that waits replaces both, so no
test here sleeps for real.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest
import respx

import ringivo.webhook_test_deliveries
from ringivo import (
    ApiError,
    Ringivo,
    RingivoError,
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
def client() -> Ringivo:
    return Ringivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=["webhooks:read", "webhooks:write"],
    )


class _Clock:
    """A fake `time.monotonic` and `time.sleep` that share one timeline."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> _Clock:
    fake = _Clock()
    monkeypatch.setattr(ringivo.webhook_test_deliveries, "_sleep", fake.sleep)
    monkeypatch.setattr(ringivo.webhook_test_deliveries, "_monotonic", fake.monotonic)
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
    "updatedAt": "2026-10-22T15:04:06.000000Z",
}


def _refusal(status: int, title: str, *, retry_after: str | None = None, **extra: Any) -> Any:
    error: dict[str, Any] = {"status": str(status), "title": title, "detail": f"{title}."}
    error.update(extra)
    return httpx.Response(
        status,
        json={"errors": [error]},
        headers={"Retry-After": retry_after} if retry_after is not None else None,
    )


# -- send_test: the request ---------------------------------------------------


def test_send_test_posts_a_flat_json_body_naming_the_type(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.post(SEND_URL).mock(return_value=httpx.Response(202, json=_document()))

    with client:
        client.webhook_endpoints.send_test(ENDPOINT_ID, type="fax.delivered")

    request = route.calls.last.request
    # FLAT JSON, as the spec's `WebhookTestRequest` says — not a JSON:API
    # document with `data.attributes`.
    assert json.loads(request.content) == {"eventType": "fax.delivered"}
    assert request.headers["content-type"] == "application/json"
    assert request.headers["accept"] == JSONAPI
    # Each send is a new test, so there is no key to replay one with.
    assert "idempotency-key" not in request.headers
    assert route.call_count == 1


def test_send_test_without_a_type_sends_an_empty_object(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.post(SEND_URL).mock(return_value=httpx.Response(202, json=_document()))

    with client:
        client.webhook_endpoints.send_test(ENDPOINT_ID)

    # No `eventType` member at all — never `null` — so the API sends the
    # endpoint's first type.
    assert json.loads(route.calls.last.request.content) == {}


def test_send_test_body_matches_the_spec_request_schema(
    respx_mock: respx.MockRouter, client: Ringivo, openapi_spec: dict[str, Any]
) -> None:
    operation = openapi_spec["paths"]["/v1/webhook-endpoints/{webhookEndpoint}/test"]["post"]
    body = operation["requestBody"]
    assert body["required"] is False
    assert list(body["content"]) == ["application/json"]
    schema = openapi_spec["components"]["schemas"]["WebhookTestRequest"]
    assert set(schema["properties"]) == {"eventType"}

    route = respx_mock.post(SEND_URL).mock(return_value=httpx.Response(202, json=_document()))
    with client:
        client.webhook_endpoints.send_test(
            ENDPOINT_ID, type=body["content"]["application/json"]["example"]["eventType"]
        )

    assert (
        json.loads(route.calls.last.request.content)
        == body["content"]["application/json"]["example"]
    )


def test_send_test_escapes_the_endpoint_id(respx_mock: respx.MockRouter, client: Ringivo) -> None:
    route = respx_mock.post(f"{BASE_URL}/v1/webhook-endpoints/a%2Fb/test").mock(
        return_value=httpx.Response(202, json=_document())
    )

    with client:
        client.webhook_endpoints.send_test("a/b")

    assert route.called


# -- send_test: the 202 -------------------------------------------------------


def test_send_test_reads_the_pending_result(respx_mock: respx.MockRouter, client: Ringivo) -> None:
    respx_mock.post(SEND_URL).mock(return_value=httpx.Response(202, json=_document()))

    with client:
        test = client.webhook_endpoints.send_test(ENDPOINT_ID, type="fax.delivered")

    assert isinstance(test, WebhookTestDelivery)
    assert test.id == TEST_ID
    assert test.endpoint_id == ENDPOINT_ID
    assert test.event_type == "fax.delivered"
    assert test.status == "pending"
    assert test.status_code is None
    assert test.duration_ms is None
    assert test.response_body is None
    assert test.error is None
    assert test.attempted_at is None
    assert test.created_at == datetime(2026, 10, 22, 15, 4, 5, tzinfo=timezone.utc)
    assert test.raw["id"] == TEST_ID


def test_send_test_reads_a_202_that_already_failed(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.post(SEND_URL).mock(
        return_value=httpx.Response(
            202, json=_document(status="failed", error="The test could not be queued.")
        )
    )

    with client:
        test = client.webhook_endpoints.send_test(ENDPOINT_ID)

    # A 202 that already failed is a result, not an exception.
    assert test.status == "failed"
    assert test.error == "The test could not be queued."


def test_send_test_reads_the_spec_202_example(
    respx_mock: respx.MockRouter, client: Ringivo, openapi_spec: dict[str, Any]
) -> None:
    operation = openapi_spec["paths"]["/v1/webhook-endpoints/{webhookEndpoint}/test"]["post"]
    example = operation["responses"]["202"]["content"][JSONAPI]["example"]
    respx_mock.post(SEND_URL).mock(return_value=httpx.Response(202, json=example))

    with client:
        test = client.webhook_endpoints.send_test(ENDPOINT_ID)

    assert test.id == example["data"]["id"]
    assert test.status == example["data"]["attributes"]["status"]
    assert test.event_type == example["data"]["attributes"]["eventType"]
    # The server always names the endpoint, with `data` and no `links`.
    assert example["data"]["relationships"] == {
        "endpoint": {"data": {"type": "webhook-endpoints", "id": test.endpoint_id}}
    }
    assert test.endpoint_id is not None


@pytest.mark.parametrize(
    ("path", "status"),
    [
        ("/v1/webhook-endpoints/{webhookEndpoint}/test", "202"),
        ("/v1/webhook-test-deliveries/{webhookTestDelivery}", "200"),
    ],
)
def test_the_fixtures_use_the_exact_relationship_shape_the_spec_publishes(
    openapi_spec: dict[str, Any], path: str, status: str
) -> None:
    operation = openapi_spec["paths"][path]
    operation = operation.get("post") or operation["get"]
    example = operation["responses"][status]["content"][JSONAPI]["example"]
    published = example["data"]["relationships"]
    endpoint_id = published["endpoint"]["data"]["id"]

    # `data` is always there and there are no `links`: the fixtures here
    # send exactly that shape, and nothing the server does not send.
    assert published == {"endpoint": {"data": {"type": "webhook-endpoints", "id": endpoint_id}}}
    assert _resource()["relationships"] == {
        "endpoint": {"data": {"type": "webhook-endpoints", "id": ENDPOINT_ID}}
    }


def test_send_test_refuses_an_empty_type_before_any_request(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The API turns "" into null and then sends the endpoint's FIRST type
    # with a 202 — a test of a type the caller did not ask for.
    route = respx_mock.post(SEND_URL)

    with client, pytest.raises(ValueError, match="type"):
        client.webhook_endpoints.send_test(ENDPOINT_ID, type="")

    assert not route.called


# -- send_test: the refusals --------------------------------------------------


def test_a_disabled_endpoint_is_a_409_that_is_not_retryable(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.post(SEND_URL).mock(return_value=_refusal(409, "Endpoint disabled"))

    with client, pytest.raises(ApiError) as caught:
        client.webhook_endpoints.send_test(ENDPOINT_ID)

    assert caught.value.status_code == 409
    assert caught.value.errors[0].title == "Endpoint disabled"
    assert caught.value.retry_after is None
    assert is_retryable(caught.value) is False


def test_a_type_the_endpoint_cannot_receive_is_a_422_pointing_at_event_type(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.post(SEND_URL).mock(
        return_value=_refusal(422, "Unprocessable Entity", source={"pointer": "/eventType"})
    )

    with client, pytest.raises(ApiError) as caught:
        client.webhook_endpoints.send_test(ENDPOINT_ID, type="port_order.status_changed")

    assert caught.value.status_code == 422
    assert caught.value.errors[0].source == {"pointer": "/eventType"}
    assert is_retryable(caught.value) is False


@pytest.mark.parametrize(
    ("status", "title", "header", "seconds"),
    [
        (429, "Too many test events", "42", 42),
        (503, "Test events unavailable", "60", 60),
    ],
    ids=["rate-limited", "limiter-unavailable"],
)
def test_a_429_or_503_carries_its_retry_after_and_is_not_resent(
    respx_mock: respx.MockRouter,
    client: Ringivo,
    status: int,
    title: str,
    header: str,
    seconds: int,
) -> None:
    route = respx_mock.post(SEND_URL).mock(return_value=_refusal(status, title, retry_after=header))

    with client, pytest.raises(ApiError) as caught:
        client.webhook_endpoints.send_test(ENDPOINT_ID)

    assert caught.value.status_code == status
    assert caught.value.retry_after == seconds
    # Retryable by the caller after `retry_after` — but never by the client.
    assert is_retryable(caught.value) is True
    assert route.call_count == 1


# -- get / list ---------------------------------------------------------------


def test_get_reads_a_delivered_result(respx_mock: respx.MockRouter, client: Ringivo) -> None:
    route = respx_mock.get(TEST_URL).mock(
        return_value=httpx.Response(200, json=_document(**_DELIVERED))
    )

    with client:
        test = client.webhook_test_deliveries.get(TEST_ID)

    assert route.calls.last.request.headers["accept"] == JSONAPI
    assert test.status == "delivered"
    assert test.status_code == 200
    assert test.duration_ms == 87
    assert test.response_body == '{"received":true}'
    assert test.attempted_at == datetime(2026, 10, 22, 15, 4, 6, tzinfo=timezone.utc)
    assert test.updated_at == datetime(2026, 10, 22, 15, 4, 6, tzinfo=timezone.utc)


def test_list_builds_the_filter_and_page_query(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(TESTS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    with client:
        client.webhook_test_deliveries.list(
            endpoint=ENDPOINT_ID, ids=["a", "b"], page_size=50, after="cur"
        )

    params = route.calls.last.request.url.params
    assert params["filter[endpoint]"] == ENDPOINT_ID
    # One `filter[id][]` pair per id: the spec refuses the bare `filter[id]`.
    assert params.get_list("filter[id][]") == ["a", "b"]
    assert "filter[id]" not in params
    assert params["page[size]"] == "50"
    assert params["page[after]"] == "cur"
    assert "page[before]" not in params


def test_list_refuses_one_bare_string_of_ids(client: Ringivo) -> None:
    with client, pytest.raises(ValueError, match="not one string"):
        client.webhook_test_deliveries.list(ids=TEST_ID)


def test_list_reads_the_page_and_its_cursor(
    respx_mock: respx.MockRouter, client: Ringivo, openapi_spec: dict[str, Any]
) -> None:
    example = openapi_spec["paths"]["/v1/webhook-test-deliveries"]["get"]["responses"]["200"][
        "content"
    ][JSONAPI]["example"]
    document = {
        **example,
        "links": {"next": f"{TESTS_URL}?page%5Bafter%5D=nxt"},
        "meta": {"page": {"size": 25, "nextCursor": "nxt"}},
    }
    respx_mock.get(TESTS_URL).mock(return_value=httpx.Response(200, json=document))

    with client:
        page = client.webhook_test_deliveries.list()

    assert isinstance(page, WebhookTestDeliveryPage)
    assert len(page) == 1
    assert page[0].status == "failed"
    assert page[0].status_code == 401
    assert page[0].error == "The endpoint answered 401."
    assert [t.id for t in page] == [example["data"][0]["id"]]
    assert page.next_cursor == "nxt"
    assert page.next_url == f"{TESTS_URL}?page%5Bafter%5D=nxt"


# -- wait ---------------------------------------------------------------------


def test_wait_polls_until_the_result_is_no_longer_pending(
    respx_mock: respx.MockRouter, client: Ringivo, clock: _Clock
) -> None:
    route = respx_mock.get(TEST_URL).mock(
        side_effect=[
            httpx.Response(200, json=_document()),
            httpx.Response(200, json=_document(**_DELIVERED)),
        ]
    )
    pending = WebhookTestDelivery._from_resource(_resource())

    with client:
        result = client.webhook_test_deliveries.wait(pending, interval=3.0)

    assert result.status == "delivered"
    assert route.call_count == 2
    # It sleeps BEFORE each read: the 202 it was handed was already a read.
    assert clock.slept == [3.0, 3.0]


def test_wait_returns_a_result_that_is_not_pending_without_a_request(
    respx_mock: respx.MockRouter, client: Ringivo, clock: _Clock
) -> None:
    route = respx_mock.get(TEST_URL).mock(return_value=httpx.Response(200, json=_document()))
    failed = WebhookTestDelivery._from_resource(
        _resource(status="failed", error="The test could not be queued.")
    )

    with client:
        result = client.webhook_test_deliveries.wait(failed)

    assert result is failed
    assert route.call_count == 0
    assert clock.slept == []


def test_wait_takes_an_id_and_reads_it_first(
    respx_mock: respx.MockRouter, client: Ringivo, clock: _Clock
) -> None:
    route = respx_mock.get(TEST_URL).mock(
        return_value=httpx.Response(200, json=_document(**_DELIVERED))
    )

    with client:
        result = client.webhook_test_deliveries.wait(TEST_ID)

    assert result.status == "delivered"
    assert route.call_count == 1
    # Read at once: an id carries no status to skip the first read with.
    assert clock.slept == []


def test_wait_raises_with_the_last_read_when_the_timeout_runs_out(
    respx_mock: respx.MockRouter, client: Ringivo, clock: _Clock
) -> None:
    route = respx_mock.get(TEST_URL).mock(return_value=httpx.Response(200, json=_document()))
    pending = WebhookTestDelivery._from_resource(_resource())

    with client, pytest.raises(WebhookTestTimeoutError) as caught:
        client.webhook_test_deliveries.wait(pending, interval=4.0, timeout=10.0)

    # 4 + 4 + 2: the last sleep is cut to what is left of the timeout, and
    # one last read is made at the deadline before giving up.
    assert clock.slept == [4.0, 4.0, 2.0]
    assert route.call_count == 3
    assert caught.value.delivery.status == "pending"
    assert caught.value.delivery.id == TEST_ID
    assert isinstance(caught.value, RingivoError)
    assert isinstance(caught.value, TimeoutError)


def test_wait_defaults_outlast_the_servers_two_minute_cutoff() -> None:
    import inspect

    from ringivo import WebhookTestDeliveries

    parameters = inspect.signature(WebhookTestDeliveries.wait).parameters
    timeout = parameters["timeout"].default
    interval = parameters["interval"].default
    # The server fails a test with no result after 120 s, so a default at or
    # under that would time out on a test the server was about to settle.
    assert 120 < timeout <= 180
    assert 0 < interval <= 5


@pytest.mark.parametrize("interval", [0, -1.0])
def test_wait_refuses_an_interval_that_is_not_positive(client: Ringivo, interval: float) -> None:
    with client, pytest.raises(ValueError, match="interval"):
        client.webhook_test_deliveries.wait(TEST_ID, interval=interval)


@pytest.mark.parametrize(
    "refusal",
    [
        _refusal(503, "Service Unavailable", retry_after="5"),
        _refusal(404, "Not Found"),
        _refusal(429, "Too Many Requests"),  # no Retry-After: nothing to wait for
    ],
    ids=["503-with-retry-after", "404", "429-without-retry-after"],
)
def test_wait_lets_any_other_refused_read_propagate_at_once(
    respx_mock: respx.MockRouter, client: Ringivo, clock: _Clock, refusal: httpx.Response
) -> None:
    route = respx_mock.get(TEST_URL).mock(return_value=refusal)
    pending = WebhookTestDelivery._from_resource(_resource())

    with client, pytest.raises(ApiError) as caught:
        client.webhook_test_deliveries.wait(pending, interval=2.0)

    assert caught.value.status_code == refusal.status_code
    assert route.call_count == 1
    assert clock.slept == [2.0]


def test_wait_sleeps_through_a_429_on_a_read_and_keeps_polling(
    respx_mock: respx.MockRouter, client: Ringivo, clock: _Clock
) -> None:
    route = respx_mock.get(TEST_URL).mock(
        side_effect=[
            _refusal(429, "Too Many Requests", retry_after="5"),
            httpx.Response(200, json=_document(**_DELIVERED)),
        ]
    )
    pending = WebhookTestDelivery._from_resource(_resource())

    with client:
        result = client.webhook_test_deliveries.wait(pending, interval=2.0)

    assert result.status == "delivered"
    assert route.call_count == 2
    # The interval, then the server's own Retry-After, then the read.
    assert clock.slept == [2.0, 5]


def test_wait_sleeps_through_a_429_on_the_first_read_of_an_id(
    respx_mock: respx.MockRouter, client: Ringivo, clock: _Clock
) -> None:
    route = respx_mock.get(TEST_URL).mock(
        side_effect=[
            _refusal(429, "Too Many Requests", retry_after="3"),
            httpx.Response(200, json=_document(**_DELIVERED)),
        ]
    )

    with client:
        result = client.webhook_test_deliveries.wait(TEST_ID)

    assert result.status == "delivered"
    assert route.call_count == 2
    assert clock.slept == [3]


def test_wait_cuts_a_429_sleep_to_the_deadline_and_then_raises_the_429(
    respx_mock: respx.MockRouter, client: Ringivo, clock: _Clock
) -> None:
    route = respx_mock.get(TEST_URL).mock(
        return_value=_refusal(429, "Too Many Requests", retry_after="30")
    )
    pending = WebhookTestDelivery._from_resource(_resource())

    with client, pytest.raises(ApiError) as caught:
        client.webhook_test_deliveries.wait(pending, interval=2.0, timeout=10.0)

    # 2 s interval, then min(30, 8 left) = 8 s, then one read at the
    # deadline that is refused again: past the deadline the 429 propagates.
    assert clock.slept == [2.0, 8.0]
    assert route.call_count == 2
    assert caught.value.status_code == 429
    assert caught.value.retry_after == 30


@pytest.mark.parametrize("timeout", [-1.0, -0.001, float("nan")], ids=["minus-one", "tiny", "nan"])
def test_wait_refuses_a_timeout_that_is_not_zero_or_more(
    respx_mock: respx.MockRouter, client: Ringivo, timeout: float
) -> None:
    route = respx_mock.get(url__startswith=TESTS_URL)

    with client, pytest.raises(ValueError, match="timeout"):
        client.webhook_test_deliveries.wait(TEST_ID, timeout=timeout)

    assert not route.called


def test_wait_with_a_zero_timeout_reads_an_id_once(
    respx_mock: respx.MockRouter, client: Ringivo, clock: _Clock
) -> None:
    route = respx_mock.get(TEST_URL).mock(return_value=httpx.Response(200, json=_document()))

    with client, pytest.raises(WebhookTestTimeoutError):
        client.webhook_test_deliveries.wait(TEST_ID, timeout=0)

    assert route.call_count == 1
    assert clock.slept == []


def test_the_timeout_error_is_not_retryable() -> None:
    error = WebhookTestTimeoutError(
        "still pending", delivery=WebhookTestDelivery._from_resource(_resource())
    )

    assert is_retryable(error) is False


@pytest.mark.parametrize("value", ["", ".", ".."], ids=["empty", "dot", "dot-dot"])
def test_wait_refuses_a_dot_segment_or_empty_id_before_any_request(
    respx_mock: respx.MockRouter, client: Ringivo, value: str
) -> None:
    route = respx_mock.get(url__startswith=TESTS_URL)

    with client, pytest.raises(ValueError):
        client.webhook_test_deliveries.wait(value)

    assert not route.called
