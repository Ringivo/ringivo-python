"""`client.inbound_messages`, asserted on the WIRE.

`list()`'s job is to build a query string, which is not observable from
the return value, so the tests read the request that went out. The page is
read from the spec's own example, so a spec sync that reshapes it fails
here instead of leaving a hand copy behind.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
import pytest
import respx

from ringivo import ApiError, InboundMessage, InboundMessagePage, Ringivo

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
                "scope": "numbers:messaging",
                "scopes": ["numbers:messaging"],
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
        scopes=["numbers:messaging"],
    )


@pytest.fixture
def list_example(openapi_spec: dict[str, Any]) -> dict[str, Any]:
    """The spec's 200 example for `GET /v1/inbound-messages`."""
    return openapi_spec["paths"]["/v1/inbound-messages"]["get"]["responses"]["200"]["content"][
        JSONAPI
    ]["example"]


def _mms_resource() -> dict[str, Any]:
    return {
        "type": "inbound-messages",
        "id": MESSAGE_ID,
        "attributes": {
            "kind": "mms",
            "from": "+12003004000",
            "to": "+13215550101",
            "body": None,
            "media": [
                {"contentType": "text/vcard", "filename": "dana.vcf", "encoding": "base64", "bytes": 512},
            ],
            "receivedAt": "2026-09-03T09:14:02.000000Z",
            "createdAt": "2026-09-03T09:14:03.000000Z",
            "updatedAt": "2026-09-03T09:14:03.000000Z",
        },
    }


def test_list_reads_the_spec_example(
    client: Ringivo, respx_mock: respx.MockRouter, list_example: dict[str, Any]
) -> None:
    route = respx_mock.get(MESSAGES_URL).mock(return_value=httpx.Response(200, json=list_example))

    page = client.inbound_messages.list()

    assert isinstance(page, InboundMessagePage)
    assert len(page) == 1
    (message,) = page
    assert message is page[0]
    assert message.id == MESSAGE_ID
    assert message.kind == "sms"
    assert message.from_ == "+12003004000"
    assert message.to == "+13215550101"
    assert message.body == "Hello World"
    assert message.media == ()
    assert message.received_at == datetime(2026, 9, 3, 9, 14, 2, tzinfo=timezone.utc)
    assert message.created_at == datetime(2026, 9, 3, 9, 14, 3, tzinfo=timezone.utc)
    assert message.updated_at == datetime(2026, 9, 3, 9, 14, 3, tzinfo=timezone.utc)
    assert page.next_cursor is None
    assert page.raw == list_example
    sent = route.calls.last.request
    assert sent.headers["Accept"] == JSONAPI
    assert sent.url.query == b""


def test_list_sends_every_filter_and_the_cursor(client: Ringivo, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(MESSAGES_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [],
                "links": {"next": f"{MESSAGES_URL}?page[after]=c2"},
                "meta": {"page": {"nextCursor": "c2"}},
            },
        )
    )

    page = client.inbound_messages.list(
        number="+13215550101",
        from_="+12003004000",
        kind="mms",
        received_after="2026-09-01T00:00:00Z",
        received_before="2026-09-30T23:59:59Z",
        ids=["a", "b"],
        after="c1",
        page_size=50,
    )

    params = route.calls.last.request.url.params
    assert params["filter[number]"] == "+13215550101"
    assert params["filter[from]"] == "+12003004000"
    assert params["filter[kind]"] == "mms"
    assert params["filter[receivedAfter]"] == "2026-09-01T00:00:00Z"
    assert params["filter[receivedBefore]"] == "2026-09-30T23:59:59Z"
    assert params.get_list("filter[id][]") == ["a", "b"]
    assert params["page[after]"] == "c1"
    assert params["page[size]"] == "50"
    assert "page[before]" not in params
    assert page.next_cursor == "c2"
    assert page.next_url == f"{MESSAGES_URL}?page[after]=c2"
    assert len(page) == 0


def test_list_refuses_one_bare_id_string_before_any_request(
    client: Ringivo, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(MESSAGES_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    with pytest.raises(ValueError, match="not one string"):
        client.inbound_messages.list(ids=MESSAGE_ID)

    assert not route.called


def test_every_list_filter_is_one_the_spec_publishes(
    client: Ringivo, respx_mock: respx.MockRouter, openapi_spec: dict[str, Any]
) -> None:
    published = {
        parameter["name"]
        for parameter in openapi_spec["paths"]["/v1/inbound-messages"]["get"]["parameters"]
        if "name" in parameter
    }
    route = respx_mock.get(MESSAGES_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    client.inbound_messages.list(
        number="n", from_="f", kind="sms", received_after="a", received_before="b", ids=["i"]
    )

    sent = {key for key in route.calls.last.request.url.params if key.startswith("filter[")}
    assert sent == published


def test_get_reads_one_message_and_its_attachments(client: Ringivo, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(f"{MESSAGES_URL}/{MESSAGE_ID}").mock(
        return_value=httpx.Response(200, json={"data": _mms_resource()})
    )

    message = client.inbound_messages.get(MESSAGE_ID)

    assert isinstance(message, InboundMessage)
    assert route.called
    assert message.kind == "mms"
    assert message.body is None
    (part,) = message.media
    assert part.content_type == "text/vcard"
    assert part.filename == "dana.vcf"
    assert part.encoding == "base64"
    assert part.byte_size == 512


def test_an_inbound_message_id_stays_inside_its_own_path_segment(
    client: Ringivo, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(200, json={"data": _mms_resource()})
    )

    client.inbound_messages.get("../fax-accounts/secret")

    assert route.calls.last.request.url.raw_path == b"/v1/inbound-messages/..%2Ffax-accounts%2Fsecret"


def test_get_refuses_an_empty_id(client: Ringivo) -> None:
    with pytest.raises(ValueError, match="inbound message id is required"):
        client.inbound_messages.get("")


def test_a_404_is_an_api_error(client: Ringivo, respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{MESSAGES_URL}/{MESSAGE_ID}").mock(
        return_value=httpx.Response(404, json={"errors": [{"status": "404", "title": "Not Found"}]})
    )

    with pytest.raises(ApiError) as caught:
        client.inbound_messages.get(MESSAGE_ID)

    assert caught.value.status_code == 404


@pytest.mark.parametrize(
    "document",
    [[], "x", {"data": "x"}, {"data": [None, "x", {"attributes": "x"}]}],
)
def test_a_malformed_page_reads_defensively(
    client: Ringivo, respx_mock: respx.MockRouter, document: Any
) -> None:
    respx_mock.get(MESSAGES_URL).mock(return_value=httpx.Response(200, json=document))

    page = client.inbound_messages.list()

    assert all(message.kind is None for message in page)
    assert page.next_cursor is None
