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

from ringivo import (
    ApiError,
    InboundMessage,
    InboundMessageMediaItem,
    InboundMessageMediaWithLink,
    InboundMessagePage,
    Ringivo,
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


@pytest.fixture
def media_link(openapi_spec: dict[str, Any]) -> dict[str, str]:
    """The spec's own examples for a media item's `contentUrl` and `expiresAt`.

    Read from `InboundMessageMediaWithLink`, so the download URL these tests
    follow is the shape the API documents — on the API host, signed in the
    query — and not a hand copy.
    """
    properties = openapi_spec["components"]["schemas"]["InboundMessageMediaWithLink"]["properties"]
    return {
        "contentUrl": properties["contentUrl"]["example"],
        "expiresAt": properties["expiresAt"]["example"],
    }


def _mms_resource(*media: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "inbound-messages",
        "id": MESSAGE_ID,
        "attributes": {
            "kind": "mms",
            "from": "+12003004000",
            "to": "+13215550101",
            "body": None,
            "media": list(media)
            or [
                {
                    "contentType": "text/vcard",
                    "filename": "dana.vcf",
                    "size": 512,
                    "contentUrl": None,
                    "expiresAt": None,
                },
            ],
            "receivedAt": "2026-09-03T09:14:02.000000Z",
            "createdAt": "2026-09-03T09:14:03.000000Z",
            "updatedAt": "2026-09-03T09:14:03.000000Z",
        },
    }


def _held_item(link: dict[str, str]) -> dict[str, Any]:
    """A media item the platform holds the file of: it carries a link."""
    return {"contentType": "image/jpeg", "filename": "photo.jpg", "size": 40213, **link}


def _unheld_item() -> dict[str, Any]:
    """A media item the platform does not hold: both link members are null."""
    return {
        "contentType": "text/plain",
        "filename": None,
        "size": 26,
        "contentUrl": None,
        "expiresAt": None,
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


def test_list_sends_every_filter_and_the_cursor(
    client: Ringivo, respx_mock: respx.MockRouter
) -> None:
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


def test_get_reads_one_message_and_its_media(client: Ringivo, respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(f"{MESSAGES_URL}/{MESSAGE_ID}").mock(
        return_value=httpx.Response(200, json={"data": _mms_resource()})
    )

    message = client.inbound_messages.get(MESSAGE_ID)

    assert isinstance(message, InboundMessage)
    assert route.called
    assert message.kind == "mms"
    assert message.body is None
    (item,) = message.media
    assert isinstance(item, InboundMessageMediaWithLink)
    # Still an `InboundMessageMediaItem`: code written against 0.24 that
    # names the old class keeps working.
    assert isinstance(item, InboundMessageMediaItem)
    assert item.content_type == "text/vcard"
    assert item.filename == "dana.vcf"
    assert item.size == 512
    assert item.content_url is None
    assert item.expires_at is None


def test_list_reads_each_media_items_link_and_when_it_dies(
    client: Ringivo, respx_mock: respx.MockRouter, media_link: dict[str, str]
) -> None:
    respx_mock.get(MESSAGES_URL).mock(
        return_value=httpx.Response(
            200, json={"data": [_mms_resource(_held_item(media_link), _unheld_item())]}
        )
    )

    (message,) = client.inbound_messages.list()

    held, unheld = message.media
    assert isinstance(held, InboundMessageMediaWithLink)
    assert held.content_type == "image/jpeg"
    assert held.filename == "photo.jpg"
    assert held.size == 40213
    assert held.content_url == media_link["contentUrl"]
    assert held.expires_at == datetime(2026, 8, 18, 12, 43, 57, tzinfo=timezone.utc)
    assert held.raw == _held_item(media_link)
    assert isinstance(unheld, InboundMessageMediaWithLink)
    assert unheld.content_url is None
    assert unheld.expires_at is None


def test_get_reads_each_media_items_link(
    client: Ringivo, respx_mock: respx.MockRouter, media_link: dict[str, str]
) -> None:
    respx_mock.get(f"{MESSAGES_URL}/{MESSAGE_ID}").mock(
        return_value=httpx.Response(200, json={"data": _mms_resource(_held_item(media_link))})
    )

    message = client.inbound_messages.get(MESSAGE_ID)

    (item,) = message.media
    assert item.content_url == media_link["contentUrl"]
    assert item.expires_at == datetime(2026, 8, 18, 12, 43, 57, tzinfo=timezone.utc)


def test_a_link_member_of_the_wrong_type_reads_none(
    client: Ringivo, respx_mock: respx.MockRouter
) -> None:
    item = {"contentType": "image/jpeg", "size": 1, "contentUrl": 7, "expiresAt": "soon"}
    respx_mock.get(f"{MESSAGES_URL}/{MESSAGE_ID}").mock(
        return_value=httpx.Response(200, json={"data": _mms_resource(item)})
    )

    (read,) = client.inbound_messages.get(MESSAGE_ID).media

    assert read.content_url is None
    assert read.expires_at is None
    assert read.raw == item


# -- download_media -------------------------------------------------------------


def test_download_media_follows_the_link_without_the_bearer(
    client: Ringivo, respx_mock: respx.MockRouter, media_link: dict[str, str]
) -> None:
    # The link is on the tenant's OWN API host, the same host the bearer
    # token goes to — which is why this is worth asserting. The link reads
    # one file for five minutes; the token reads every message this client
    # can reach, and must never travel with the link.
    api = respx_mock.get(f"{MESSAGES_URL}/{MESSAGE_ID}").mock(
        return_value=httpx.Response(200, json={"data": _mms_resource(_held_item(media_link))})
    )
    download = respx_mock.get(media_link["contentUrl"]).mock(
        return_value=httpx.Response(200, content=b"\xff\xd8\xff the photo")
    )

    with client:
        (item,) = client.inbound_messages.get(MESSAGE_ID).media
        content = client.inbound_messages.download_media(item)

    assert content == b"\xff\xd8\xff the photo"
    assert api.calls.last.request.headers["authorization"] == "Bearer tok"
    sent = download.calls.last.request
    assert "authorization" not in sent.headers
    # It drops the token and nothing else: the API host's access log still
    # sees which client fetched the file.
    assert sent.headers["user-agent"] == f"Ringivo/Python {__version__}"
    # The link is followed exactly as minted: the signature covers all of it.
    assert str(sent.url) == media_link["contentUrl"]


@pytest.mark.parametrize(
    "content_url",
    # None is what the API sends for a file it does not hold. "" is never
    # sent (the spec says `format: uri`), but if it arrives it is refused the
    # same way, not followed into an `httpx.UnsupportedProtocol`.
    [None, ""],
)
def test_download_media_refuses_an_item_with_no_link_before_any_request(
    client: Ringivo, respx_mock: respx.MockRouter, content_url: str | None
) -> None:
    route = respx_mock.route(host="api.yourprovider.example", method="GET")
    item = InboundMessageMediaWithLink._from_json({**_unheld_item(), "contentUrl": content_url})

    with pytest.raises(ValueError, match="no download link") as caught:
        client.inbound_messages.download_media(item)

    assert "messaging provider" in str(caught.value)
    assert not route.called


def test_the_signed_link_stays_out_of_repr(
    client: Ringivo, respx_mock: respx.MockRouter, media_link: dict[str, str]
) -> None:
    # A logged message must not carry a working five-minute link into the
    # logs. The link is still on the attribute and on `raw`.
    respx_mock.get(f"{MESSAGES_URL}/{MESSAGE_ID}").mock(
        return_value=httpx.Response(200, json={"data": _mms_resource(_held_item(media_link))})
    )

    message = client.inbound_messages.get(MESSAGE_ID)
    (item,) = message.media

    assert item.content_url == media_link["contentUrl"]
    assert "signature=" not in repr(item)
    assert "signature=" not in repr(message)
    assert "content_url" not in repr(item)
    assert "expires_at=" in repr(item)


def test_download_media_refuses_a_webhook_media_item(
    client: Ringivo, respx_mock: respx.MockRouter
) -> None:
    # A `message.received` item has no link, by design. The refusal names
    # the way to one: read the message with `get()`.
    route = respx_mock.route(host="api.yourprovider.example", method="GET")
    item = InboundMessageMediaItem(content_type="image/jpeg", filename="photo.jpg", size=40213)

    with pytest.raises(TypeError, match=r"inbound_messages\.get\(\)"):
        client.inbound_messages.download_media(item)  # type: ignore[arg-type]

    assert not route.called


@pytest.mark.parametrize(
    ("status", "body", "headers"),
    [
        # A changed or expired link: the signature did not verify.
        (403, {"errors": [{"status": "403", "title": "Invalid signature."}]}, {}),
        # No such file to serve; every miss answers the same way.
        (404, {"errors": [{"status": "404", "code": "not_found", "title": "Not found"}]}, {}),
        # Downloads count against the API rate limit.
        (
            429,
            {"errors": [{"status": "429", "code": "rate_limited", "title": "Too many"}]},
            {"Retry-After": "12"},
        ),
    ],
)
def test_a_refused_download_is_an_api_error(
    client: Ringivo,
    respx_mock: respx.MockRouter,
    media_link: dict[str, str],
    status: int,
    body: dict[str, Any],
    headers: dict[str, str],
) -> None:
    respx_mock.get(media_link["contentUrl"]).mock(
        return_value=httpx.Response(status, json=body, headers=headers)
    )
    item = InboundMessageMediaWithLink._from_json(_held_item(media_link))

    with client, pytest.raises(ApiError) as caught:
        client.inbound_messages.download_media(item)

    assert caught.value.status_code == status
    assert caught.value.code == body["errors"][0].get("code")
    assert caught.value.retry_after == (12 if status == 429 else None)


def test_an_inbound_message_id_stays_inside_its_own_path_segment(
    client: Ringivo, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(200, json={"data": _mms_resource()})
    )

    client.inbound_messages.get("../fax-accounts/secret")

    assert (
        route.calls.last.request.url.raw_path == b"/v1/inbound-messages/..%2Ffax-accounts%2Fsecret"
    )


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
