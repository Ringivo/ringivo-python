"""The fax-account-grant surface, asserted on the WIRE.

The mirror of tests/test_fax_accounts.py, and for the same reason: every
test here checks the request that went out or the object that came back,
never an internal call. `list()`'s whole job is to build a query string and
`create()`'s is to build a JSON:API document, and neither is observable
from the return value alone.

Two things about this resource shape the assertions below. Its write body
is ALL RELATIONSHIPS — a grant has no attributes a caller writes — and its
account filter is `filter[faxAccount]`, camelCase like its relationships
since the API's v1 naming cleanup. Both are asserted rather than assumed:
a filter the API does not recognise is refused with a 400, and the 0.15
bridge's fallback to the old spelling is pinned in test_filter_bridge.py.
"""

from __future__ import annotations

import json as jsonlib
from datetime import datetime, timezone

import httpx
import pytest
import respx

from ringivo import ApiError, FaxAccountUser, FaxAccountUserPage, Ringivo

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
    """Every test here needs a credential to have been minted, not tested.

    respx's own `respx_mock` fixture, rather than the `@respx.mock`
    decorator, because a decorator starts AFTER fixtures run — routes
    registered here would then survive into the next test.
    """
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
def client() -> Ringivo:
    # The scopes this module's calls need, and they are NOT the same on both
    # halves: `fax:read` lists and reads a grant, `fax-accounts:write` makes
    # and withdraws one. That split is the whole design — reading an
    # account's content is grant-gated, administering the account is
    # permission-gated.
    return Ringivo(
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


# -- list ------------------------------------------------------------------


def test_list_builds_the_filter_and_page_query(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(GRANTS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    with client:
        client.fax_account_users.list(
            fax_account=ACCOUNT_ID,
            user=USER_ID,
            page_size=50,
            after="0198c4a1",
        )

    params = route.calls.last.request.url.params

    # camelCase since the API's v1 naming cleanup, like the relationships
    # the two filters narrow (`faxAccount`, `user`). The old spelling is
    # never sent first; see test_filter_bridge.py for when it is sent at all.
    assert params["filter[faxAccount]"] == ACCOUNT_ID
    assert "filter[fax_account]" not in params
    assert params["filter[user]"] == USER_ID
    assert params["page[size]"] == "50"
    assert params["page[after]"] == "0198c4a1"
    # An unset filter is absent, not empty: `filter[user]=` would be a 400
    # rather than "no opinion".
    assert "page[before]" not in params
    assert route.calls.last.request.headers["accept"] == JSONAPI


def test_list_asks_for_one_account_without_naming_a_user(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # "Who can see this account's faxes?" — the question this collection
    # exists to answer, and the one filter that must reach the wire alone.
    route = respx_mock.get(GRANTS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    with client:
        client.fax_account_users.list(fax_account=ACCOUNT_ID)

    params = route.calls.last.request.url.params

    assert params["filter[faxAccount]"] == ACCOUNT_ID
    assert "filter[user]" not in params


def test_list_reads_the_grants_and_the_next_cursor_from_page_meta(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(GRANTS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [_grant_resource()],
                "links": {"next": f"{GRANTS_URL}?page%5Bafter%5D=0198c4a1-next"},
                "meta": {"page": {"size": 25, "nextCursor": "0198c4a1-next"}},
            },
        )
    )

    with client:
        page = client.fax_account_users.list()

    assert isinstance(page, FaxAccountUserPage)
    assert len(page) == 1
    assert list(page)[0].id == GRANT_ID
    assert page[0].user_email == "records@acme-vet.example"
    assert page.next_cursor == "0198c4a1-next"
    assert page.next_url is not None and "page%5Bafter%5D" in page.next_url


def test_the_last_page_has_no_cursor_to_follow(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # An empty page is a real answer here: nobody has been granted this
    # account. That is not the same as an account that does not exist, which
    # is a 404 on the filter's own id.
    respx_mock.get(GRANTS_URL).mock(
        return_value=httpx.Response(
            200, json={"data": [], "meta": {"page": {"size": 25, "nextCursor": None}}}
        )
    )

    with client:
        page = client.fax_account_users.list(fax_account=ACCOUNT_ID)

    assert len(page) == 0
    assert page.next_cursor is None
    assert page.next_url is None


# -- get -------------------------------------------------------------------


def test_get_reads_both_halves_of_the_pair_off_the_relationships(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(GRANT_URL).mock(
        return_value=httpx.Response(200, json={"data": _grant_resource()})
    )

    with client:
        grant = client.fax_account_users.get(GRANT_ID)

    assert isinstance(grant, FaxAccountUser)
    assert grant.id == GRANT_ID
    # THE SUBSTANCE OF A GRANT IS THE PAIR, and neither half is an
    # attribute: both are read out of the relationship linkages.
    assert grant.fax_account_id == ACCOUNT_ID
    assert grant.user_id == USER_ID
    assert grant.user_email == "records@acme-vet.example"
    assert grant.created_at == datetime(2026, 8, 2, 10, 0, 0, tzinfo=timezone.utc)
    assert grant.updated_at == datetime(2026, 8, 2, 10, 0, 0, tzinfo=timezone.utc)
    # The whole resource object is kept, so a member the API adds after this
    # release still reaches the caller.
    assert grant.raw["type"] == "fax-account-users"


def test_a_relationship_without_linkage_is_a_missing_reading_rather_than_a_crash(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # A JSON:API server may answer a relationship with `links` alone. That is
    # legal, it says nothing about the grant, and it must not raise — the
    # linkage is still in `raw` either way.
    resource = _grant_resource()
    resource["relationships"] = {
        "faxAccount": {"links": {"self": f"{GRANT_URL}/relationships/faxAccount"}},
        "user": {"data": {"type": "users", "id": USER_ID}},
    }
    respx_mock.get(GRANT_URL).mock(return_value=httpx.Response(200, json={"data": resource}))

    with client:
        grant = client.fax_account_users.get(GRANT_ID)

    assert grant.fax_account_id is None
    assert grant.user_id == USER_ID
    assert grant.id == GRANT_ID


def test_a_grant_object_cannot_be_changed_after_it_is_read(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # FROZEN, like every model this package hands back. A grant is a record
    # of a decision that was already made; assigning to one would look like
    # it moved the grant to another account and would move nothing at all.
    # There is no update route on this resource, so the object being
    # writable would be a lie in two directions at once.
    import dataclasses

    respx_mock.get(GRANT_URL).mock(
        return_value=httpx.Response(200, json={"data": _grant_resource()})
    )

    with client:
        grant = client.fax_account_users.get(GRANT_ID)

    with pytest.raises(dataclasses.FrozenInstanceError):
        grant.fax_account_id = "0198c4a1-0000-0000-0000-000000000000"  # type: ignore[misc]


def test_a_grant_id_stays_inside_its_own_path_segment(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # An id is whatever the caller's own system handed them, and one carrying
    # `/` or `..` must not steer the request at a DIFFERENT endpoint.
    # Asserted on `raw_path`, which is what goes on the wire — `url.path` is
    # a DECODED view and shows the traversal even when the escaping is right.
    evil = "../fax-accounts/secret"
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(200, json={"data": _grant_resource()})
    )

    with client:
        client.fax_account_users.get(evil)

    assert (
        route.calls.last.request.url.raw_path
        == b"/v1/fax-account-users/..%2Ffax-accounts%2Fsecret"
    )


def test_an_empty_grant_id_is_refused_by_its_own_name(client: Ringivo) -> None:
    with client, pytest.raises(ValueError, match="a fax account user id is required"):
        client.fax_account_users.get("")


def test_a_grant_that_is_not_yours_raises_a_typed_404(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(GRANT_URL).mock(
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
        client.fax_account_users.get(GRANT_ID)

    assert caught.value.status_code == 404
    assert caught.value.code == "not_found"


# -- create ----------------------------------------------------------------


def test_create_posts_a_document_that_is_all_relationships(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.post(GRANTS_URL).mock(
        return_value=httpx.Response(201, json={"data": _grant_resource()})
    )

    with client:
        grant = client.fax_account_users.create(fax_account=ACCOUNT_ID, user=USER_ID)

    request = route.calls.last.request
    body = jsonlib.loads(request.content)

    # The content type is the assertion that matters: httpx stamps
    # `application/json` on a `json=` body, and this surface answers 415 to
    # that. The explicit header wins because httpx only fills in what the
    # caller left unset.
    assert request.headers["content-type"] == JSONAPI
    assert request.headers["accept"] == JSONAPI
    assert body["data"]["type"] == "fax-account-users"
    assert body["data"]["relationships"]["faxAccount"]["data"] == {
        "type": "fax-accounts",
        "id": ACCOUNT_ID,
    }
    assert body["data"]["relationships"]["user"]["data"] == {
        "type": "users",
        "id": USER_ID,
    }
    # NO attributes member at all — a grant has none a caller writes, and an
    # empty `attributes: {}` would be this client inventing one.
    assert "attributes" not in body["data"]
    assert set(body["data"]) == {"type", "relationships"}
    assert grant.id == GRANT_ID


def test_create_names_the_relationships_camelcased_as_the_document_wants(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The other half of the snake_case/camelCase split the filters have: the
    # DOCUMENT member is `faxAccount`, and a snake_cased one here would be a
    # 422 on a relationship the server does not know.
    route = respx_mock.post(GRANTS_URL).mock(
        return_value=httpx.Response(201, json={"data": _grant_resource()})
    )

    with client:
        client.fax_account_users.create(fax_account=ACCOUNT_ID, user=USER_ID)

    relationships = jsonlib.loads(route.calls.last.request.content)["data"]["relationships"]

    assert set(relationships) == {"faxAccount", "user"}
    assert "fax_account" not in relationships


def test_a_fax_account_that_is_not_yours_answers_on_the_relationship_pointer(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.post(GRANTS_URL).mock(
        return_value=httpx.Response(
            404,
            json={
                "errors": [
                    {
                        "status": "404",
                        "title": "Not Found",
                        "detail": "The related resource does not exist.",
                        "source": {"pointer": "/data/relationships/faxAccount"},
                    }
                ]
            },
        )
    )

    with client, pytest.raises(ApiError) as caught:
        client.fax_account_users.create(fax_account=ACCOUNT_ID, user=USER_ID)

    assert caught.value.status_code == 404
    assert caught.value.errors[0].source == {"pointer": "/data/relationships/faxAccount"}


def test_granting_the_same_pair_twice_is_the_servers_refusal_to_make(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The pair IS the row, so a duplicate is a conflict rather than a second
    # grant. This client does not read the collection first to find out —
    # that would be a race with a truthful-looking answer.
    respx_mock.post(GRANTS_URL).mock(
        return_value=httpx.Response(
            422,
            json={
                "errors": [
                    {
                        "status": "422",
                        "title": "Unprocessable Content",
                        "detail": "This user already has access to this fax account.",
                        "source": {"pointer": "/data/relationships/user"},
                    }
                ]
            },
        )
    )

    with client, pytest.raises(ApiError) as caught:
        client.fax_account_users.create(fax_account=ACCOUNT_ID, user=USER_ID)

    assert caught.value.status_code == 422


# -- delete ----------------------------------------------------------------


def test_delete_answers_nothing_and_returns_none(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.delete(GRANT_URL).mock(return_value=httpx.Response(204))

    with client:
        answer = client.fax_account_users.delete(GRANT_ID)

    assert answer is None
    assert route.calls.last.request.method == "DELETE"


def test_an_empty_grant_id_is_refused_before_a_withdrawal_reaches_the_wire(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The refusal names the id the caller passed, and it happens BEFORE the
    # request exists: an empty segment would otherwise send
    # `DELETE /v1/fax-account-users/` at the collection.
    with client, pytest.raises(ValueError, match="a fax account user id is required"):
        client.fax_account_users.delete("")

    assert respx_mock.calls.call_count == 0, "an empty withdrawal reached the wire"


def test_a_withdrawal_of_a_grant_that_is_gone_is_a_typed_404(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.delete(GRANT_URL).mock(
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
        client.fax_account_users.delete(GRANT_ID)

    assert caught.value.status_code == 404
    assert caught.value.code == "not_found"
