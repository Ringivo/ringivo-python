"""The PBX surface, asserted on the WIRE.

Three read collections and one write, and what is worth asserting differs
between them.

For the reads it is the QUERY: `list()`'s whole job is to build one, and
that is not observable from the return value. Every filter gets a named
assertion, including the two booleans — `filter[registered]` and
`filter[include-hidden]` — which are the ones a client can silently drop,
because `False` is falsy and "not asked for" is not.

For the READING it is the two timestamp rules, which pull in opposite
directions on purpose: a user's and a device's timestamps stay TEXT,
because the phone system has never published what format it writes them
in, while a call record's three instants are parsed, because those are RFC
3339 in UTC. A test that only checked "it came back" would have nothing to
say about either.

For the write it is the BODY. `users.call()` makes a real phone ring, so
the document it posts is pinned member by member: the type, the required
attribute, the two optional ones that must be ABSENT rather than null when
they were not passed, and the boolean that is always sent.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

import httpx
import pytest
import respx

from ringivo import (
    ApiError,
    CallRecord,
    CallRecordPage,
    PbxCall,
    PbxDevice,
    PbxDevicePage,
    PbxUser,
    PbxUserPage,
    Ringivo,
)

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
USERS_URL = f"{BASE_URL}/v1/pbx/users"
DEVICES_URL = f"{BASE_URL}/v1/pbx/devices"
CALL_RECORDS_URL = f"{BASE_URL}/v1/pbx/call-records"
USER_ID = "6f98cc5d-5248-5100-9967-8606e2993077"
USER_URL = f"{USERS_URL}/{USER_ID}"
CALLS_URL = f"{USER_URL}/calls"
DEVICE_ID = "92e7c8b3-9d9f-5286-86ac-f0d0c035e6c0"
DEVICE_URL = f"{DEVICES_URL}/{DEVICE_ID}"
CALL_RECORD_ID = "e4837703-48c1-5c9e-8699-bbaafb17bb84"
CALL_RECORD_URL = f"{CALL_RECORDS_URL}/{CALL_RECORD_ID}"
CALL_ID = "0198c7f2-1111-7000-8000-000000000001"
CUSTOMER_ID = "0198c4a1-2b3c-7d4e-8f50-1a2b3c4d5e6f"
TENANT = "0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8"
JSONAPI = "application/vnd.api+json"

# The scopes this whole surface needs, in one place: two reads that are
# deliberately separate — a call log is a different sensitivity from a
# directory — and the write that makes a phone ring.
SCOPES = ["pbx-users:read", "pbx-call-records:read", "pbx-calls:write"]


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


def _user_resource(
    *,
    relationships: dict[str, object] | None = None,
    attributes: dict[str, object] | None = None,
) -> dict[str, object]:
    """One resource object, with any attribute replaced.

    The overrides come in as a DICT rather than as `**kwargs`, unlike the
    fax suites' builders: this server writes its attributes in kebab-case,
    and `display-name` is not a Python identifier, so `**{"...": ...}` is
    the only spelling `**kwargs` would accept — and a `**dict[str, object]`
    splat reads to a type checker as something that could also fill
    `relationships`.
    """
    merged: dict[str, object] = {
        "user": "101",
        "domain": "acme.example",
        "display-name": "Ann Perkins",
        "first-name": "Ann",
        "last-name": "Perkins",
        "email": "ann@acme.example",
        "scope": "Basic User",
        "group": "sales",
        "site": "HQ",
        "presence": "open",
        "caller-id-number": "+14075550101",
        "caller-id-name": "Ann Perkins",
        "time-zone": "US/Eastern",
        "created-at": "2026-01-02 03:04:05",
        "updated-at": "2026-09-01 10:00:00",
    }
    merged.update(attributes or {})
    return {
        "type": "users",
        "id": USER_ID,
        "attributes": merged,
        "relationships": (
            relationships
            if relationships is not None
            else {
                "customer": {"data": {"type": "customers", "id": CUSTOMER_ID}},
                "devices": {"data": [{"type": "devices", "id": DEVICE_ID}]},
            }
        ),
    }


def _device_resource(
    *,
    relationships: dict[str, object] | None = None,
    attributes: dict[str, object] | None = None,
) -> dict[str, object]:
    merged: dict[str, object] = {
        "aor": "sip:101@acme.example",
        "user": "101",
        "domain": "acme.example",
        "mode": "register",
        "user-agent": "Polycom/6.4.2",
        "contact": "sip:101@198.51.100.7:5060",
        "transport": "udp",
        "received-from": "198.51.100.7:5060",
        "registered-at": "2026-09-14 08:00:00",
        "registration-expires-at": "2026-09-14 09:00:00",
        "registered": True,
        "auto-answer": False,
        "created-at": "2026-01-02 03:04:05",
    }
    merged.update(attributes or {})
    return {
        "type": "devices",
        "id": DEVICE_ID,
        "attributes": merged,
        "relationships": (
            relationships
            if relationships is not None
            else {
                "customer": {"data": {"type": "customers", "id": CUSTOMER_ID}},
                "pbx-user": {"data": {"type": "users", "id": USER_ID}},
            }
        ),
    }


def _call_record_resource(
    *,
    relationships: dict[str, object] | None = None,
    attributes: dict[str, object] | None = None,
) -> dict[str, object]:
    merged: dict[str, object] = {
        "direction": "inbound",
        "disposition": "answered",
        "vendor-type": 1,
        "domain": "acme.example",
        "from-user": "",
        "from-uri": "sip:+13025556789@carrier.example",
        "from-name": "Dr Bell",
        "to-user": "101",
        "to-uri": "sip:101@acme.example",
        "dialed": "+14075550101",
        "by-user": "",
        "term-user": "101",
        "started-at": "2026-09-12T14:00:00+00:00",
        "answered-at": "2026-09-12T14:00:04+00:00",
        "released-at": "2026-09-12T14:01:04+00:00",
        "duration": 64,
        "talk-time": 60,
        "tag": "clinic",
        "hidden": False,
        "has-recording": True,
        "vendor-id": "20260912000000000001c0ffee0123456789abcdef",
    }
    merged.update(attributes or {})
    return {
        "type": "call-records",
        "id": CALL_RECORD_ID,
        "attributes": merged,
        "relationships": (
            relationships
            if relationships is not None
            else {
                "customer": {"data": {"type": "customers", "id": CUSTOMER_ID}},
                "from-pbx-user": {"data": None},
                "to-pbx-user": {"data": {"type": "users", "id": USER_ID}},
            }
        ),
    }


def _call_resource(*, attributes: dict[str, object] | None = None) -> dict[str, object]:
    merged: dict[str, object] = {
        "destination": "+13025046250",
        "caller-id": None,
        "auto-answer": False,
        "device": None,
        "status": "requested",
        "requested-at": "2026-09-15T09:30:00+00:00",
    }
    merged.update(attributes or {})
    return {"type": "calls", "id": CALL_ID, "attributes": merged}


# -- users.list ------------------------------------------------------------


def test_users_list_builds_the_filter_and_page_query(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(USERS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    with client:
        client.pbx.users.list(
            customer=CUSTOMER_ID,
            user="101",
            search="perkins",
            after="0198c4a1",
            page_size=100,
        )

    request = route.calls.last.request
    params = request.url.params

    assert request.url.path == "/v1/pbx/users"
    assert params["filter[customer]"] == CUSTOMER_ID
    assert params["filter[user]"] == "101"
    assert params["filter[search]"] == "perkins"
    assert params["page[after]"] == "0198c4a1"
    assert params["page[size]"] == "100"
    # An unset filter is absent, not empty: `filter[search]=` would be a
    # search for the empty string rather than "no opinion".
    assert "page[before]" not in params
    assert request.headers["accept"] == JSONAPI


def test_users_list_reads_the_rows_and_the_next_cursor_from_page_meta(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(USERS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [_user_resource()],
                "links": {"next": f"{USERS_URL}?page%5Bafter%5D=0198c4a1-next"},
                "meta": {"page": {"size": 25, "nextCursor": "0198c4a1-next"}},
            },
        )
    )

    with client:
        page = client.pbx.users.list()

    assert isinstance(page, PbxUserPage)
    assert len(page) == 1
    assert list(page)[0].id == USER_ID
    assert page[0].user == "101"
    assert page.next_cursor == "0198c4a1-next"
    assert page.next_url is not None and "page%5Bafter%5D" in page.next_url


def test_users_list_walks_the_cursor_to_the_last_page(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The whole-collection walk the README documents: follow `next_cursor`
    # until it comes back None, which is the ONLY end-of-collection signal —
    # a short page is not one.
    pages = [
        httpx.Response(
            200,
            json={
                "data": [_user_resource()],
                "meta": {"page": {"size": 1, "nextCursor": "cursor-2"}},
            },
        ),
        httpx.Response(
            200,
            json={
                "data": [_user_resource(attributes={"user": "102"})],
                "meta": {"page": {"size": 1, "nextCursor": None}},
            },
        ),
    ]
    route = respx_mock.get(USERS_URL).mock(side_effect=pages)

    with client:
        collected: list[PbxUser] = []
        after: str | None = None
        while True:
            page = client.pbx.users.list(after=after)
            collected.extend(page)
            if page.next_cursor is None:
                break
            after = page.next_cursor

    assert [user.user for user in collected] == ["101", "102"]
    assert route.call_count == 2
    # The second request carried the server's own cursor back, unchanged.
    assert "page[after]" not in route.calls[0].request.url.params
    assert route.calls[1].request.url.params["page[after]"] == "cursor-2"


# -- users.get -------------------------------------------------------------


def test_users_get_reads_a_jsonapi_document_into_the_public_dataclass(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(USER_URL).mock(return_value=httpx.Response(200, json={"data": _user_resource()}))

    with client:
        user = client.pbx.users.get(USER_ID)

    assert isinstance(user, PbxUser)
    assert user.id == USER_ID
    assert user.user == "101"
    assert user.domain == "acme.example"
    assert user.display_name == "Ann Perkins"
    assert user.first_name == "Ann"
    assert user.last_name == "Perkins"
    assert user.email == "ann@acme.example"
    assert user.scope == "Basic User"
    assert user.group == "sales"
    assert user.site == "HQ"
    assert user.presence == "open"
    assert user.caller_id_number == "+14075550101"
    assert user.caller_id_name == "Ann Perkins"
    assert user.time_zone == "US/Eastern"
    assert user.customer_id == CUSTOMER_ID
    assert user.device_ids == (DEVICE_ID,)
    assert user.raw["type"] == "users"


def test_a_pbx_users_timestamps_are_served_as_text_rather_than_guessed_at(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # THE RULE THIS SURFACE INVERTS. Every other model in this package parses
    # `createdAt` into a `datetime`; these two stay `str`, because the phone
    # system has never published what format it writes and a wrong parse is
    # silent — an instant that is off by a zone still looks like an instant.
    respx_mock.get(USER_URL).mock(return_value=httpx.Response(200, json={"data": _user_resource()}))

    with client:
        user = client.pbx.users.get(USER_ID)

    assert user.created_at == "2026-01-02 03:04:05"
    assert user.updated_at == "2026-09-01 10:00:00"
    assert isinstance(user.created_at, str)


def test_a_user_relationship_without_linkage_is_no_id_rather_than_a_crash(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # A JSON:API server may answer a relationship with `links` alone. On the
    # to-many `devices` that reads None — "we did not tell you" — which is
    # not the same as the `()` an empty linkage array would give.
    respx_mock.get(USER_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": _user_resource(
                    relationships={
                        "customer": {"links": {"self": f"{USER_URL}/relationships/customer"}},
                        "devices": {"links": {"self": f"{USER_URL}/relationships/devices"}},
                    }
                )
            },
        )
    )

    with client:
        user = client.pbx.users.get(USER_ID)

    assert user.customer_id is None
    assert user.device_ids is None


def test_a_user_with_no_devices_registered_reads_an_empty_tuple(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The other half of the distinction above: an empty linkage array really
    # does say "nobody has registered a phone", and it must not read as None.
    respx_mock.get(USER_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": _user_resource(
                    relationships={
                        "customer": {"data": {"type": "customers", "id": CUSTOMER_ID}},
                        "devices": {"data": []},
                    }
                )
            },
        )
    )

    with client:
        user = client.pbx.users.get(USER_ID)

    assert user.device_ids == ()


def test_a_pbx_user_id_stays_inside_its_own_path_segment(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(200, json={"data": _user_resource()})
    )

    with client:
        client.pbx.users.get("../../faxes/secret")

    assert route.calls.last.request.url.raw_path == b"/v1/pbx/users/..%2F..%2Ffaxes%2Fsecret"


def test_an_empty_pbx_user_id_is_refused_by_its_own_name(client: Ringivo) -> None:
    with client, pytest.raises(ValueError, match="a PBX user id is required"):
        client.pbx.users.get("")


def test_a_pbx_user_outside_your_customers_domains_raises_a_typed_404(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # 404 rather than 403, and this client does not soften it: telling the
    # two apart would tell a caller that the subscriber exists.
    respx_mock.get(USER_URL).mock(
        return_value=httpx.Response(
            404,
            json={"errors": [{"status": "404", "title": "Not found", "code": "not_found"}]},
        )
    )

    with client, pytest.raises(ApiError) as caught:
        client.pbx.users.get(USER_ID)

    assert caught.value.status_code == 404
    assert caught.value.code == "not_found"


def test_a_credential_that_reaches_no_phone_system_is_refused_rather_than_emptied(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The refusal this surface is built around: "nobody has a phone system
    # yet" must never arrive looking like "nobody has any users".
    respx_mock.get(USERS_URL).mock(
        return_value=httpx.Response(
            400,
            json={
                "errors": [
                    {
                        "status": "400",
                        "code": "invalid_query",
                        "title": "Bad query",
                        "detail": "No customer you may read has a phone system.",
                    }
                ]
            },
        )
    )

    with client, pytest.raises(ApiError) as caught:
        client.pbx.users.list()

    assert caught.value.status_code == 400
    assert caught.value.code == "invalid_query"


# -- devices ---------------------------------------------------------------


def test_devices_list_builds_the_filter_and_page_query(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(DEVICES_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    with client:
        client.pbx.devices.list(
            customer=CUSTOMER_ID, user=USER_ID, registered=True, before="0198c4a1", page_size=50
        )

    request = route.calls.last.request
    params = request.url.params

    assert request.url.path == "/v1/pbx/devices"
    assert params["filter[customer]"] == CUSTOMER_ID
    assert params["filter[user]"] == USER_ID
    assert params["filter[registered]"] == "true"
    assert params["page[before]"] == "0198c4a1"
    assert params["page[size]"] == "50"
    assert "page[after]" not in params


def test_devices_list_sends_registered_false_rather_than_dropping_it(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # `False` is falsy and "not asked for" is not. Dropping this one would
    # turn "show me what has expired" into "show me everything" — a wrong
    # answer that looks like a right one.
    route = respx_mock.get(DEVICES_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    with client:
        client.pbx.devices.list(registered=False)

    assert route.calls.last.request.url.params["filter[registered]"] == "false"


def test_devices_list_with_no_filters_sends_no_filter_parameters(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(DEVICES_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    with client:
        page = client.pbx.devices.list()

    assert isinstance(page, PbxDevicePage)
    assert str(route.calls.last.request.url.params) == ""


def test_devices_get_reads_a_jsonapi_document_into_the_public_dataclass(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(DEVICE_URL).mock(
        return_value=httpx.Response(200, json={"data": _device_resource()})
    )

    with client:
        device = client.pbx.devices.get(DEVICE_ID)

    assert isinstance(device, PbxDevice)
    assert device.id == DEVICE_ID
    assert device.aor == "sip:101@acme.example"
    assert device.user == "101"
    assert device.domain == "acme.example"
    assert device.mode == "register"
    assert device.user_agent == "Polycom/6.4.2"
    assert device.contact == "sip:101@198.51.100.7:5060"
    assert device.transport == "udp"
    assert device.received_from == "198.51.100.7:5060"
    # Text, like a user's — the API refuses to guess the switch's format and
    # so does this client.
    assert device.registered_at == "2026-09-14 08:00:00"
    assert device.registration_expires_at == "2026-09-14 09:00:00"
    assert device.created_at == "2026-01-02 03:04:05"
    # DERIVED by the API, and the field to read: comparing the two strings
    # above yourself would mean guessing the format.
    assert device.registered is True
    assert device.auto_answer is False
    assert device.customer_id == CUSTOMER_ID
    # `pbx_user_id`, not `user_id`: `user` is already an attribute here, and
    # JSON:API forbids a relationship sharing an attribute's name.
    assert device.pbx_user_id == USER_ID


def test_an_expired_registration_is_a_row_with_registered_false(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(DEVICE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": _device_resource(
                    attributes={"registered": False, "auto-answer": True}
                )
            },
        )
    )

    with client:
        device = client.pbx.devices.get(DEVICE_ID)

    assert device.registered is False
    assert device.auto_answer is True


def test_an_empty_pbx_device_id_is_refused_by_its_own_name(client: Ringivo) -> None:
    with client, pytest.raises(ValueError, match="a PBX device id is required"):
        client.pbx.devices.get("")


def test_a_pbx_device_id_stays_inside_its_own_path_segment(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(200, json={"data": _device_resource()})
    )

    with client:
        client.pbx.devices.get("../users/secret")

    assert route.calls.last.request.url.raw_path == b"/v1/pbx/devices/..%2Fusers%2Fsecret"


# -- call records ----------------------------------------------------------


def test_call_records_list_builds_every_filter_and_the_page_query(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(CALL_RECORDS_URL).mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    with client:
        client.pbx.call_records.list(
            customer=CUSTOMER_ID,
            started_after="2026-09-01T00:00:00Z",
            started_before="2026-09-30T23:59:59Z",
            direction="inbound",
            user=USER_ID,
            call_id=CALL_ID,
            include_hidden=True,
            after="0198c4a1",
            page_size=100,
        )

    request = route.calls.last.request
    params = request.url.params

    assert request.url.path == "/v1/pbx/call-records"
    assert params["filter[customer]"] == CUSTOMER_ID
    # The date range is KEBAB-CASE here, unlike the fax collection's
    # `filter[created_after]`. Two servers, two spellings, and only the
    # spec settles which is which.
    assert params["filter[started-after]"] == "2026-09-01T00:00:00Z"
    assert params["filter[started-before]"] == "2026-09-30T23:59:59Z"
    assert params["filter[direction]"] == "inbound"
    assert params["filter[user]"] == USER_ID
    # The id `users.call()` answered with, KEBAB-CASE like the date range.
    assert params["filter[call-id]"] == CALL_ID
    assert params["filter[include-hidden]"] == "true"
    assert params["page[after]"] == "0198c4a1"
    assert params["page[size]"] == "100"
    assert "page[before]" not in params


def test_call_records_list_no_longer_sends_a_disposition_filter(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The platform answers `filter[disposition]` with a 400 now. Removing the
    # argument is not proof on its own, so this asks the way a caller who
    # reaches past the type hint would — and checks the WIRE first, then the
    # refusal. The `cast` is that caller: the type checker already refuses
    # the argument.
    route = respx_mock.get(CALL_RECORDS_URL).mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    refused = False
    with client:
        try:
            cast(Any, client.pbx.call_records).list(disposition="missed")
        except TypeError:
            refused = True

    sent = [call.request.url.params for call in route.calls]
    assert not any("filter[disposition]" in params for params in sent), (
        f"filter[disposition] reached the wire: {sent}"
    )
    assert refused, "list() accepted disposition= instead of refusing it"


def test_call_records_list_sends_include_hidden_false_rather_than_dropping_it(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(CALL_RECORDS_URL).mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    with client:
        client.pbx.call_records.list(include_hidden=False)

    assert route.calls.last.request.url.params["filter[include-hidden]"] == "false"


def test_call_records_list_with_no_range_asks_for_no_range(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # Which is NOT the same as asking for everything: with no range the API
    # reads the current and previous month only. The client says nothing and
    # lets the server's own default stand.
    route = respx_mock.get(CALL_RECORDS_URL).mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    with client:
        page = client.pbx.call_records.list()

    assert isinstance(page, CallRecordPage)
    params = route.calls.last.request.url.params
    assert "filter[started-after]" not in params
    assert "filter[started-before]" not in params


def test_a_range_wider_than_the_ceiling_is_the_servers_refusal_to_make(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The client keeps no copy of the 13-month ceiling: a second copy of a
    # server rule goes stale on its own, and the refusal names the real
    # number in its `meta`.
    route = respx_mock.get(CALL_RECORDS_URL).mock(
        return_value=httpx.Response(
            400,
            json={
                "errors": [
                    {
                        "status": "400",
                        "code": "invalid_query",
                        "title": "Bad query",
                        "detail": "The date range may not be wider than 13 months.",
                        "source": {"parameter": "filter[started-after]"},
                        "meta": {"filter": {"maxMonths": 13}},
                    }
                ]
            },
        )
    )

    with client, pytest.raises(ApiError) as caught:
        client.pbx.call_records.list(
            started_after="2020-01-01T00:00:00Z", started_before="2026-09-01T00:00:00Z"
        )

    assert route.calls.last.request.url.params["filter[started-after]"] == "2020-01-01T00:00:00Z"
    assert caught.value.status_code == 400
    assert caught.value.errors[0].meta == {"filter": {"maxMonths": 13}}


def test_a_direction_this_collection_does_not_publish_is_refused_by_the_api(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # Passed through rather than validated here, for the reason
    # webhook_deliveries.list() gives about its own statuses: the API's
    # refusal names the real vocabulary, and a copy of the enum in this
    # package would go stale on its own.
    route = respx_mock.get(CALL_RECORDS_URL).mock(
        return_value=httpx.Response(
            400,
            json={
                "errors": [
                    {
                        "status": "400",
                        "code": "invalid_query",
                        "title": "Bad query",
                        "detail": "filter[direction] must be one of: outbound, inbound, on-net.",
                        "source": {"parameter": "filter[direction]"},
                    }
                ]
            },
        )
    )

    with client, pytest.raises(ApiError) as caught:
        client.pbx.call_records.list(direction="sideways")

    assert route.calls.last.request.url.params["filter[direction]"] == "sideways"
    assert caught.value.errors[0].source == {"parameter": "filter[direction]"}


def test_call_records_get_reads_a_jsonapi_document_into_the_public_dataclass(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(CALL_RECORD_URL).mock(
        return_value=httpx.Response(200, json={"data": _call_record_resource()})
    )

    with client:
        record = client.pbx.call_records.get(CALL_RECORD_ID)

    assert isinstance(record, CallRecord)
    assert record.id == CALL_RECORD_ID
    assert record.direction == "inbound"
    assert record.disposition == "answered"
    assert record.vendor_type == 1
    assert record.domain == "acme.example"
    assert record.from_user == ""
    assert record.from_uri == "sip:+13025556789@carrier.example"
    assert record.from_name == "Dr Bell"
    assert record.to_user == "101"
    assert record.to_uri == "sip:101@acme.example"
    assert record.dialed == "+14075550101"
    assert record.by_user == ""
    assert record.term_user == "101"
    assert record.duration == 64
    assert record.talk_time == 60
    assert record.tag == "clinic"
    assert record.hidden is False
    assert record.has_recording is True
    assert record.vendor_id == "20260912000000000001c0ffee0123456789abcdef"
    assert record.customer_id == CUSTOMER_ID
    # An outside caller has no subscriber to point at, and the API says so
    # with an explicit null linkage rather than by leaving the member out.
    assert record.from_pbx_user_id is None
    assert record.to_pbx_user_id == USER_ID


def test_a_call_records_three_instants_are_parsed_unlike_the_other_two_resources(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The other side of the timestamp rule: these three ARE RFC 3339 in UTC,
    # because the switch stores them as Unix epochs, so there is nothing to
    # guess and every reason to hand back a real instant.
    respx_mock.get(CALL_RECORD_URL).mock(
        return_value=httpx.Response(200, json={"data": _call_record_resource()})
    )

    with client:
        record = client.pbx.call_records.get(CALL_RECORD_ID)

    assert record.started_at == datetime(2026, 9, 12, 14, 0, 0, tzinfo=timezone.utc)
    assert record.answered_at == datetime(2026, 9, 12, 14, 0, 4, tzinfo=timezone.utc)
    assert record.released_at == datetime(2026, 9, 12, 14, 1, 4, tzinfo=timezone.utc)


def test_a_missed_call_carries_no_answered_at(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(CALL_RECORD_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": _call_record_resource(
                    attributes={
                        "direction": "inbound",
                        "disposition": "missed",
                        "vendor-type": 2,
                        "answered-at": None,
                        "talk-time": 0,
                    }
                )
            },
        )
    )

    with client:
        record = client.pbx.call_records.get(CALL_RECORD_ID)

    assert record.disposition == "missed"
    assert record.vendor_type == 2
    assert record.answered_at is None
    assert record.talk_time == 0


def test_a_vendor_type_with_no_word_for_it_arrives_as_its_own_digits(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The API publishes an unknown integer as a STRING in `direction` rather
    # than as null, so a vocabulary that grows at the switch's end never
    # erases a call. This client passes that through — it keeps no enum of
    # its own to fall foul of.
    respx_mock.get(CALL_RECORD_URL).mock(
        return_value=httpx.Response(
            200,
            json={"data": _call_record_resource(
                attributes={"direction": "9", "disposition": None, "vendor-type": 9}
            )},
        )
    )

    with client:
        record = client.pbx.call_records.get(CALL_RECORD_ID)

    assert record.direction == "9"
    assert record.disposition is None
    assert record.vendor_type == 9


def test_a_hidden_record_is_served_on_a_direct_read(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The asymmetry the phone system's own portal has: the list leaves a
    # hidden record out, a direct read hands it over.
    respx_mock.get(CALL_RECORD_URL).mock(
        return_value=httpx.Response(
            200, json={"data": _call_record_resource(attributes={"hidden": True})}
        )
    )

    with client:
        record = client.pbx.call_records.get(CALL_RECORD_ID)

    assert record.hidden is True


def test_an_empty_call_record_id_is_refused_by_its_own_name(client: Ringivo) -> None:
    with client, pytest.raises(ValueError, match="a call record id is required"):
        client.pbx.call_records.get("")


def test_a_call_record_id_stays_inside_its_own_path_segment(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(200, json={"data": _call_record_resource()})
    )

    with client:
        client.pbx.call_records.get("../users/secret")

    assert route.calls.last.request.url.raw_path == b"/v1/pbx/call-records/..%2Fusers%2Fsecret"


# -- users.call (click-to-dial) --------------------------------------------


def test_call_posts_a_jsonapi_document_under_the_users_own_path(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    import json

    route = respx_mock.post(CALLS_URL).mock(
        return_value=httpx.Response(202, json={"data": _call_resource()})
    )

    with client:
        placed = client.pbx.users.call(USER_ID, destination="+13025046250")

    request = route.calls.last.request
    body = json.loads(request.content)

    assert request.url.path == f"/v1/pbx/users/{USER_ID}/calls"
    assert request.headers["content-type"] == JSONAPI
    assert request.headers["accept"] == JSONAPI
    assert body["data"]["type"] == "calls"
    assert body["data"]["attributes"]["destination"] == "+13025046250"
    # ALWAYS SENT, because it is a fact about this call and `False` is a
    # value rather than a silence.
    assert body["data"]["attributes"]["auto-answer"] is False
    # ABSENT, not null: on a create there is nothing to clear, and "use the
    # subscriber's own caller id" is not the same request as "present no
    # caller id at all".
    assert "caller-id" not in body["data"]["attributes"]
    assert "device" not in body["data"]["attributes"]
    assert isinstance(placed, PbxCall)


def test_call_sends_every_optional_attribute_it_was_given(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    import json

    route = respx_mock.post(CALLS_URL).mock(
        return_value=httpx.Response(
            202,
            json={
                "data": _call_resource(
                    attributes={
                        # AS THE PLATFORM STORES IT — E.164 without the plus,
                        # which is not the spelling the request used.
                        "caller-id": "14075550101",
                        "auto-answer": True,
                        "device": DEVICE_ID,
                    }
                )
            },
        )
    )

    with client:
        placed = client.pbx.users.call(
            USER_ID,
            destination="1002",
            caller_id="+14075550101",
            auto_answer=True,
            device=DEVICE_ID,
        )

    attributes = json.loads(route.calls.last.request.content)["data"]["attributes"]

    assert attributes == {
        "destination": "1002",
        "auto-answer": True,
        "caller-id": "+14075550101",
        "device": DEVICE_ID,
    }
    # The request went out WITH the plus; the answer is what the switch was
    # sent, which this platform stores as E.164 WITHOUT it.
    assert placed.caller_id == "14075550101"


def test_call_reads_the_202_into_the_public_dataclass(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.post(CALLS_URL).mock(
        return_value=httpx.Response(
            202,
            json={
                "data": _call_resource(
                    attributes={
                        # AS THE PLATFORM STORES IT — E.164 without the plus,
                        # which is not the spelling the request used.
                        "caller-id": "14075550101",
                        "auto-answer": True,
                        "device": DEVICE_ID,
                    }
                )
            },
        )
    )

    with client:
        placed = client.pbx.users.call(
            USER_ID,
            destination="+13025046250",
            caller_id="+14075550101",
            auto_answer=True,
            device=DEVICE_ID,
        )

    assert placed.id == CALL_ID
    assert placed.destination == "+13025046250"
    # THE ANSWER IS WHAT WAS SENT TO THE SWITCH, NOT WHAT WAS TYPED: the
    # request's `+14075550101` comes back as `14075550101`.
    assert placed.caller_id == "14075550101"
    assert placed.auto_answer is True
    assert placed.device == DEVICE_ID
    # The whole promise of a 202, and no more of one: the request was
    # accepted. No phone has rung yet.
    assert placed.status == "requested"
    assert placed.requested_at == datetime(2026, 9, 15, 9, 30, 0, tzinfo=timezone.utc)
    assert placed.raw["type"] == "calls"


def test_a_device_that_is_not_this_users_is_refused_with_a_pointer(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # "No such device" and "not yours" share one answer on purpose: the two
    # must not be distinguishable from outside.
    respx_mock.post(CALLS_URL).mock(
        return_value=httpx.Response(
            422,
            json={
                "errors": [
                    {
                        "status": "422",
                        "code": "validation_failed",
                        "title": "Unprocessable",
                        "detail": "The selected device is invalid.",
                        "source": {"pointer": "/data/attributes/device"},
                    }
                ]
            },
        )
    )

    with client, pytest.raises(ApiError) as caught:
        client.pbx.users.call(
            USER_ID, destination="+13025046250", device="0198c7f2-dead-7000-8000-000000000000"
        )

    assert caught.value.status_code == 422
    assert caught.value.code == "validation_failed"
    assert caught.value.errors[0].source == {"pointer": "/data/attributes/device"}


def test_a_switch_that_refuses_the_call_arrives_as_a_502(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The phone system's own refusal, relayed rather than translated: the
    # platform could not carry out a request it had already accepted as
    # well-formed, and the vendor's status is in `meta`.
    respx_mock.post(CALLS_URL).mock(
        return_value=httpx.Response(
            502,
            json={
                "errors": [
                    {
                        "status": "502",
                        "title": "Bad gateway",
                        "detail": "The phone system refused the call.",
                        "meta": {"vendor_status": 400},
                    }
                ]
            },
        )
    )

    with client, pytest.raises(ApiError) as caught:
        client.pbx.users.call(USER_ID, destination="+13025046250")

    assert caught.value.status_code == 502
    assert caught.value.errors[0].meta == {"vendor_status": 400}


def test_an_empty_pbx_user_id_is_refused_before_a_phone_can_ring(client: Ringivo) -> None:
    # The escaper runs before the request is built, which matters more here
    # than on a read: nothing may reach the switch on a malformed id.
    with client, pytest.raises(ValueError, match="a PBX user id is required"):
        client.pbx.users.call("", destination="+13025046250")


def test_the_pbx_user_id_stays_inside_its_own_path_segment_on_a_call(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(202, json={"data": _call_resource()})
    )

    with client:
        client.pbx.users.call("../../faxes/secret", destination="+13025046250")

    assert (
        route.calls.last.request.url.raw_path
        == b"/v1/pbx/users/..%2F..%2Ffaxes%2Fsecret/calls"
    )
