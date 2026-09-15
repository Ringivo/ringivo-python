"""The PBX surface again, awaited, and asserted on the WIRE.

The mirror of tests/test_pbx.py. `AsyncPbx` is a sibling of `Pbx` rather
than a wrapper around it, so the query strings and the request body it
writes are its own code and get their own assertions — the imported page
readers are the only halves the two share.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx
import pytest
import respx

from ringivo import (
    ApiError,
    AsyncRingivo,
    CallRecord,
    CallRecordPage,
    PbxCall,
    PbxDevice,
    PbxUser,
    PbxUserPage,
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
def client() -> AsyncRingivo:
    return AsyncRingivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=SCOPES,
    )


def _user_resource(*, attributes: dict[str, object] | None = None) -> dict[str, object]:
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
        "relationships": {
            "customer": {"data": {"type": "customers", "id": CUSTOMER_ID}},
            "devices": {"data": [{"type": "devices", "id": DEVICE_ID}]},
        },
    }


def _device_resource(*, attributes: dict[str, object] | None = None) -> dict[str, object]:
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
        "relationships": {
            "customer": {"data": {"type": "customers", "id": CUSTOMER_ID}},
            "pbx-user": {"data": {"type": "users", "id": USER_ID}},
        },
    }


def _call_record_resource(*, attributes: dict[str, object] | None = None) -> dict[str, object]:
    merged: dict[str, object] = {
        "direction": "outbound",
        "disposition": "answered",
        "vendor-type": 0,
        "domain": "acme.example",
        "from-user": "101",
        "from-uri": "sip:101@acme.example",
        "from-name": "Ann Perkins",
        "to-user": "",
        "to-uri": "sip:+13025556789@carrier.example",
        "dialed": "+13025556789",
        "by-user": "",
        "term-user": "",
        "started-at": "2026-09-12T14:00:00+00:00",
        "answered-at": "2026-09-12T14:00:04+00:00",
        "released-at": "2026-09-12T14:01:04+00:00",
        "duration": 64,
        "talk-time": 60,
        "tag": "clinic",
        "hidden": False,
        "has-recording": False,
        "vendor-id": "20260912000000000001c0ffee0123456789abcdef",
    }
    merged.update(attributes or {})
    return {
        "type": "call-records",
        "id": CALL_RECORD_ID,
        "attributes": merged,
        "relationships": {
            "customer": {"data": {"type": "customers", "id": CUSTOMER_ID}},
            "from-pbx-user": {"data": {"type": "users", "id": USER_ID}},
            "to-pbx-user": {"data": None},
        },
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


# -- users -----------------------------------------------------------------


@pytest.mark.anyio
async def test_users_list_builds_the_filter_and_page_query(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.get(USERS_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    async with client:
        page = await client.pbx.users.list(
            customer=CUSTOMER_ID, user="101", search="perkins", page_size=100
        )

    request = route.calls.last.request
    params = request.url.params

    assert isinstance(page, PbxUserPage)
    assert request.url.path == "/v1/pbx/users"
    assert params["filter[customer]"] == CUSTOMER_ID
    assert params["filter[user]"] == "101"
    assert params["filter[search]"] == "perkins"
    assert params["page[size]"] == "100"
    assert "page[after]" not in params
    assert request.headers["accept"] == JSONAPI


@pytest.mark.anyio
async def test_users_list_walks_the_cursor_to_the_last_page(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.get(USERS_URL).mock(
        side_effect=[
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
    )

    async with client:
        collected: list[PbxUser] = []
        after: str | None = None
        while True:
            page = await client.pbx.users.list(after=after)
            collected.extend(page)
            if page.next_cursor is None:
                break
            after = page.next_cursor

    assert [user.user for user in collected] == ["101", "102"]
    assert route.call_count == 2
    assert route.calls[1].request.url.params["page[after]"] == "cursor-2"


@pytest.mark.anyio
async def test_users_get_reads_a_jsonapi_document_into_the_public_dataclass(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.get(USER_URL).mock(return_value=httpx.Response(200, json={"data": _user_resource()}))

    async with client:
        user = await client.pbx.users.get(USER_ID)

    assert isinstance(user, PbxUser)
    assert user.id == USER_ID
    assert user.user == "101"
    assert user.display_name == "Ann Perkins"
    assert user.presence == "open"
    assert user.customer_id == CUSTOMER_ID
    assert user.device_ids == (DEVICE_ID,)
    # Text, not a `datetime`: the phone system has never published what
    # format it writes these in, so a parse here would be a guess.
    assert user.created_at == "2026-01-02 03:04:05"
    assert user.updated_at == "2026-09-01 10:00:00"


@pytest.mark.anyio
async def test_a_pbx_user_id_stays_inside_its_own_path_segment(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(200, json={"data": _user_resource()})
    )

    async with client:
        await client.pbx.users.get("../../faxes/secret")

    assert route.calls.last.request.url.raw_path == b"/v1/pbx/users/..%2F..%2Ffaxes%2Fsecret"


@pytest.mark.anyio
async def test_an_empty_pbx_user_id_is_refused_by_its_own_name(client: AsyncRingivo) -> None:
    async with client:
        with pytest.raises(ValueError, match="a PBX user id is required"):
            await client.pbx.users.get("")


@pytest.mark.anyio
async def test_a_pbx_user_outside_your_customers_domains_raises_a_typed_404(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.get(USER_URL).mock(
        return_value=httpx.Response(
            404,
            json={"errors": [{"status": "404", "title": "Not found", "code": "not_found"}]},
        )
    )

    async with client:
        with pytest.raises(ApiError) as caught:
            await client.pbx.users.get(USER_ID)

    assert caught.value.status_code == 404
    assert caught.value.code == "not_found"


# -- devices ---------------------------------------------------------------


@pytest.mark.anyio
async def test_devices_list_builds_the_filter_and_page_query(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.get(DEVICES_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    async with client:
        await client.pbx.devices.list(
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


@pytest.mark.anyio
async def test_devices_list_sends_registered_false_rather_than_dropping_it(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    # `False` is falsy and "not asked for" is not — the drop would turn
    # "what has expired" into "everything".
    route = respx_mock.get(DEVICES_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    async with client:
        await client.pbx.devices.list(registered=False)

    assert route.calls.last.request.url.params["filter[registered]"] == "false"


@pytest.mark.anyio
async def test_devices_get_reads_a_jsonapi_document_into_the_public_dataclass(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.get(DEVICE_URL).mock(
        return_value=httpx.Response(200, json={"data": _device_resource()})
    )

    async with client:
        device = await client.pbx.devices.get(DEVICE_ID)

    assert isinstance(device, PbxDevice)
    assert device.id == DEVICE_ID
    assert device.aor == "sip:101@acme.example"
    assert device.user_agent == "Polycom/6.4.2"
    assert device.received_from == "198.51.100.7:5060"
    assert device.registered is True
    assert device.auto_answer is False
    assert device.registered_at == "2026-09-14 08:00:00"
    assert device.customer_id == CUSTOMER_ID
    assert device.pbx_user_id == USER_ID


@pytest.mark.anyio
async def test_an_empty_pbx_device_id_is_refused_by_its_own_name(client: AsyncRingivo) -> None:
    async with client:
        with pytest.raises(ValueError, match="a PBX device id is required"):
            await client.pbx.devices.get("")


# -- call records ----------------------------------------------------------


@pytest.mark.anyio
async def test_call_records_list_builds_every_filter_and_the_page_query(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.get(CALL_RECORDS_URL).mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    async with client:
        page = await client.pbx.call_records.list(
            customer=CUSTOMER_ID,
            started_after="2026-09-01T00:00:00Z",
            started_before="2026-09-30T23:59:59Z",
            direction="outbound",
            disposition="missed",
            user=USER_ID,
            include_hidden=True,
            after="0198c4a1",
            page_size=100,
        )

    request = route.calls.last.request
    params = request.url.params

    assert isinstance(page, CallRecordPage)
    assert request.url.path == "/v1/pbx/call-records"
    assert params["filter[customer]"] == CUSTOMER_ID
    assert params["filter[started-after]"] == "2026-09-01T00:00:00Z"
    assert params["filter[started-before]"] == "2026-09-30T23:59:59Z"
    assert params["filter[direction]"] == "outbound"
    assert params["filter[disposition]"] == "missed"
    assert params["filter[user]"] == USER_ID
    assert params["filter[include-hidden]"] == "true"
    assert params["page[after]"] == "0198c4a1"
    assert params["page[size]"] == "100"
    assert "page[before]" not in params


@pytest.mark.anyio
async def test_call_records_list_sends_include_hidden_false_rather_than_dropping_it(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.get(CALL_RECORDS_URL).mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    async with client:
        await client.pbx.call_records.list(include_hidden=False)

    assert route.calls.last.request.url.params["filter[include-hidden]"] == "false"


@pytest.mark.anyio
async def test_call_records_get_reads_the_three_instants_as_real_datetimes(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.get(CALL_RECORD_URL).mock(
        return_value=httpx.Response(200, json={"data": _call_record_resource()})
    )

    async with client:
        record = await client.pbx.call_records.get(CALL_RECORD_ID)

    assert isinstance(record, CallRecord)
    assert record.id == CALL_RECORD_ID
    assert record.direction == "outbound"
    assert record.vendor_type == 0
    assert record.duration == 64
    assert record.talk_time == 60
    assert record.has_recording is False
    assert record.started_at == datetime(2026, 9, 12, 14, 0, 0, tzinfo=timezone.utc)
    assert record.answered_at == datetime(2026, 9, 12, 14, 0, 4, tzinfo=timezone.utc)
    assert record.released_at == datetime(2026, 9, 12, 14, 1, 4, tzinfo=timezone.utc)
    # The outbound leg resolves to a subscriber; the far end does not.
    assert record.from_pbx_user_id == USER_ID
    assert record.to_pbx_user_id is None


@pytest.mark.anyio
async def test_a_range_wider_than_the_ceiling_is_the_servers_refusal_to_make(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.get(CALL_RECORDS_URL).mock(
        return_value=httpx.Response(
            400,
            json={
                "errors": [
                    {
                        "status": "400",
                        "code": "invalid_query",
                        "title": "Bad query",
                        "detail": "The date range may not be wider than 13 months.",
                        "meta": {"filter": {"maxMonths": 13}},
                    }
                ]
            },
        )
    )

    async with client:
        with pytest.raises(ApiError) as caught:
            await client.pbx.call_records.list(
                started_after="2020-01-01T00:00:00Z", started_before="2026-09-01T00:00:00Z"
            )

    assert caught.value.status_code == 400
    assert caught.value.errors[0].meta == {"filter": {"maxMonths": 13}}


@pytest.mark.anyio
async def test_an_empty_call_record_id_is_refused_by_its_own_name(client: AsyncRingivo) -> None:
    async with client:
        with pytest.raises(ValueError, match="a call record id is required"):
            await client.pbx.call_records.get("")


# -- users.call (click-to-dial) --------------------------------------------


@pytest.mark.anyio
async def test_call_posts_a_jsonapi_document_under_the_users_own_path(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.post(CALLS_URL).mock(
        return_value=httpx.Response(202, json={"data": _call_resource()})
    )

    async with client:
        placed = await client.pbx.users.call(USER_ID, destination="+13025046250")

    request = route.calls.last.request
    body = json.loads(request.content)

    assert request.url.path == f"/v1/pbx/users/{USER_ID}/calls"
    assert request.headers["content-type"] == JSONAPI
    assert body["data"]["type"] == "calls"
    assert body["data"]["attributes"]["destination"] == "+13025046250"
    assert body["data"]["attributes"]["auto-answer"] is False
    # Absent, not null — there is nothing to clear on a create.
    assert "caller-id" not in body["data"]["attributes"]
    assert "device" not in body["data"]["attributes"]
    assert isinstance(placed, PbxCall)
    assert placed.status == "requested"


@pytest.mark.anyio
async def test_call_sends_every_optional_attribute_it_was_given(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.post(CALLS_URL).mock(
        return_value=httpx.Response(
            202,
            json={
                "data": _call_resource(
                    attributes={
                        "caller-id": "+14075550101",
                        "auto-answer": True,
                        "device": DEVICE_ID,
                    }
                )
            },
        )
    )

    async with client:
        placed = await client.pbx.users.call(
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
    assert placed.id == CALL_ID
    assert placed.device == DEVICE_ID
    assert placed.auto_answer is True
    assert placed.requested_at == datetime(2026, 9, 15, 9, 30, 0, tzinfo=timezone.utc)


@pytest.mark.anyio
async def test_a_device_that_is_not_this_users_is_refused_with_a_pointer(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
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

    async with client:
        with pytest.raises(ApiError) as caught:
            await client.pbx.users.call(
                USER_ID, destination="+13025046250", device="0198c7f2-dead-7000-8000-000000000000"
            )

    assert caught.value.status_code == 422
    assert caught.value.errors[0].source == {"pointer": "/data/attributes/device"}


@pytest.mark.anyio
async def test_an_empty_pbx_user_id_is_refused_before_a_phone_can_ring(
    client: AsyncRingivo,
) -> None:
    async with client:
        with pytest.raises(ValueError, match="a PBX user id is required"):
            await client.pbx.users.call("", destination="+13025046250")
