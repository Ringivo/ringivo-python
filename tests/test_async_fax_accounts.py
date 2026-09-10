"""The fax-account surface again, awaited, and asserted on the WIRE.

The mirror of tests/test_fax_accounts.py. `AsyncFaxAccounts` is a sibling
of `FaxAccounts` rather than a wrapper around it, so the documents it
builds and the query strings it writes are its own code and get their own
assertions.
"""

from __future__ import annotations

import json as jsonlib
from datetime import datetime, timezone

import httpx
import pytest
import respx

from ringivo import ApiError, AsyncRingivo, FaxAccount, FaxAccountNumber, FaxAccountPage

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
ACCOUNTS_URL = f"{BASE_URL}/v1/fax-accounts"
ACCOUNT_ID = "0198c4a1-3c4d-7e5f-9061-2b3c4d5e6f70"
ACCOUNT_URL = f"{ACCOUNTS_URL}/{ACCOUNT_ID}"
NUMBERS_URL = f"{ACCOUNT_URL}/numbers"
CUSTOMER_ID = "0198c4a1-4d5e-7f60-a172-3c4d5e6f7081"
NUMBER_ID = "0198c4a1-5e6f-7081-b283-4d5e6f708192"
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
                "scope": "fax:read fax-accounts:write",
                "scopes": ["fax:read", "fax-accounts:write"],
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
        scopes=["fax:read", "fax-accounts:write"],
    )


def _account_resource(**attribute_overrides: object) -> dict[str, object]:
    attributes: dict[str, object] = {
        "name": "Front desk",
        "headerText": "ACME VETERINARY",
        "defaultFromE164": "+14075550100",
        "retentionDays": 365,
        "retentionPages": None,
        "status": "active",
        "createdAt": "2026-08-01T09:00:00.000000Z",
        "updatedAt": "2026-08-16T11:00:00.000000Z",
    }
    attributes.update(attribute_overrides)
    return {
        "type": "fax-accounts",
        "id": ACCOUNT_ID,
        "attributes": attributes,
        "relationships": {
            "customer": {"data": {"type": "customers", "id": CUSTOMER_ID}},
        },
    }


def _number_resource(number_id: str = NUMBER_ID, e164: str = "+14075550111") -> dict[str, object]:
    return {
        "type": "phone-numbers",
        "id": number_id,
        "attributes": {
            "e164": e164,
            "status": "active",
            "country": "US",
            "activatedAt": "2026-07-30T14:11:00.000000Z",
            "createdAt": "2026-07-30T14:10:00.000000Z",
        },
    }


@pytest.mark.anyio
async def test_list_builds_the_filter_and_page_query(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.get(ACCOUNTS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    async with client:
        page = await client.fax_accounts.list(customer=CUSTOMER_ID, status="active", page_size=50)

    params = route.calls.last.request.url.params

    assert isinstance(page, FaxAccountPage)
    assert params["filter[customer]"] == CUSTOMER_ID
    assert params["filter[status]"] == "active"
    assert params["page[size]"] == "50"
    assert "page[after]" not in params


@pytest.mark.anyio
async def test_get_reads_a_jsonapi_document_into_the_public_dataclass(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.get(ACCOUNT_URL).mock(
        return_value=httpx.Response(200, json={"data": _account_resource()})
    )

    async with client:
        account = await client.fax_accounts.get(ACCOUNT_ID)

    assert isinstance(account, FaxAccount)
    assert account.retention_days == 365
    assert account.retention_pages is None
    assert account.customer_id == CUSTOMER_ID
    assert account.created_at == datetime(2026, 8, 1, 9, 0, 0, tzinfo=timezone.utc)


@pytest.mark.anyio
async def test_a_fax_account_id_stays_inside_its_own_path_segment(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(200, json={"data": _account_resource()})
    )

    async with client:
        await client.fax_accounts.get("../faxes/secret")

    assert route.calls.last.request.url.raw_path == b"/v1/fax-accounts/..%2Ffaxes%2Fsecret"


@pytest.mark.anyio
async def test_numbers_walks_every_page_and_returns_them_all(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    pages = [
        httpx.Response(
            200,
            json={
                "data": [_number_resource()],
                "meta": {"page": {"size": 100, "nextCursor": "cursor-2"}},
            },
        ),
        httpx.Response(
            200,
            json={
                "data": [_number_resource("0198c4a1-6f70-8192-c394-5e6f70819203", "+14075550112")],
                "meta": {"page": {"size": 100, "nextCursor": None}},
            },
        ),
    ]
    route = respx_mock.get(NUMBERS_URL).mock(side_effect=pages)

    async with client:
        numbers = await client.fax_accounts.numbers(ACCOUNT_ID)

    assert len(numbers) == 2
    assert isinstance(numbers[0], FaxAccountNumber)
    assert [n.e164 for n in numbers] == ["+14075550111", "+14075550112"]
    assert route.calls[1].request.url.params["page[after]"] == "cursor-2"


@pytest.mark.anyio
async def test_numbers_refuses_a_repeated_cursor_rather_than_walking_for_ever(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    from ringivo import RingivoError

    respx_mock.get(NUMBERS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [_number_resource()],
                "meta": {"page": {"size": 100, "nextCursor": "stuck"}},
            },
        )
    )

    async with client:
        with pytest.raises(RingivoError, match="served the cursor 'stuck' twice"):
            await client.fax_accounts.numbers(ACCOUNT_ID)


@pytest.mark.anyio
async def test_create_posts_a_jsonapi_document_naming_the_customer(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.post(ACCOUNTS_URL).mock(
        return_value=httpx.Response(201, json={"data": _account_resource()})
    )

    async with client:
        await client.fax_accounts.create(
            customer=CUSTOMER_ID, name="Front desk", retention_pages=500
        )

    request = route.calls.last.request
    body = jsonlib.loads(request.content)

    assert request.headers["content-type"] == JSONAPI
    assert body["data"]["type"] == "fax-accounts"
    assert body["data"]["attributes"] == {"name": "Front desk", "retentionPages": 500}
    assert body["data"]["relationships"]["customer"]["data"]["id"] == CUSTOMER_ID


@pytest.mark.anyio
async def test_update_sends_only_what_was_named(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.patch(ACCOUNT_URL).mock(
        return_value=httpx.Response(200, json={"data": _account_resource(status="suspended")})
    )

    async with client:
        account = await client.fax_accounts.update(ACCOUNT_ID, status="suspended")

    body = jsonlib.loads(route.calls.last.request.content)

    assert body["data"]["id"] == ACCOUNT_ID
    assert body["data"]["attributes"] == {"status": "suspended"}
    assert account.status == "suspended"


@pytest.mark.anyio
async def test_update_refuses_a_change_that_changes_nothing(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    async with client:
        with pytest.raises(ValueError, match="at least one field to change"):
            await client.fax_accounts.update(ACCOUNT_ID)

    assert respx_mock.calls.call_count == 0, "an empty update reached the wire"


@pytest.mark.anyio
async def test_delete_returns_none_and_surfaces_the_routed_numbers_refusal(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    # BOTH calls happen inside ONE `async with`: leaving the block closes the
    # client for good, so a second one would meet a closed transport rather
    # than the refusal this test is about. The two answers are queued on the
    # route instead — 204 first, then the published 409.
    respx_mock.delete(ACCOUNT_URL).mock(
        side_effect=[
            httpx.Response(204),
            httpx.Response(
                409,
                json={
                    "errors": [
                        {
                            "status": "409",
                            "code": "fax_account_has_routed_numbers",
                            "title": "Conflict",
                            "detail": "Numbers still route to this fax account.",
                        }
                    ]
                },
            ),
        ]
    )

    async with client:
        assert await client.fax_accounts.delete(ACCOUNT_ID) is None

        with pytest.raises(ApiError) as caught:
            await client.fax_accounts.delete(ACCOUNT_ID)

    assert caught.value.code == "fax_account_has_routed_numbers"
