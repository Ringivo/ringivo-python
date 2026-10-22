"""`AsyncRingivo.inbound_messages`: the same wire as the sync twin, awaited."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

from ringivo import AsyncRingivo, InboundMessage, InboundMessagePage

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
