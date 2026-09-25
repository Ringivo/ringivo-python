"""The fax-account-grant surface again, awaited, and asserted on the WIRE.

The mirror of tests/test_fax_account_users.py. `AsyncFaxAccountUsers` is a
sibling of `FaxAccountUsers` rather than a wrapper around it, so the
documents it builds and the query strings it writes are its own code and
get their own assertions.
"""

from __future__ import annotations

import json as jsonlib
from datetime import datetime, timezone

import httpx
import pytest
import respx

from ringivo import ApiError, AsyncRingivo, FaxAccountUser, FaxAccountUserPage

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
GRANTS_URL = f"{BASE_URL}/v1/fax-account-users"
GRANT_ID = "0198c4a1-6f70-7192-c394-5e6f70819203"
GRANT_URL = f"{GRANTS_URL}/{GRANT_ID}"
ACCOUNT_ID = "0198c4a1-3c4d-7e5f-9061-2b3c4d5e6f70"
USER_ID = "0198c4a1-7081-72a3-d4a5-6f7081920314"
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


def _grant_resource(**attribute_overrides: object) -> dict[str, object]:
    attributes: dict[str, object] = {
        "userEmail": "records@acme-vet.example",
        "createdAt": "2026-08-02T10:00:00.000000Z",
        "updatedAt": "2026-08-02T10:00:00.000000Z",
    }
    attributes.update(attribute_overrides)
    return {
        "type": "fax-account-users",
        "id": GRANT_ID,
        "attributes": attributes,
        "relationships": {
            "faxAccount": {"data": {"type": "fax-accounts", "id": ACCOUNT_ID}},
            "user": {"data": {"type": "users", "id": USER_ID}},
        },
    }


@pytest.mark.anyio
async def test_list_builds_the_filter_and_page_query(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.get(GRANTS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    async with client:
        page = await client.fax_account_users.list(
            fax_account=ACCOUNT_ID, user=USER_ID, page_size=50
        )

    params = route.calls.last.request.url.params

    assert isinstance(page, FaxAccountUserPage)
    # snake_case, the API's own spelling — see the sync twin's test for why
    # camelCasing it here would read back as a page of everything.
    assert params["filter[faxAccount]"] == ACCOUNT_ID
    assert params["filter[user]"] == USER_ID
    assert params["page[size]"] == "50"
    assert "page[after]" not in params


@pytest.mark.anyio
async def test_get_reads_both_halves_of_the_pair_off_the_relationships(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.get(GRANT_URL).mock(
        return_value=httpx.Response(200, json={"data": _grant_resource()})
    )

    async with client:
        grant = await client.fax_account_users.get(GRANT_ID)

    assert isinstance(grant, FaxAccountUser)
    assert grant.fax_account_id == ACCOUNT_ID
    assert grant.user_id == USER_ID
    assert grant.user_email == "records@acme-vet.example"
    assert grant.created_at == datetime(2026, 8, 2, 10, 0, 0, tzinfo=timezone.utc)


@pytest.mark.anyio
async def test_a_grant_id_stays_inside_its_own_path_segment(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    # The security control is imported rather than copied, and it is
    # asserted on this client too: a second copy would be a second thing to
    # get wrong, and an untested import is a claim rather than a fact.
    evil = "../fax-accounts/secret"
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(200, json={"data": _grant_resource()})
    )

    async with client:
        await client.fax_account_users.get(evil)

    assert (
        route.calls.last.request.url.raw_path
        == b"/v1/fax-account-users/..%2Ffax-accounts%2Fsecret"
    )


@pytest.mark.anyio
async def test_an_empty_grant_id_is_refused_by_its_own_name(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    async with client:
        with pytest.raises(ValueError, match="a fax account user id is required"):
            await client.fax_account_users.get("")

    assert respx_mock.calls.call_count == 0, "an empty id reached the wire"


@pytest.mark.anyio
async def test_create_posts_a_document_that_is_all_relationships(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.post(GRANTS_URL).mock(
        return_value=httpx.Response(201, json={"data": _grant_resource()})
    )

    async with client:
        grant = await client.fax_account_users.create(fax_account=ACCOUNT_ID, user=USER_ID)

    request = route.calls.last.request
    body = jsonlib.loads(request.content)

    assert request.headers["content-type"] == JSONAPI
    assert body["data"]["type"] == "fax-account-users"
    assert set(body["data"]) == {"type", "relationships"}
    assert body["data"]["relationships"]["faxAccount"]["data"]["id"] == ACCOUNT_ID
    assert body["data"]["relationships"]["user"]["data"]["id"] == USER_ID
    assert grant.id == GRANT_ID


@pytest.mark.anyio
async def test_delete_returns_none_and_surfaces_a_withdrawal_of_what_is_gone(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    # BOTH calls happen inside ONE `async with`: leaving the block closes the
    # client for good, so a second one would meet a closed transport rather
    # than the refusal this test is about. The two answers are queued on the
    # route instead — 204 first, then the 404.
    respx_mock.delete(GRANT_URL).mock(
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
        assert await client.fax_account_users.delete(GRANT_ID) is None

        with pytest.raises(ApiError) as caught:
            await client.fax_account_users.delete(GRANT_ID)

    assert caught.value.code == "not_found"
