"""The v1 naming cleanup bridge (0.14.x), asserted on the WIRE.

The API renamed eight filter keys and a few plain-JSON members from
snake_case to camelCase with no alias. This release works against the API on
BOTH sides of that deploy: it asks with the new filter names, falls back once
to the old ones on the exact 400 an unknown filter key gets, remembers which
spelling worked, and flips back the same way. It reads both spellings of the
renamed response members. The next release deletes all of it.

The refusal fixture is the API's real body for an unknown filter key,
captured from the console on 2026-09-24:

    {"errors": [{"detail": "Filter parameter fax_account is not allowed.",
                 "source": {"parameter": "filter"}, "status": "400",
                 "title": "Invalid Query Parameter"}]}
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
import respx

from ringivo import ApiError, AsyncRingivo, Ringivo

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
FAXES_URL = f"{BASE_URL}/v1/faxes"
DELIVERIES_URL = f"{BASE_URL}/v1/webhook-deliveries"
FAX_ID = "0198c4a1-2b3c-7d4e-8f50-1a2b3c4d5e6f"
ACCOUNT_ID = "0198c4a1-3c4d-7e5f-9061-2b3c4d5e6f70"
TENANT = "0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8"


def _unknown_filter(name: str) -> httpx.Response:
    return httpx.Response(
        400,
        json={
            "errors": [
                {
                    "detail": f"Filter parameter {name} is not allowed.",
                    "source": {"parameter": "filter"},
                    "status": "400",
                    "title": "Invalid Query Parameter",
                }
            ]
        },
    )


EMPTY_PAGE = httpx.Response(200, json={"data": []})


@pytest.fixture(autouse=True)
def _token(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "token_type": "Bearer",
                "access_token": "tok",
                "expires_in": 900,
                "scope": "fax:read fax:write webhooks:read",
                "scopes": ["fax:read", "fax:write", "webhooks:read"],
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
        scopes=["fax:read", "fax:write", "webhooks:read"],
    )


def _sent(route: respx.Route) -> list[dict[str, str]]:
    return [dict(call.request.url.params) for call in route.calls]


def test_an_api_with_the_rename_is_asked_once_in_the_new_names(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(FAXES_URL).mock(return_value=EMPTY_PAGE)

    with client:
        client.faxes.list(
            fax_account=ACCOUNT_ID,
            client_reference="chart-4471",
            created_after="2026-08-05",
            created_before="2026-08-20",
        )

    assert _sent(route) == [
        {
            "filter[faxAccount]": ACCOUNT_ID,
            "filter[clientReference]": "chart-4471",
            "filter[createdAfter]": "2026-08-05",
            "filter[createdBefore]": "2026-08-20",
        }
    ]


def test_an_api_before_the_rename_is_asked_again_in_the_old_names_and_remembered(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(FAXES_URL).mock(
        side_effect=[_unknown_filter("faxAccount"), EMPTY_PAGE, EMPTY_PAGE]
    )

    with client:
        client.faxes.list(fax_account=ACCOUNT_ID, status="received")
        # The second call goes straight to the spelling that worked: one
        # request, not a refusal and a retry every time.
        client.faxes.list(fax_account=ACCOUNT_ID)

    assert _sent(route) == [
        {"filter[faxAccount]": ACCOUNT_ID, "filter[status]": "received"},
        {"filter[fax_account]": ACCOUNT_ID, "filter[status]": "received"},
        {"filter[fax_account]": ACCOUNT_ID},
    ]


def test_a_process_that_learned_the_old_names_flips_back_when_the_api_is_renamed(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # A long-running worker started before the deploy learned the old names;
    # the API then takes the rename. The first refusal of the OLD name must
    # send it back to the new one rather than failing until a restart.
    route = respx_mock.get(DELIVERIES_URL).mock(
        side_effect=[
            _unknown_filter("eventType"),
            EMPTY_PAGE,
            _unknown_filter("event_type"),
            EMPTY_PAGE,
            EMPTY_PAGE,
        ]
    )

    with client:
        client.webhook_deliveries.list(event_type="fax.received")
        client.webhook_deliveries.list(event_type="fax.received")
        client.webhook_deliveries.list(event_type="fax.received")

    assert [list(params) for params in _sent(route)] == [
        ["filter[eventType]"],
        ["filter[event_type]"],
        ["filter[event_type]"],
        ["filter[eventType]"],
        ["filter[eventType]"],
    ]


def test_any_other_400_reaches_the_caller_untouched_and_is_never_retried(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(FAXES_URL).mock(
        return_value=httpx.Response(
            400,
            json={
                "errors": [
                    {
                        "detail": "The page size must not be greater than 100.",
                        "source": {"parameter": "page.size"},
                        "status": "400",
                    }
                ]
            },
        )
    )

    with client, pytest.raises(ApiError) as raised:
        client.faxes.list(fax_account=ACCOUNT_ID, page_size=1000)

    assert raised.value.status_code == 400
    assert route.call_count == 1


def test_an_unknown_filter_refusal_for_a_name_that_was_not_renamed_is_not_retried(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # `filter[status]` was never renamed, so a refusal naming it is the
    # caller's own problem, and a query with no renamed filter never
    # enters the bridge at all.
    route = respx_mock.get(FAXES_URL).mock(return_value=_unknown_filter("status"))

    with client, pytest.raises(ApiError):
        client.faxes.list(status="nonsense")

    assert route.call_count == 1


def test_the_send_acknowledgement_reads_the_new_names_and_falls_back_to_the_old(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    base = {"id": FAX_ID, "status": "queued", "direction": "outbound"}
    respx_mock.post(FAXES_URL).mock(
        side_effect=[
            httpx.Response(
                202,
                json={"data": {**base, "clientReference": "new", "createdAt": "2026-08-16T11:02:31+00:00"}},
            ),
            httpx.Response(
                202,
                json={"data": {**base, "client_reference": "old", "created_at": "2026-08-16T11:02:31+00:00"}},
            ),
        ]
    )

    with client:
        renamed = client.faxes.send(fax_account=ACCOUNT_ID, to="+13025556789", urls=["https://x.example/a.pdf"])
        legacy = client.faxes.send(fax_account=ACCOUNT_ID, to="+13025556789", urls=["https://x.example/a.pdf"])

    stamp = datetime(2026, 8, 16, 11, 2, 31, tzinfo=timezone.utc)
    assert (renamed.client_reference, renamed.created_at) == ("new", stamp)
    assert (legacy.client_reference, legacy.created_at) == ("old", stamp)


def test_the_media_link_reads_the_new_names_and_falls_back_to_the_old(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    url = f"{BASE_URL}/v1/faxes/{FAX_ID}/media/content?signature=abc"
    respx_mock.get(f"{FAXES_URL}/{FAX_ID}/media").mock(
        side_effect=[
            httpx.Response(
                200,
                json={"url": url, "expiresAt": "2026-08-16T11:07:31+00:00", "byteSize": 7, "sha256": "d" * 64},
            ),
            httpx.Response(
                200,
                json={"url": url, "expires_at": "2026-08-16T11:07:31+00:00", "byte_size": 7, "sha256": "d" * 64},
            ),
        ]
    )

    with client:
        renamed = client.faxes.media_link(FAX_ID)
        legacy = client.faxes.media_link(FAX_ID)

    stamp = datetime(2026, 8, 16, 11, 7, 31, tzinfo=timezone.utc)
    assert (renamed.expires_at, renamed.byte_size) == (stamp, 7)
    assert (legacy.expires_at, legacy.byte_size) == (stamp, 7)


@pytest.mark.anyio
async def test_the_async_client_bridges_the_same_way(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(f"{BASE_URL}/v1/webhook-endpoints").mock(
        side_effect=[_unknown_filter("scopeType"), EMPTY_PAGE, EMPTY_PAGE]
    )

    async with AsyncRingivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=["webhooks:read"],
    ) as client:
        await client.webhook_endpoints.list(scope_type="customer", scope_id=ACCOUNT_ID)
        await client.webhook_endpoints.list(scope_type="customer")

    assert [sorted(params) for params in _sent(route)] == [
        ["filter[scopeId]", "filter[scopeType]"],
        ["filter[scope_id]", "filter[scope_type]"],
        ["filter[scope_type]"],
    ]
