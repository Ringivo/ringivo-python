"""`AsyncRingivo.messages.record()`: the same wire as the sync twin.

The body rules are shared code (messages.py), so these tests prove the
async client posts the same document, reads the same answer, keeps the same
timeout floor and refuses before any request in the same way.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx
import pytest
import respx

from ringivo import ApiError, AsyncRingivo
from ringivo.messages import RECORD_MIN_TIMEOUT_SECONDS

# The same constants as tests/test_messages.py, repeated as every async test
# file here repeats its twin's: each file reads on its own.
BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
RECORD_URL = f"{BASE_URL}/v1/outbound-messages"
TENANT = "0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8"

#: The spec's request example for `POST /v1/outbound-messages`.
SPEC_REQUEST_EXAMPLE = {
    "data": {
        "type": "outbound-messages",
        "attributes": {
            "from": "+14075550142",
            "to": "+13215550187",
            "body": "Reminder: Rex is due for his rabies booster on Oct 24.",
            "media": [],
            "senderLabel": "Appointment reminder",
            "markConversationRead": False,
            "alreadySent": {
                "providerMessageId": "01JC8ZA1F5T3R8C2P6M0L4JSWQ",
                "providerPartIds": ["01JC8ZA1F5T3R8C2P6M0L4JSWQ"],
                "sentAt": "2026-10-19T15:02:44Z",
            },
        },
    }
}

#: The spec's 201 example.
SPEC_RESPONSE_EXAMPLE = {
    "data": {
        "type": "outbound-messages",
        "id": "0192f0c0-5d2e-7a1b-8c3d-4e5f60718293",
        "attributes": {
            "source": "recorded",
            "kind": "sms",
            "status": "sent",
            "from": "+14075550142",
            "to": "+13215550187",
            "body": "Reminder: Rex is due for his rabies booster on Oct 24.",
            "media": [],
            "senderLabel": "Appointment reminder",
            "markConversationRead": False,
            "sentAt": "2026-10-19T15:02:44.000000Z",
            "providerMessageId": "01JC8ZA1F5T3R8C2P6M0L4JSWQ",
            "providerPartIds": ["01JC8ZA1F5T3R8C2P6M0L4JSWQ"],
            "createdAt": "2026-10-19T15:02:45.000000Z",
            "updatedAt": "2026-10-19T15:02:45.000000Z",
        },
    }
}

SENT_AT = datetime(2026, 10, 19, 15, 2, 44, tzinfo=timezone.utc)


def _arguments(**overrides: object) -> dict[str, object]:
    arguments: dict[str, object] = {
        "from_": "+14075550142",
        "to": "+13215550187",
        "body": "Reminder: Rex is due for his rabies booster on Oct 24.",
        "sender_label": "Appointment reminder",
        "provider_message_id": "01JC8ZA1F5T3R8C2P6M0L4JSWQ",
        "provider_part_ids": ["01JC8ZA1F5T3R8C2P6M0L4JSWQ"],
        "sent_at": SENT_AT,
    }
    arguments.update(overrides)
    return arguments


@pytest.fixture(autouse=True)
def _token(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "token_type": "Bearer",
                "access_token": "tok",
                "expires_in": 900,
                "scope": "messages:record",
                "scopes": ["messages:record"],
            },
        )
    )


def _client(timeout: float = 30.0) -> AsyncRingivo:
    return AsyncRingivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=["messages:record"],
        timeout=timeout,
    )


@pytest.mark.anyio
async def test_record_posts_the_spec_example(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(RECORD_URL).mock(
        return_value=httpx.Response(201, json=SPEC_RESPONSE_EXAMPLE)
    )

    async with _client() as client:
        recorded = await client.messages.record(**_arguments())  # type: ignore[arg-type]

    sent = route.calls.last.request
    assert json.loads(sent.content) == SPEC_REQUEST_EXAMPLE
    assert sent.headers["Content-Type"] == "application/vnd.api+json"
    assert "Idempotency-Key" not in sent.headers
    assert recorded.replayed is False
    assert recorded.id == "0192f0c0-5d2e-7a1b-8c3d-4e5f60718293"


@pytest.mark.anyio
async def test_a_200_is_a_replay(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(RECORD_URL).mock(return_value=httpx.Response(200, json=SPEC_RESPONSE_EXAMPLE))

    async with _client() as client:
        recorded = await client.messages.record(**_arguments())  # type: ignore[arg-type]

    assert recorded.replayed is True


@pytest.mark.anyio
async def test_a_429_carries_retry_after(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(RECORD_URL).mock(
        return_value=httpx.Response(429, headers={"Retry-After": "9"}, json={"errors": []})
    )

    async with _client() as client:
        with pytest.raises(ApiError) as caught:
            await client.messages.record(**_arguments())  # type: ignore[arg-type]

    assert caught.value.status_code == 429
    assert caught.value.retry_after == 9


@pytest.mark.anyio
async def test_the_record_waits_at_least_the_floor(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(RECORD_URL).mock(
        return_value=httpx.Response(201, json=SPEC_RESPONSE_EXAMPLE)
    )

    async with _client(timeout=5.0) as client:
        await client.messages.record(**_arguments())  # type: ignore[arg-type]

    assert route.calls.last.request.extensions["timeout"]["read"] == RECORD_MIN_TIMEOUT_SECONDS


@pytest.mark.anyio
async def test_a_bad_label_is_refused_before_any_request(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(RECORD_URL).mock(return_value=httpx.Response(201))

    async with _client() as client:
        with pytest.raises(ValueError, match="one line"):
            await client.messages.record(**_arguments(sender_label="a\nb"))  # type: ignore[arg-type]

    assert not route.called
