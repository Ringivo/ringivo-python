"""`AsyncRingivo.inbound_messages`: the same wire as the sync twin, awaited."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
import pytest
import respx

from ringivo import (
    ApiError,
    AsyncRingivo,
    InboundMessage,
    InboundMessageMediaItem,
    InboundMessageMediaWithLink,
    InboundMessagePage,
    __version__,
)

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
MESSAGES_URL = f"{BASE_URL}/v1/inbound-messages"
MESSAGE_ID = "0198c4a1-8f70-7081-b283-4d5e6f708301"
TENANT = "0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8"
JSONAPI = "application/vnd.api+json"


@pytest.fixture(autouse=True)
def _token(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "token_type": "Bearer",
                "access_token": "tok",
                "expires_in": 900,
                "scope": "numbers:read",
                "scopes": ["numbers:read"],
            },
        )
    )


def _client() -> AsyncRingivo:
    return AsyncRingivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=["numbers:read"],
    )


@pytest.mark.anyio
async def test_list_sends_the_filters_and_reads_the_page(
    respx_mock: respx.MockRouter, openapi_spec: dict[str, Any]
) -> None:
    example = openapi_spec["paths"]["/v1/inbound-messages"]["get"]["responses"]["200"]["content"][
        JSONAPI
    ]["example"]
    route = respx_mock.get(MESSAGES_URL).mock(return_value=httpx.Response(200, json=example))

    async with _client() as client:
        page = await client.inbound_messages.list(
            number="+13215550101", kind="sms", ids=["a"], before="c0", page_size=10
        )

    params = route.calls.last.request.url.params
    assert params["filter[number]"] == "+13215550101"
    assert params["filter[kind]"] == "sms"
    assert params.get_list("filter[id][]") == ["a"]
    assert params["page[before]"] == "c0"
    assert params["page[size]"] == "10"
    assert isinstance(page, InboundMessagePage)
    (message,) = page
    assert message.id == MESSAGE_ID
    assert message.body == "Hello World"


@pytest.mark.anyio
async def test_list_refuses_one_bare_id_string(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(MESSAGES_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    async with _client() as client:
        with pytest.raises(ValueError, match="not one string"):
            await client.inbound_messages.list(ids=MESSAGE_ID)

    assert not route.called


@pytest.mark.anyio
async def test_get_reads_one_message(respx_mock: respx.MockRouter) -> None:
    resource = {
        "type": "inbound-messages",
        "id": MESSAGE_ID,
        "attributes": {"kind": "sms", "from": "+12003004000", "to": "+13215550101", "body": "Hi"},
    }
    respx_mock.get(f"{MESSAGES_URL}/{MESSAGE_ID}").mock(
        return_value=httpx.Response(200, json={"data": resource})
    )

    async with _client() as client:
        message = await client.inbound_messages.get(MESSAGE_ID)

    assert isinstance(message, InboundMessage)
    assert message.body == "Hi"
    assert message.media == ()


def _media_link(spec: dict[str, Any]) -> dict[str, str]:
    """The spec's own examples for a media item's `contentUrl` and `expiresAt`."""
    properties = spec["components"]["schemas"]["InboundMessageMediaWithLink"]["properties"]
    return {
        "contentUrl": properties["contentUrl"]["example"],
        "expiresAt": properties["expiresAt"]["example"],
    }


def _held_item(link: dict[str, str]) -> dict[str, Any]:
    return {"contentType": "image/jpeg", "filename": "photo.jpg", "size": 40213, **link}


@pytest.mark.anyio
async def test_get_reads_the_media_link_and_download_media_follows_it_without_the_bearer(
    respx_mock: respx.MockRouter, openapi_spec: dict[str, Any]
) -> None:
    link = _media_link(openapi_spec)
    resource = {
        "type": "inbound-messages",
        "id": MESSAGE_ID,
        "attributes": {"kind": "mms", "media": [_held_item(link)]},
    }
    api = respx_mock.get(f"{MESSAGES_URL}/{MESSAGE_ID}").mock(
        return_value=httpx.Response(200, json={"data": resource})
    )
    download = respx_mock.get(link["contentUrl"]).mock(
        return_value=httpx.Response(200, content=b"\xff\xd8\xff the photo")
    )

    async with _client() as client:
        message = await client.inbound_messages.get(MESSAGE_ID)
        (item,) = message.media
        content = await client.inbound_messages.download_media(item)

    assert isinstance(item, InboundMessageMediaWithLink)
    assert item.content_url == link["contentUrl"]
    assert item.expires_at == datetime(2026, 8, 18, 12, 43, 57, tzinfo=timezone.utc)
    assert content == b"\xff\xd8\xff the photo"
    assert api.calls.last.request.headers["authorization"] == "Bearer tok"
    sent = download.calls.last.request
    assert "authorization" not in sent.headers
    assert sent.headers["user-agent"] == f"Ringivo/Python {__version__}"
    assert str(sent.url) == link["contentUrl"]


@pytest.mark.anyio
async def test_download_media_refuses_an_item_with_no_link_before_any_request(
    respx_mock: respx.MockRouter,
) -> None:
    route = respx_mock.route(host="api.yourprovider.example", method="GET")
    item = InboundMessageMediaWithLink(content_type="text/plain", size=26)

    async with _client() as client:
        with pytest.raises(ValueError, match="no download link"):
            await client.inbound_messages.download_media(item)

    assert not route.called


@pytest.mark.anyio
async def test_download_media_refuses_a_webhook_media_item(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.route(host="api.yourprovider.example", method="GET")
    item = InboundMessageMediaItem(content_type="image/jpeg", filename="photo.jpg", size=40213)

    async with _client() as client:
        with pytest.raises(TypeError, match=r"inbound_messages\.get\(\)"):
            await client.inbound_messages.download_media(item)  # type: ignore[arg-type]

    assert not route.called


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status", "code"),
    [(403, None), (404, "not_found")],
)
async def test_an_expired_or_missing_download_is_an_api_error(
    respx_mock: respx.MockRouter, openapi_spec: dict[str, Any], status: int, code: str | None
) -> None:
    link = _media_link(openapi_spec)
    error: dict[str, Any] = {"status": str(status), "title": "Invalid signature."}
    if code is not None:
        error["code"] = code
    respx_mock.get(link["contentUrl"]).mock(
        return_value=httpx.Response(status, json={"errors": [error]})
    )
    item = InboundMessageMediaWithLink._from_json(_held_item(link))

    async with _client() as client:
        with pytest.raises(ApiError) as caught:
            await client.inbound_messages.download_media(item)

    assert caught.value.status_code == status
    assert caught.value.code == code
