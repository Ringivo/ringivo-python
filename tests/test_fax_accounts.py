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
