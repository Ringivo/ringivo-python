"""The fax-account surface, asserted on the WIRE.

Every test here checks the request that went out or the object that came
back, never an internal call. That is deliberate, and it is the same reason
tests/test_faxes.py gives: `list()`'s whole job is to build a query string,
`create()`'s and `update()`'s is to build a JSON:API document, and
`numbers()`'s is to walk a cursor to the end. None of that is observable
from the return value alone.

The write bodies here ARE JSON:API documents — `{"data": {"type":
"fax-accounts", ...}}` sent as `application/vnd.api+json` — unlike
`POST /v1/faxes`, whose body is multipart or flat JSON and never a
document. The content type is asserted rather than assumed: httpx would
otherwise stamp `application/json` on a `json=` body, and this API answers
415 to that on a resource route.
"""

from __future__ import annotations

import json as jsonlib
from datetime import datetime, timezone

import httpx
import pytest
import respx

from ringivo import ApiError, FaxAccount, FaxAccountNumber, FaxAccountPage, Ringivo

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
    # The scopes are the ones this module's calls need: `fax:read` for the
    # reads and `fax-accounts:write` for the writes. `fax:write` sends a
    # fax and does not open an account, which is the split the platform
    # made deliberately.
    return Ringivo(
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


# -- list ------------------------------------------------------------------


def test_list_builds_the_filter_and_page_query(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(ACCOUNTS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    with client:
        client.fax_accounts.list(
            customer=CUSTOMER_ID,
            status="suspended",
            page_size=50,
            after="0198c4a1",
        )

    params = route.calls.last.request.url.params

    assert params["filter[customer]"] == CUSTOMER_ID
    assert params["filter[status]"] == "suspended"
    assert params["page[size]"] == "50"
    assert params["page[after]"] == "0198c4a1"
    # An unset filter is absent, not empty: `filter[status]=` would be a 400
    # rather than "no opinion".
    assert "page[before]" not in params
    assert route.calls.last.request.headers["accept"] == JSONAPI


def test_list_reads_the_accounts_and_the_next_cursor_from_page_meta(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(ACCOUNTS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [_account_resource()],
                "links": {"next": f"{ACCOUNTS_URL}?page%5Bafter%5D=0198c4a1-next"},
                "meta": {"page": {"size": 25, "nextCursor": "0198c4a1-next"}},
            },
        )
    )

    with client:
        page = client.fax_accounts.list()

    assert isinstance(page, FaxAccountPage)
    assert len(page) == 1
    assert list(page)[0].id == ACCOUNT_ID
    assert page[0].name == "Front desk"
    assert page.next_cursor == "0198c4a1-next"
    assert page.next_url is not None and "page%5Bafter%5D" in page.next_url


def test_the_last_page_has_no_cursor_to_follow(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # As deployed: `links.next` is ABSENT on the final page, and
    # `meta.page.nextCursor` is the mirror, `null` at the end.
    respx_mock.get(ACCOUNTS_URL).mock(
        return_value=httpx.Response(
            200, json={"data": [], "meta": {"page": {"size": 25, "nextCursor": None}}}
        )
    )

    with client:
        page = client.fax_accounts.list()

    assert len(page) == 0
    assert page.next_cursor is None
    assert page.next_url is None


# -- get -------------------------------------------------------------------


def test_get_reads_a_jsonapi_document_into_the_public_dataclass(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(ACCOUNT_URL).mock(
        return_value=httpx.Response(200, json={"data": _account_resource()})
    )

    with client:
        account = client.fax_accounts.get(ACCOUNT_ID)

    assert isinstance(account, FaxAccount)
    assert account.id == ACCOUNT_ID
    assert account.name == "Front desk"
    assert account.header_text == "ACME VETERINARY"
    assert account.default_from_e164 == "+14075550100"
    assert account.retention_days == 365
    # `null` is the prune rule being OFF — no page limit on this account.
    assert account.retention_pages is None
    assert account.status == "active"
    assert account.customer_id == CUSTOMER_ID
    assert account.created_at == datetime(2026, 8, 1, 9, 0, 0, tzinfo=timezone.utc)
    assert account.updated_at == datetime(2026, 8, 16, 11, 0, 0, tzinfo=timezone.utc)
    # The whole resource object is kept, so a member the API adds after this
    # release still reaches the caller.
    assert account.raw["type"] == "fax-accounts"


def test_a_relationship_without_linkage_is_no_customer_rather_than_a_crash(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # A JSON:API server may answer a relationship with `links` alone. That is
    # legal, it says nothing about the account, and it must not raise.
    resource = _account_resource()
    resource["relationships"] = {"customer": {"links": {"self": f"{ACCOUNT_URL}/relationships/customer"}}}
    respx_mock.get(ACCOUNT_URL).mock(return_value=httpx.Response(200, json={"data": resource}))

    with client:
        account = client.fax_accounts.get(ACCOUNT_ID)

    assert account.customer_id is None
    assert account.id == ACCOUNT_ID


def test_a_fax_account_id_stays_inside_its_own_path_segment(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # An id is whatever the caller's own system handed them, and one carrying
    # `/` or `..` must not steer the request at a DIFFERENT endpoint.
    # Asserted on `raw_path`, which is what goes on the wire — `url.path` is
    # a DECODED view and shows the traversal even when the escaping is right.
    evil = "../faxes/secret"
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(200, json={"data": _account_resource()})
    )

    with client:
        client.fax_accounts.get(evil)

    assert route.calls.last.request.url.raw_path == b"/v1/fax-accounts/..%2Ffaxes%2Fsecret"


def test_an_empty_fax_account_id_is_refused_by_its_own_name(client: Ringivo) -> None:
    with client, pytest.raises(ValueError, match="a fax account id is required"):
        client.fax_accounts.get("")


def test_an_account_that_is_not_yours_raises_a_typed_404(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(ACCOUNT_URL).mock(
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
        client.fax_accounts.get(ACCOUNT_ID)

    assert caught.value.status_code == 404
    assert caught.value.code == "not_found"


# -- numbers ---------------------------------------------------------------


def test_numbers_walks_every_page_and_returns_them_all(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # A truncated list is indistinguishable from a complete one — every row
    # on it is real — so this call walks to the end rather than handing back
    # page one. Two pages here, and the second is reached with the cursor the
    # first one published.
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

    with client:
        numbers = client.fax_accounts.numbers(ACCOUNT_ID)

    assert len(numbers) == 2
    assert isinstance(numbers[0], FaxAccountNumber)
    assert [n.e164 for n in numbers] == ["+14075550111", "+14075550112"]
    assert numbers[0].status == "active"
    assert numbers[0].country == "US"
    assert numbers[0].activated_at == datetime(2026, 7, 30, 14, 11, 0, tzinfo=timezone.utc)

    first, second = route.calls[0].request, route.calls[1].request
    assert first.url.params["page[size]"] == "100"
    assert "page[after]" not in first.url.params
    assert second.url.params["page[after]"] == "cursor-2"


def test_numbers_refuses_a_repeated_cursor_rather_than_walking_for_ever(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # A server that answers the same cursor twice would spin this walk for
    # ever, and a hang is the one failure nobody can see. It is refused with
    # a RingivoError instead — catchable as this package's own.
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

    with client, pytest.raises(RingivoError, match="served the cursor 'stuck' twice"):
        client.fax_accounts.numbers(ACCOUNT_ID)


# -- create ----------------------------------------------------------------


def test_create_posts_a_jsonapi_document_naming_the_customer(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.post(ACCOUNTS_URL).mock(
        return_value=httpx.Response(201, json={"data": _account_resource()})
    )

    with client:
        account = client.fax_accounts.create(
            customer=CUSTOMER_ID,
            name="Front desk",
            header_text="ACME VETERINARY",
            retention_days=365,
        )

    request = route.calls.last.request
    body = jsonlib.loads(request.content)

    # The content type is the assertion that matters: httpx stamps
    # `application/json` on a `json=` body, and this surface answers 415 to
    # that. The explicit header wins because httpx only fills in what the
    # caller left unset.
    assert request.headers["content-type"] == JSONAPI
    assert request.headers["accept"] == JSONAPI
    assert body["data"]["type"] == "fax-accounts"
    assert body["data"]["attributes"]["name"] == "Front desk"
    assert body["data"]["attributes"]["headerText"] == "ACME VETERINARY"
    assert body["data"]["attributes"]["retentionDays"] == 365
    assert body["data"]["relationships"]["customer"]["data"] == {
        "type": "customers",
        "id": CUSTOMER_ID,
    }
    assert account.id == ACCOUNT_ID


def test_create_leaves_out_an_attribute_nobody_named(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # ABSENT, not null. An attribute this client does not send is one the
    # platform fills in with its own default — a year of retention and no
    # page limit today. A client that sent `null` would be turning both
    # rules OFF while looking like it asked for nothing.
    route = respx_mock.post(ACCOUNTS_URL).mock(
        return_value=httpx.Response(201, json={"data": _account_resource()})
    )

    with client:
        client.fax_accounts.create(customer=CUSTOMER_ID, name="Front desk")

    attributes = jsonlib.loads(route.calls.last.request.content)["data"]["attributes"]

    assert attributes == {"name": "Front desk"}
    assert "retentionDays" not in attributes
    assert "retentionPages" not in attributes
    assert "headerText" not in attributes


def test_create_sends_null_for_a_rule_the_caller_turned_off(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The other half of the same contract, and the reason the sentinel
    # exists: `None` is a VALUE here — "keep the pages for ever" — and it
    # must reach the wire as `null` rather than being dropped with the
    # arguments nobody passed.
    route = respx_mock.post(ACCOUNTS_URL).mock(
        return_value=httpx.Response(201, json={"data": _account_resource(retentionDays=None)})
    )

    with client:
        client.fax_accounts.create(customer=CUSTOMER_ID, name="Front desk", retention_days=None)

    attributes = jsonlib.loads(route.calls.last.request.content)["data"]["attributes"]

    assert attributes["retentionDays"] is None
    assert "retentionPages" not in attributes


def test_a_customer_that_is_not_yours_answers_on_the_relationship_pointer(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.post(ACCOUNTS_URL).mock(
        return_value=httpx.Response(
            404,
            json={
                "errors": [
                    {
                        "status": "404",
                        "title": "Not Found",
                        "detail": "The related resource does not exist.",
                        "source": {"pointer": "/data/relationships/customer"},
                    }
                ]
            },
        )
    )

    with client, pytest.raises(ApiError) as caught:
        client.fax_accounts.create(customer=CUSTOMER_ID, name="Front desk")

    assert caught.value.status_code == 404
    assert caught.value.errors[0].source == {"pointer": "/data/relationships/customer"}


# -- update ----------------------------------------------------------------


def test_update_sends_only_what_was_named(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.patch(ACCOUNT_URL).mock(
        return_value=httpx.Response(200, json={"data": _account_resource(status="suspended")})
    )

    with client:
        account = client.fax_accounts.update(ACCOUNT_ID, status="suspended")

    request = route.calls.last.request
    body = jsonlib.loads(request.content)

    assert request.headers["content-type"] == JSONAPI
    assert body["data"]["type"] == "fax-accounts"
    # The id travels in the document as well as in the path — a JSON:API
    # PATCH names the resource it is changing, and the raw id goes here
    # while the ESCAPED one goes in the URL.
    assert body["data"]["id"] == ACCOUNT_ID
    assert body["data"]["attributes"] == {"status": "suspended"}
    assert account.status == "suspended"


def test_update_sends_null_to_clear_a_nullable_field(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.patch(ACCOUNT_URL).mock(
        return_value=httpx.Response(200, json={"data": _account_resource(defaultFromE164=None)})
    )

    with client:
        account = client.fax_accounts.update(ACCOUNT_ID, default_from_e164=None)

    attributes = jsonlib.loads(route.calls.last.request.content)["data"]["attributes"]

    assert attributes == {"defaultFromE164": None}
    assert account.default_from_e164 is None


def test_update_refuses_a_change_that_changes_nothing(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # A PATCH with an empty attributes object is a request the server would
    # accept and act on in no way, spending a round trip and an audit entry
    # to do nothing. It is far more likely a caller building the call from a
    # form that came back empty, so it is refused here, before anything is
    # sent.
    route = respx_mock.patch(ACCOUNT_URL).mock(return_value=httpx.Response(200, json={"data": {}}))

    with client, pytest.raises(ValueError, match="at least one field to change"):
        client.fax_accounts.update(ACCOUNT_ID)

    assert route.call_count == 0
    assert respx_mock.calls.call_count == 0, "an empty update reached the wire"


# -- delete ----------------------------------------------------------------


def test_delete_answers_nothing_and_returns_none(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.delete(ACCOUNT_URL).mock(return_value=httpx.Response(204))

    with client:
        answer = client.fax_accounts.delete(ACCOUNT_ID)

    assert answer is None
    assert route.calls.last.request.method == "DELETE"


def test_delete_is_refused_while_a_number_still_routes_to_the_account(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The published refusal, and the whole reason a caller branches on
    # `code` rather than on 409: a fax that cannot be cancelled is ALSO a
    # 409, and it carries no code at all.
    respx_mock.delete(ACCOUNT_URL).mock(
        return_value=httpx.Response(
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
        )
    )

    with client, pytest.raises(ApiError) as caught:
        client.fax_accounts.delete(ACCOUNT_ID)

    assert caught.value.status_code == 409
    assert caught.value.code == "fax_account_has_routed_numbers"


def test_the_sentinel_is_never_a_value_a_caller_can_confuse_with_none() -> None:
    from ringivo import NOT_GIVEN, NotGiven

    assert isinstance(NOT_GIVEN, NotGiven)
    assert NOT_GIVEN is not None
    assert bool(NOT_GIVEN) is False
    assert repr(NOT_GIVEN) == "NOT_GIVEN"
