"""The customers surface again, awaited, and asserted on the WIRE.

The mirror of tests/test_customers.py. `AsyncCustomers` is a sibling of
`Customers` rather than a wrapper around it, so the query string it writes
and the path it builds are its own code and get their own assertions — the
imported page reader is the only half the two share.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from ringivo import ApiError, AsyncRingivo, Customer, CustomerPage

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
CUSTOMERS_URL = f"{BASE_URL}/v1/customers"
CUSTOMER_ID = "0198c4a1-7a10-7c3e-9d21-4f5a6b7c8d9e"
CUSTOMER_URL = f"{CUSTOMERS_URL}/{CUSTOMER_ID}"
OTHER_ID = "0198c4a1-9b21-7d4f-8e32-5a6b7c8d9e0f"
TENANT = "0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8"

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
def client() -> AsyncRingivo:
    return AsyncRingivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=SCOPES,
    )


def _customer_resource() -> dict[str, object]:
    return {
        "type": "customers",
        "id": CUSTOMER_ID,
        "attributes": {
            "name": "Acme Dental",
            "code": "jpz3k",
            "pbx": True,
            "transports": ["tls", "udp"],
        },
    }


@pytest.mark.anyio
async def test_list_builds_the_filter_and_page_query(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.get(CUSTOMERS_URL).mock(
        return_value=httpx.Response(
            200,
            json={"data": [_customer_resource()], "meta": {"page": {"nextCursor": "next-1"}}},
        )
    )

    async with client:
        page = await client.customers.list(code="jpz3k", before="0198c4a1", page_size=10)
        await client.customers.list(after="0198c4a2")

    request, forward = (call.request for call in route.calls)
    params = request.url.params

    assert isinstance(page, CustomerPage)
    assert page[0].code == "jpz3k"
    assert page.next_cursor == "next-1"
    assert request.url.path == "/v1/customers"
    assert params["filter[code]"] == "jpz3k"
    assert params["page[before]"] == "0198c4a1"
    assert params["page[size]"] == "10"
    assert "page[after]" not in params
    # A call that names no ids sends no id parameter: `ids` is opt-in.
    assert not any(key.startswith("filter[id]") for key in params.keys())
    # BOTH cursor directions, each on its own request.
    assert forward.url.params["page[after]"] == "0198c4a2"
    assert "page[before]" not in forward.url.params


@pytest.mark.anyio
async def test_list_with_no_arguments_sends_no_query_at_all(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    # No filter by id in particular: `ids` was not given, so nothing about
    # it reaches the wire.
    route = respx_mock.get(CUSTOMERS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    async with client:
        await client.customers.list()

    assert list(route.calls.last.request.url.params.keys()) == []


@pytest.mark.anyio
async def test_list_writes_one_bracketed_pair_per_id_in_the_order_given(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.get(CUSTOMERS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    async with client:
        await client.customers.list(ids=[CUSTOMER_ID])
        await client.customers.list(ids=[CUSTOMER_ID, OTHER_ID], code="jpz3k")
        await client.customers.list(ids=[], code="jpz3k")

    one, two, none = (call.request for call in route.calls)

    # One id is still the bracketed pair, never the bracketless key.
    assert list(one.url.params.multi_items()) == [("filter[id][]", CUSTOMER_ID)]
    assert "filter%5Bid%5D=" not in one.url.query.decode()

    # Two ids are two pairs, in the order given — not one comma-joined
    # value, which PHP reads as a single id nothing matches.
    assert [value for key, value in two.url.params.multi_items() if key == "filter[id][]"] == [
        CUSTOMER_ID,
        OTHER_ID,
    ]
    assert f"{CUSTOMER_ID}%2C{OTHER_ID}" not in two.url.query.decode()
    assert "filter%5Bid%5D=" not in two.url.query.decode()
    assert two.url.params["filter[code]"] == "jpz3k"

    # An empty list asks for nothing, exactly as `None` does.
    assert list(none.url.params.keys()) == ["filter[code]"]


@pytest.mark.anyio
async def test_one_bare_string_of_ids_is_refused_before_any_request_is_sent(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.get(CUSTOMERS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    async with client:
        with pytest.raises(ValueError, match="not one string"):
            await client.customers.list(ids=CUSTOMER_ID)  # type: ignore[arg-type]

    # The awaited twin refuses the same shape, in the same words, and before
    # any request — the list call and the token mint alike.
    assert route.call_count == 0
    assert not respx_mock.calls


@pytest.mark.anyio
async def test_a_generator_and_a_tuple_of_ids_reach_the_wire_intact(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.get(CUSTOMERS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    async with client:
        await client.customers.list(
            ids=(value for value in (CUSTOMER_ID, OTHER_ID)),  # type: ignore[arg-type]
        )
        await client.customers.list(ids=(CUSTOMER_ID, OTHER_ID))

    from_generator, from_tuple = (call.request for call in route.calls)

    # A one-shot iterable is materialised once, so it survives in order
    # rather than arriving as the repr of a spent generator.
    assert [
        value for key, value in from_generator.url.params.multi_items() if key == "filter[id][]"
    ] == [CUSTOMER_ID, OTHER_ID]
    assert from_tuple.url.query.decode() == from_generator.url.query.decode()


@pytest.mark.anyio
async def test_the_last_page_has_no_cursor_to_follow(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.get(CUSTOMERS_URL).mock(
        return_value=httpx.Response(
            200, json={"data": [], "meta": {"page": {"size": 25, "nextCursor": None, "total": 0}}}
        )
    )

    async with client:
        page = await client.customers.list()

    assert len(page) == 0
    assert page.next_cursor is None
    assert page.next_url is None


@pytest.mark.anyio
async def test_get_reads_a_jsonapi_document_into_the_public_dataclass(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.get(CUSTOMER_URL).mock(
        return_value=httpx.Response(200, json={"data": _customer_resource()})
    )

    async with client:
        customer = await client.customers.get(CUSTOMER_ID)

    assert isinstance(customer, Customer)
    assert customer.id == CUSTOMER_ID
    assert customer.name == "Acme Dental"
    assert customer.pbx is True
    assert customer.transports == ("tls", "udp")


@pytest.mark.anyio
async def test_a_customer_id_stays_inside_its_own_path_segment(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(200, json={"data": _customer_resource()})
    )

    async with client:
        await client.customers.get("../fax-accounts/secret")

    assert route.calls.last.request.url.raw_path == b"/v1/customers/..%2Ffax-accounts%2Fsecret"


@pytest.mark.anyio
async def test_an_empty_customer_id_is_refused_by_its_own_name(client: AsyncRingivo) -> None:
    async with client:
        with pytest.raises(ValueError, match="a customer id is required"):
            await client.customers.get("")


@pytest.mark.anyio
async def test_a_customer_not_on_your_account_raises_a_typed_404(
    respx_mock: respx.MockRouter, client: AsyncRingivo
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

    async with client:
        with pytest.raises(ApiError) as caught:
            await client.customers.get(CUSTOMER_ID)

    assert caught.value.status_code == 404
    assert caught.value.code == "not_found"
