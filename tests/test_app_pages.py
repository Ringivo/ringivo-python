"""The app page calls, asserted on the WIRE and against the spec's examples.

Six calls on two namespaces: set, read and clear, for a customer and for
one subscriber. What is worth asserting is what the return value cannot
show — the path, the method, and the FLAT JSON body a set sends (not a
JSON:API document, and `icon` only when given) — and the reading of the
answer: the spec's own 200 examples, `page` and `effective` as None for
`null`, and a refusal as an `ApiError` with the member it names.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from ringivo import ApiError, AppPage, AppPageValue, Ringivo, is_retryable

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
def client() -> Ringivo:
    return Ringivo(
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


def _set_example(spec: dict[str, Any], path: str) -> dict[str, Any]:
    """The spec's request example for a set: the body a caller would send."""
    return spec["paths"][path]["post"]["requestBody"]["content"]["application/json"]["example"]


def _members(value: AppPageValue | None) -> dict[str, str | None] | None:
    """A page's three members, to compare with the JSON it was read from."""
    if value is None:
        return None
    return {"url": value.url, "label": value.label, "icon": value.icon}


# -- customer --------------------------------------------------------------


def test_set_sends_flat_json_to_the_customers_page_and_reads_the_answer(
    respx_mock: respx.MockRouter, client: Ringivo, openapi_spec: dict[str, Any]
) -> None:
    sent = _set_example(openapi_spec, CUSTOMER_PATH)
    answer = _example(openapi_spec, CUSTOMER_PATH, "post", "200")
    route = respx_mock.post(CUSTOMER_PAGE_URL).mock(return_value=httpx.Response(200, json=answer))

    with client:
        page = client.customers.set_app_page(
            CUSTOMER_ID, url=sent["url"], label=sent["label"], icon=sent["icon"]
        )

    request = route.calls.last.request
    # FLAT JSON: the three members at the top level, and no `data` member,
    # which the API refuses with a 422 on this route.
    assert json.loads(request.content) == {
        "url": sent["url"],
        "label": sent["label"],
        "icon": sent["icon"],
    }
    assert request.headers["content-type"] == "application/json"
    assert request.headers["accept"] == JSONAPI

    attributes = answer["data"]["attributes"]
    assert isinstance(page, AppPage)
    assert page.id == answer["data"]["id"]
    assert _members(page.page) == attributes["page"]
    assert page.complete is attributes["complete"]
    assert _members(page.effective) == attributes["effective"]
    assert page.source == "customer"
    assert page.raw == answer["data"]


def test_set_with_no_icon_leaves_icon_off_the_body(
    respx_mock: respx.MockRouter, client: Ringivo, openapi_spec: dict[str, Any]
) -> None:
    answer = _example(openapi_spec, CUSTOMER_PATH, "post", "200")
    route = respx_mock.post(CUSTOMER_PAGE_URL).mock(return_value=httpx.Response(200, json=answer))

    with client:
        client.customers.set_app_page(
            CUSTOMER_ID, url="https://app.example.com/phone", label="Missed calls"
        )

    # Absent, not null: the API then uses `open_in_new`.
    assert json.loads(route.calls.last.request.content) == {
        "url": "https://app.example.com/phone",
        "label": "Missed calls",
    }


def test_get_reads_the_customers_page(
    respx_mock: respx.MockRouter, client: Ringivo, openapi_spec: dict[str, Any]
) -> None:
    answer = _example(openapi_spec, CUSTOMER_PATH, "get", "200")
    route = respx_mock.get(CUSTOMER_PAGE_URL).mock(return_value=httpx.Response(200, json=answer))

    with client:
        page = client.customers.get_app_page(CUSTOMER_ID)

    assert route.called
    assert page.id == CUSTOMER_ID
    assert _members(page.page) == answer["data"]["attributes"]["page"]
    assert page.complete is True
    assert page.source == "customer"


def test_a_customer_with_no_page_of_its_own_reads_page_none(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # No page of its own, and the menu shows a page set for many customers.
    shared = {"url": "https://help.example.com", "label": "Help", "icon": "help"}
    respx_mock.get(CUSTOMER_PAGE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "type": "app-pages",
                    "id": CUSTOMER_ID,
                    "attributes": {
                        "page": None,
                        "complete": False,
                        "effective": shared,
                        "source": "default",
                    },
                }
            },
        )
    )

    with client:
        page = client.customers.get_app_page(CUSTOMER_ID)

    assert page.page is None
    assert page.complete is False
    assert _members(page.effective) == shared
    assert page.source == "default"


def test_an_empty_menu_reads_effective_and_source_none(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(CUSTOMER_PAGE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "type": "app-pages",
                    "id": CUSTOMER_ID,
                    "attributes": {
                        "page": None,
                        "complete": True,
                        "effective": None,
                        "source": None,
                    },
                }
            },
        )
    )

    with client:
        page = client.customers.get_app_page(CUSTOMER_ID)

    assert (page.page, page.effective, page.source) == (None, None, None)


def test_clear_deletes_the_customers_page(respx_mock: respx.MockRouter, client: Ringivo) -> None:
    route = respx_mock.delete(CUSTOMER_PAGE_URL).mock(return_value=httpx.Response(204))

    with client:
        cleared = client.customers.clear_app_page(CUSTOMER_ID)

    assert route.call_count == 1
    assert cleared is None


def test_a_refused_url_is_an_api_error_that_names_the_member(
    respx_mock: respx.MockRouter, client: Ringivo, openapi_spec: dict[str, Any]
) -> None:
    refusal = _example(openapi_spec, CUSTOMER_PATH, "post", "422")
    respx_mock.post(CUSTOMER_PAGE_URL).mock(return_value=httpx.Response(422, json=refusal))

    with client, pytest.raises(ApiError) as caught:
        client.customers.set_app_page(
            CUSTOMER_ID, url="https://app.example.com/phone", label="Missed calls"
        )

    assert caught.value.status_code == 422
    assert caught.value.errors[0].source == {"pointer": "/url"}


def test_a_set_that_failed_part_way_says_how_much_changed(
    respx_mock: respx.MockRouter, client: Ringivo, openapi_spec: dict[str, Any]
) -> None:
    failed = openapi_spec["components"]["responses"]["AppPagePhoneSystemFailed"]["content"][
        JSONAPI
    ]["example"]
    respx_mock.post(CUSTOMER_PAGE_URL).mock(return_value=httpx.Response(502, json=failed))

    with client, pytest.raises(ApiError) as caught:
        client.customers.set_app_page(
            CUSTOMER_ID, url="https://app.example.com/phone", label="Missed calls"
        )

    assert caught.value.status_code == 502
    assert caught.value.errors[0].meta == {"changedSettings": 4}
    assert is_retryable(caught.value) is True


def test_a_change_in_progress_409_has_no_code_and_is_retryable_says_false(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The API's own shape: a title and no `code`. The README documents that
    # `is_retryable()` is False for it and that a caller matches the title.
    respx_mock.post(CUSTOMER_PAGE_URL).mock(
        return_value=httpx.Response(
            409, json={"errors": [{"status": "409", "title": "Change in progress"}]}
        )
    )

    with client, pytest.raises(ApiError) as caught:
        client.customers.set_app_page(
            CUSTOMER_ID, url="https://app.example.com/phone", label="Missed calls"
        )

    assert caught.value.status_code == 409
    assert caught.value.errors[0].title == "Change in progress"
    assert is_retryable(caught.value) is False


# -- subscriber ------------------------------------------------------------


def test_set_sends_flat_json_to_the_subscribers_page_and_reads_the_answer(
    respx_mock: respx.MockRouter, client: Ringivo, openapi_spec: dict[str, Any]
) -> None:
    sent = _set_example(openapi_spec, SUBSCRIBER_PATH)
    answer = _example(openapi_spec, SUBSCRIBER_PATH, "post", "200")
    route = respx_mock.post(SUBSCRIBER_PAGE_URL).mock(return_value=httpx.Response(200, json=answer))

    with client:
        page = client.pbx.subscribers.set_app_page(
            SUBSCRIBER_ID, url=sent["url"], label=sent["label"], icon=sent["icon"]
        )

    request = route.calls.last.request
    assert json.loads(request.content) == {
        "url": sent["url"],
        "label": sent["label"],
        "icon": sent["icon"],
    }
    assert request.headers["content-type"] == "application/json"
    assert page.id == answer["data"]["id"]
    assert page.source == answer["data"]["attributes"]["source"]
    assert _members(page.effective) == answer["data"]["attributes"]["effective"]


def test_get_reads_the_subscribers_page(
    respx_mock: respx.MockRouter, client: Ringivo, openapi_spec: dict[str, Any]
) -> None:
    answer = _example(openapi_spec, SUBSCRIBER_PATH, "get", "200")
    respx_mock.get(SUBSCRIBER_PAGE_URL).mock(return_value=httpx.Response(200, json=answer))

    with client:
        page = client.pbx.subscribers.get_app_page(SUBSCRIBER_ID)

    assert page.id == SUBSCRIBER_ID
    assert _members(page.page) == answer["data"]["attributes"]["page"]
    assert page.source == "subscriber"


def test_clear_deletes_the_subscribers_page(respx_mock: respx.MockRouter, client: Ringivo) -> None:
    route = respx_mock.delete(SUBSCRIBER_PAGE_URL).mock(return_value=httpx.Response(204))

    with client:
        cleared = client.pbx.subscribers.clear_app_page(SUBSCRIBER_ID)

    assert route.call_count == 1
    assert cleared is None


def test_the_ids_are_escaped_into_the_path(respx_mock: respx.MockRouter, client: Ringivo) -> None:
    # A slash in an id stays inside its one path segment.
    route = respx_mock.delete(f"{BASE_URL}/v1/pbx/subscribers/a%2Fb/app-page").mock(
        return_value=httpx.Response(204)
    )

    with client:
        client.pbx.subscribers.clear_app_page("a/b")

    assert route.called
