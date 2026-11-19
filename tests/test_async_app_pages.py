"""The app page calls again, awaited, and asserted on the WIRE.

The mirror of tests/test_app_pages.py. The async methods are siblings of
the sync ones rather than wrappers, so the path, the method and the body
each one sends are their own code and get their own assertions. The body
builder and the answer reader are the halves the two share.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from ringivo import ApiError, AppPage, AsyncRingivo

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
CUSTOMER_ID = "0198c4a1-9203-74c5-a6d7-819203142536"
SUBSCRIBER_ID = "0198c4a1-2b3c-7d4e-8f50-1a2b3c4d5e6f"
CUSTOMER_PAGE_URL = f"{BASE_URL}/v1/customers/{CUSTOMER_ID}/app-page"
SUBSCRIBER_PAGE_URL = f"{BASE_URL}/v1/pbx/subscribers/{SUBSCRIBER_ID}/app-page"
TENANT = "0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8"
JSONAPI = "application/vnd.api+json"

SCOPES = ["pbx-app-pages:write"]

CUSTOMER_PATH = "/v1/customers/{customer}/app-page"
SUBSCRIBER_PATH = "/v1/pbx/subscribers/{subscriber}/app-page"


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
                "scope": " ".join(SCOPES),
                "scopes": SCOPES,
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
        scopes=SCOPES,
    )


def _example(spec: dict[str, Any], path: str, method: str, status: str) -> dict[str, Any]:
    """One response example of the vendored spec, as the server would send it."""
    responses = spec["paths"][path][method]["responses"]
    return responses[status]["content"][JSONAPI]["example"]


@pytest.mark.anyio
async def test_set_sends_flat_json_to_the_customers_page(
    respx_mock: respx.MockRouter, client: AsyncRingivo, openapi_spec: dict[str, Any]
) -> None:
    answer = _example(openapi_spec, CUSTOMER_PATH, "post", "200")
    route = respx_mock.post(CUSTOMER_PAGE_URL).mock(return_value=httpx.Response(200, json=answer))

    async with client:
        page = await client.customers.set_app_page(
            CUSTOMER_ID, url="https://app.example.com/phone", label="Missed calls"
        )

    request = route.calls.last.request
    assert json.loads(request.content) == {
        "url": "https://app.example.com/phone",
        "label": "Missed calls",
    }
    assert request.headers["content-type"] == "application/json"
    assert request.headers["accept"] == JSONAPI
    assert isinstance(page, AppPage)
    assert page.id == answer["data"]["id"]
    assert page.source == "customer"


@pytest.mark.anyio
async def test_get_reads_the_customers_page(
    respx_mock: respx.MockRouter, client: AsyncRingivo, openapi_spec: dict[str, Any]
) -> None:
    answer = _example(openapi_spec, CUSTOMER_PATH, "get", "200")
    respx_mock.get(CUSTOMER_PAGE_URL).mock(return_value=httpx.Response(200, json=answer))

    async with client:
        page = await client.customers.get_app_page(CUSTOMER_ID)

    assert page.page is not None
    assert page.page.url == answer["data"]["attributes"]["page"]["url"]
    assert page.complete is True


@pytest.mark.anyio
async def test_clear_deletes_the_customers_page(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.delete(CUSTOMER_PAGE_URL).mock(return_value=httpx.Response(204))

    async with client:
        cleared = await client.customers.clear_app_page(CUSTOMER_ID)

    assert route.call_count == 1
    assert cleared is None


@pytest.mark.anyio
async def test_set_sends_flat_json_to_the_subscribers_page(
    respx_mock: respx.MockRouter, client: AsyncRingivo, openapi_spec: dict[str, Any]
) -> None:
    answer = _example(openapi_spec, SUBSCRIBER_PATH, "post", "200")
    route = respx_mock.post(SUBSCRIBER_PAGE_URL).mock(return_value=httpx.Response(200, json=answer))

    async with client:
        page = await client.pbx.subscribers.set_app_page(
            SUBSCRIBER_ID,
            url="https://app.example.com/phone",
            label="Missed calls",
            icon="call_missed",
        )

    assert json.loads(route.calls.last.request.content) == {
        "url": "https://app.example.com/phone",
        "label": "Missed calls",
        "icon": "call_missed",
    }
    assert page.id == answer["data"]["id"]


@pytest.mark.anyio
async def test_get_reads_the_subscribers_page(
    respx_mock: respx.MockRouter, client: AsyncRingivo, openapi_spec: dict[str, Any]
) -> None:
    answer = _example(openapi_spec, SUBSCRIBER_PATH, "get", "200")
    respx_mock.get(SUBSCRIBER_PAGE_URL).mock(return_value=httpx.Response(200, json=answer))

    async with client:
        page = await client.pbx.subscribers.get_app_page(SUBSCRIBER_ID)

    assert page.id == SUBSCRIBER_ID
    assert page.source == "subscriber"


@pytest.mark.anyio
async def test_clear_deletes_the_subscribers_page(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.delete(SUBSCRIBER_PAGE_URL).mock(return_value=httpx.Response(204))

    async with client:
        await client.pbx.subscribers.clear_app_page(SUBSCRIBER_ID)

    assert route.call_count == 1


@pytest.mark.anyio
async def test_a_refusal_is_an_api_error(
    respx_mock: respx.MockRouter, client: AsyncRingivo, openapi_spec: dict[str, Any]
) -> None:
    refusal = _example(openapi_spec, SUBSCRIBER_PATH, "post", "422")
    respx_mock.post(SUBSCRIBER_PAGE_URL).mock(return_value=httpx.Response(422, json=refusal))

    async with client:
        with pytest.raises(ApiError) as caught:
            await client.pbx.subscribers.set_app_page(
                SUBSCRIBER_ID, url="https://app.example.com/phone", label="Missed calls"
            )

    assert caught.value.status_code == 422
    assert caught.value.errors[0].source == {"pointer": "/url"}
