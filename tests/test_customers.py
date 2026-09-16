"""The customers surface, asserted on the WIRE.

Two reads, and what is worth asserting differs between them. For `list()`
it is the QUERY, which is not observable from the return value: the two
filters it takes, the cursor paging, and the one shape the platform reads a
list of ids in — a separate `filter[id][]` pair for every id, never a
comma-joined value and never the bracketless key. For `get()` it is the
READING: every attribute the spec documents, the order of `transports`, and
the five phone-system fields that are null for a customer with no phone
system.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
import respx

from ringivo import ApiError, Customer, CustomerPage, Ringivo

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
CUSTOMERS_URL = f"{BASE_URL}/v1/customers"
CUSTOMER_ID = "0198c4a1-7a10-7c3e-9d21-4f5a6b7c8d9e"
CUSTOMER_URL = f"{CUSTOMERS_URL}/{CUSTOMER_ID}"
OTHER_ID = "0198c4a1-9b21-7d4f-8e32-5a6b7c8d9e0f"
TENANT = "0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8"
JSONAPI = "application/vnd.api+json"

SCOPES = ["customers:read"]


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


def _customer_resource(*, attributes: dict[str, object] | None = None) -> dict[str, object]:
    """The spec's own list example: a customer WITH a phone system."""
    merged: dict[str, object] = {
        "name": "Acme Dental",
        "code": "jpz3k",
        "country": "US",
        "addressLines": ["233 S Wacker Dr"],
        "city": "Chicago",
        "region": "IL",
        "postalCode": "60606",
        "timeZone": "America/Chicago",
        "dataResidencyCountry": "US",
        "regionPreference": "partner_default",
        "effectiveRegion": "use1",
        "pbx": True,
        "residential": False,
        "callLimit": 10,
        "callLimitExternal": 10,
        "transports": ["tls", "udp"],
        "provisioningState": "active",
        "createdAt": "2026-09-01T12:00:00.000000Z",
        "updatedAt": "2026-09-01T12:05:00.000000Z",
    }
    merged.update(attributes or {})
    return {"type": "customers", "id": CUSTOMER_ID, "attributes": merged}


# -- list ------------------------------------------------------------------


def test_list_builds_the_filter_and_page_query(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(CUSTOMERS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    with client:
        client.customers.list(code="jpz3k", after="0198c4a1", page_size=50)
        client.customers.list(before="0198c4a0")

    forward, backward = (call.request for call in route.calls)
    params = forward.url.params

    assert forward.url.path == "/v1/customers"
    assert params["filter[code]"] == "jpz3k"
    assert params["page[after]"] == "0198c4a1"
    assert params["page[size]"] == "50"
    assert "page[before]" not in params
    # A call that names no ids sends no id parameter, beside a code or
    # without one: `ids` is opt-in and leaks into nothing.
    assert not any(key.startswith("filter[id]") for key in params.keys())
    assert forward.headers["accept"] == JSONAPI

    # BOTH cursor directions, each on its own request: a walk that lost
    # either key would serve the first page again and never end.
    assert backward.url.params["page[before]"] == "0198c4a0"
    assert "page[after]" not in backward.url.params


def test_list_with_no_arguments_sends_no_query_at_all(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # No filter by id in particular: `ids` was not given, so nothing about
    # it reaches the wire.
    route = respx_mock.get(CUSTOMERS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    with client:
        client.customers.list()

    assert list(route.calls.last.request.url.params.keys()) == []


def test_one_id_is_one_bracketed_filter_id_pair(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(CUSTOMERS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    with client:
        client.customers.list(ids=[CUSTOMER_ID])

    request = route.calls.last.request
    # The BRACKETED key, and only it: one id is still `filter[id][]=<id>`.
    assert list(request.url.params.multi_items()) == [("filter[id][]", CUSTOMER_ID)]
    # Sent bracketless, the platform refuses the call with a 400.
    assert "filter%5Bid%5D=" not in request.url.query.decode()


def test_two_ids_are_two_pairs_in_the_order_given_and_never_comma_joined(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(CUSTOMERS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    with client:
        client.customers.list(ids=[CUSTOMER_ID, OTHER_ID], code="jpz3k")

    request = route.calls.last.request
    query = request.url.query.decode()

    # One pair per id, in the order the caller gave them.
    assert [value for key, value in request.url.params.multi_items() if key == "filter[id][]"] == [
        CUSTOMER_ID,
        OTHER_ID,
    ]
    # NOT one comma-joined value: that is a single id nothing matches.
    assert f"{CUSTOMER_ID}%2C{OTHER_ID}" not in query
    # NOT the bracketless key: PHP keeps only the last of repeated
    # `filter[id]=` pairs, as one string, and the filter does not read a
    # string as a list.
    assert "filter%5Bid%5D=" not in query
    # It narrows alongside `code` rather than replacing it.
    assert request.url.params["filter[code]"] == "jpz3k"


def test_an_empty_id_list_sends_no_id_parameter_at_all(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(CUSTOMERS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    with client:
        client.customers.list(ids=[], code="jpz3k")

    request = route.calls.last.request
    # `ids=[]` asks for nothing, exactly as `ids=None` does — and in
    # particular not an empty `filter[id][]=`, which is a value.
    assert not any(key.startswith("filter[id]") for key in request.url.params.keys())
    assert list(request.url.params.keys()) == ["filter[code]"]


def test_list_reads_the_customers_and_the_next_cursor_from_page_meta(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(CUSTOMERS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [_customer_resource()],
                "links": {"next": f"{CUSTOMERS_URL}?page%5Bafter%5D=0198c4a1-next"},
                "meta": {"page": {"size": 25, "nextCursor": "0198c4a1-next", "total": 2}},
            },
        )
    )

    with client:
        page = client.customers.list()

    assert isinstance(page, CustomerPage)
    assert len(page) == 1
    assert list(page)[0].id == CUSTOMER_ID
    assert page[0].name == "Acme Dental"
    assert page.next_cursor == "0198c4a1-next"
    assert page.next_url is not None and "page%5Bafter%5D" in page.next_url
    # The exact total is not a field; the page keeps it in `raw`, as its
    # docstring says.
    assert page.raw["meta"]["page"]["total"] == 2


def test_the_last_page_has_no_cursor_to_follow(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(CUSTOMERS_URL).mock(
        return_value=httpx.Response(
            200, json={"data": [], "meta": {"page": {"size": 25, "nextCursor": None, "total": 0}}}
        )
    )

    with client:
        page = client.customers.list()

    assert len(page) == 0
    assert page.next_cursor is None
    assert page.next_url is None


# -- get -------------------------------------------------------------------


def test_get_reads_every_documented_attribute_into_the_public_dataclass(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(CUSTOMER_URL).mock(
        return_value=httpx.Response(200, json={"data": _customer_resource()})
    )

    with client:
        customer = client.customers.get(CUSTOMER_ID)

    assert route.calls.last.request.headers["accept"] == JSONAPI
    assert isinstance(customer, Customer)
    assert customer.id == CUSTOMER_ID
    assert customer.name == "Acme Dental"
    assert customer.code == "jpz3k"
    assert customer.country == "US"
    assert customer.address_lines == ("233 S Wacker Dr",)
    assert customer.city == "Chicago"
    assert customer.region == "IL"
    assert customer.postal_code == "60606"
    assert customer.time_zone == "America/Chicago"
    assert customer.data_residency_country == "US"
    assert customer.region_preference == "partner_default"
    assert customer.effective_region == "use1"
    assert customer.pbx is True
    assert customer.residential is False
    assert customer.call_limit == 10
    assert customer.call_limit_external == 10
    # The ORDER is data — the order the transports are offered in DNS.
    assert customer.transports == ("tls", "udp")
    assert customer.provisioning_state == "active"
    assert customer.created_at == datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert customer.updated_at == datetime(2026, 9, 1, 12, 5, 0, tzinfo=timezone.utc)
    assert customer.raw["type"] == "customers"


def test_a_customer_without_a_phone_system_reads_none_for_the_five_phone_system_fields(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The spec's own `get` example: `pbx: false`, and the five fields after
    # it null.
    resource = _customer_resource(
        attributes={
            "pbx": False,
            "residential": None,
            "callLimit": None,
            "callLimitExternal": None,
            "transports": None,
            "provisioningState": None,
        }
    )
    respx_mock.get(CUSTOMER_URL).mock(return_value=httpx.Response(200, json={"data": resource}))

    with client:
        customer = client.customers.get(CUSTOMER_ID)

    assert customer.pbx is False
    assert customer.residential is None
    assert customer.call_limit is None
    assert customer.call_limit_external is None
    assert customer.transports is None
    assert customer.provisioning_state is None


def test_values_outside_the_spec_vocabulary_pass_through_unchanged(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The three enum-like fields are passed through as text, not checked
    # against a copy of today's vocabulary. A value the platform adds later
    # must arrive as sent — and `transports` keeps its order, because the
    # order is the DNS preference.
    resource = _customer_resource(
        attributes={
            "regionPreference": "euw1",
            "transports": ["wss", "tls"],
            "provisioningState": "some_future_state",
        }
    )
    respx_mock.get(CUSTOMER_URL).mock(return_value=httpx.Response(200, json={"data": resource}))

    with client:
        customer = client.customers.get(CUSTOMER_ID)

    assert customer.region_preference == "euw1"
    assert customer.transports == ("wss", "tls")
    assert customer.provisioning_state == "some_future_state"


def test_a_customer_id_stays_inside_its_own_path_segment(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(200, json={"data": _customer_resource()})
    )

    with client:
        client.customers.get("../fax-accounts/secret")

    assert route.calls.last.request.url.raw_path == b"/v1/customers/..%2Ffax-accounts%2Fsecret"


def test_an_empty_customer_id_is_refused_by_its_own_name(client: Ringivo) -> None:
    with client, pytest.raises(ValueError, match="a customer id is required"):
        client.customers.get("")


def test_a_customer_not_on_your_account_raises_a_typed_404(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(CUSTOMER_URL).mock(
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
        client.customers.get(CUSTOMER_ID)

    assert caught.value.status_code == 404
    assert caught.value.code == "not_found"
