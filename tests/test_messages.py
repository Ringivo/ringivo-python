"""`client.messages.record()`, asserted on the WIRE.

The posted document is compared with the request example the spec
publishes for `POST /v1/outbound-messages`, copied here verbatim, so the
body this client builds is the one the contract documents. The refusals
assert that NO request went out: a `ValueError` must cost nothing.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pytest
import respx

from ringivo import ApiError, OutboundMessage, Ringivo, sender_label
from ringivo.messages import (
    MAX_MEDIA,
    MAX_PROVIDER_ID_LENGTH,
    MAX_SENDER_LABEL_CODE_POINTS,
    RECORD_MIN_TIMEOUT_SECONDS,
)

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
RECORD_URL = f"{BASE_URL}/v1/outbound-messages"
TENANT = "0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8"

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


@pytest.fixture
def client() -> Ringivo:
    return Ringivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=["messages:record"],
    )


def test_record_posts_the_spec_example_as_json_api(
    client: Ringivo,
    respx_mock: respx.MockRouter,
    request_example: dict[str, Any],
    response_example: dict[str, Any],
) -> None:
    route = respx_mock.post(RECORD_URL).mock(
        return_value=httpx.Response(201, json=response_example)
    )

    client.messages.record(**_arguments())  # type: ignore[arg-type]

    sent = route.calls.last.request
    assert json.loads(sent.content) == request_example
    assert sent.headers["Content-Type"] == "application/vnd.api+json"
    assert sent.headers["Accept"] == "application/vnd.api+json"
    assert sent.headers["Authorization"] == "Bearer tok"
    # The provider message id is the dedupe key; no second key is sent.
    assert "Idempotency-Key" not in sent.headers


def test_a_201_reads_the_record_and_is_not_a_replay(
    client: Ringivo, respx_mock: respx.MockRouter, response_example: dict[str, Any]
) -> None:
    respx_mock.post(RECORD_URL).mock(return_value=httpx.Response(201, json=response_example))

    recorded = client.messages.record(**_arguments())  # type: ignore[arg-type]

    assert isinstance(recorded, OutboundMessage)
    assert recorded.replayed is False
    assert recorded.id == "0192f0c0-5d2e-7a1b-8c3d-4e5f60718293"
    assert recorded.source == "recorded"
    assert recorded.kind == "sms"
    assert recorded.status == "sent"
    assert recorded.from_ == "+14075550142"
    assert recorded.to == "+13215550187"
    assert recorded.sender_label == "Appointment reminder"
    assert recorded.mark_conversation_read is False
    assert recorded.sent_at == SENT_AT
    assert recorded.provider_message_id == "01JC8ZA1F5T3R8C2P6M0L4JSWQ"
    assert recorded.provider_part_ids == ("01JC8ZA1F5T3R8C2P6M0L4JSWQ",)
    assert recorded.media == ()
    assert recorded.created_at == datetime(2026, 10, 19, 15, 2, 45, tzinfo=timezone.utc)


def test_a_200_is_a_replay_of_the_first_record(
    client: Ringivo, respx_mock: respx.MockRouter, response_example: dict[str, Any]
) -> None:
    respx_mock.post(RECORD_URL).mock(return_value=httpx.Response(200, json=response_example))

    recorded = client.messages.record(**_arguments())  # type: ignore[arg-type]

    assert recorded.replayed is True
    assert recorded.id == "0192f0c0-5d2e-7a1b-8c3d-4e5f60718293"


def test_pictures_mark_read_and_every_part_are_sent(
    client: Ringivo, respx_mock: respx.MockRouter, response_example: dict[str, Any]
) -> None:
    route = respx_mock.post(RECORD_URL).mock(
        return_value=httpx.Response(201, json=response_example)
    )
    eastern = timezone(timedelta(hours=-4))

    client.messages.record(
        **_arguments(  # type: ignore[arg-type]
            body=None,
            media_urls=["https://media.example.com/a.jpg", "https://media.example.com/b.jpg"],
            provider_part_ids=["part-1", "part-2"],
            mark_conversation_read=True,
            sent_at=datetime(2026, 10, 19, 11, 2, 44, 120000, tzinfo=eastern),
        )
    )

    attributes = json.loads(route.calls.last.request.content)["data"]["attributes"]
    assert attributes["body"] is None
    assert attributes["media"] == [
        {"url": "https://media.example.com/a.jpg"},
        {"url": "https://media.example.com/b.jpg"},
    ]
    assert attributes["markConversationRead"] is True
    assert attributes["alreadySent"]["providerPartIds"] == ["part-1", "part-2"]
    # Converted to UTC, sub-seconds kept.
    assert attributes["alreadySent"]["sentAt"] == "2026-10-19T15:02:44.120000Z"


def test_a_422_raises_with_the_pointer(client: Ringivo, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(RECORD_URL).mock(
        return_value=httpx.Response(
            422,
            json={
                "errors": [
                    {
                        "status": "422",
                        "title": "Record refused",
                        "detail": "The label must be one line.",
                        "source": {"pointer": "/data/attributes/senderLabel"},
                    }
                ]
            },
        )
    )

    with pytest.raises(ApiError) as caught:
        client.messages.record(**_arguments())  # type: ignore[arg-type]

    assert caught.value.status_code == 422
    assert caught.value.errors[0].source == {"pointer": "/data/attributes/senderLabel"}


def test_a_409_raises(client: Ringivo, respx_mock: respx.MockRouter) -> None:
    respx_mock.post(RECORD_URL).mock(
        return_value=httpx.Response(409, json={"errors": [{"status": "409", "title": "Conflict"}]})
    )

    with pytest.raises(ApiError) as caught:
        client.messages.record(**_arguments())  # type: ignore[arg-type]

    assert caught.value.status_code == 409


@pytest.mark.parametrize("status", [429, 503])
def test_a_429_or_503_carries_retry_after(
    client: Ringivo, respx_mock: respx.MockRouter, status: int
) -> None:
    respx_mock.post(RECORD_URL).mock(
        return_value=httpx.Response(
            status, headers={"Retry-After": "17"}, json={"errors": [{"status": str(status)}]}
        )
    )

    with pytest.raises(ApiError) as caught:
        client.messages.record(**_arguments())  # type: ignore[arg-type]

    assert caught.value.status_code == status
    assert caught.value.retry_after == 17


def test_the_record_waits_at_least_the_floor(
    respx_mock: respx.MockRouter, response_example: dict[str, Any]
) -> None:
    short = Ringivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=["messages:record"],
        timeout=5.0,
    )
    route = respx_mock.post(RECORD_URL).mock(
        return_value=httpx.Response(201, json=response_example)
    )

    short.messages.record(**_arguments())  # type: ignore[arg-type]

    timeout = route.calls.last.request.extensions["timeout"]
    assert timeout["read"] == RECORD_MIN_TIMEOUT_SECONDS


def test_a_longer_client_timeout_is_kept(
    respx_mock: respx.MockRouter, response_example: dict[str, Any]
) -> None:
    long = Ringivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=["messages:record"],
        timeout=60.0,
    )
    route = respx_mock.post(RECORD_URL).mock(
        return_value=httpx.Response(201, json=response_example)
    )

    long.messages.record(**_arguments())  # type: ignore[arg-type]

    assert route.calls.last.request.extensions["timeout"]["read"] == 60.0


def test_an_httpx_timeout_has_its_read_raised_to_the_floor(
    respx_mock: respx.MockRouter, response_example: dict[str, Any]
) -> None:
    """A client built with an `httpx.Timeout` must record, not raise a
    `TypeError` from comparing a `Timeout` with a float. The record waits
    for the answer, so the READ timeout is the one raised to the floor; the
    connect, write and pool timeouts are the caller's and are kept."""
    client = Ringivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=["messages:record"],
        timeout=httpx.Timeout(5.0, connect=2.0, write=3.0, pool=4.0),
    )
    route = respx_mock.post(RECORD_URL).mock(
        return_value=httpx.Response(201, json=response_example)
    )

    client.messages.record(**_arguments())  # type: ignore[arg-type]

    assert route.calls.last.request.extensions["timeout"] == {
        "connect": 2.0,
        "read": RECORD_MIN_TIMEOUT_SECONDS,
        "write": 3.0,
        "pool": 4.0,
    }


@pytest.mark.parametrize(
    ("timeout", "read"),
    [
        (httpx.Timeout(60.0), 60.0),  # a longer read is kept
        (httpx.Timeout(5.0, read=None), None),  # no read timeout stays none
    ],
)
def test_an_httpx_timeout_keeps_a_longer_or_absent_read(
    respx_mock: respx.MockRouter,
    response_example: dict[str, Any],
    timeout: httpx.Timeout,
    read: float | None,
) -> None:
    client = Ringivo(
        base_url=BASE_URL,
        client_id="cid",
        client_secret="csecret",
        tenant=TENANT,
        scopes=["messages:record"],
        timeout=timeout,
    )
    route = respx_mock.post(RECORD_URL).mock(
        return_value=httpx.Response(201, json=response_example)
    )

    client.messages.record(**_arguments())  # type: ignore[arg-type]

    assert route.calls.last.request.extensions["timeout"]["read"] == read


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"provider_message_id": ""}, "provider_message_id"),
        ({"provider_part_ids": []}, "provider_part_ids"),
        ({"provider_part_ids": "01JC8ZA1F5T3R8C2P6M0L4JSWQ"}, "not one string"),
        ({"provider_part_ids": ["ok", ""]}, "provider_part_ids"),
        ({"sent_at": datetime(2026, 10, 19, 15, 2, 44)}, "time zone"),
        ({"media_urls": [f"https://m.example.com/{n}.jpg" for n in range(11)]}, "at most 10"),
        ({"media_urls": ["http://m.example.com/a.jpg"]}, "https"),
        ({"media_urls": "https://m.example.com/a.jpg"}, "not one string"),
        ({"body": None}, "body or at least one attachment"),
        ({"sender_label": "  "}, "empty"),
        ({"sender_label": "Dana\nSmith"}, "one line"),
        ({"sender_label": "Dana Smith"}, "one line"),
        ({"sender_label": "​​"}, "visible"),
        ({"sender_label": "x" * (MAX_SENDER_LABEL_CODE_POINTS + 1)}, "at most 40"),
        ({"provider_message_id": "x" * (MAX_PROVIDER_ID_LENGTH + 1)}, "at most 128"),
        ({"provider_part_ids": ["x" * (MAX_PROVIDER_ID_LENGTH + 1)]}, "at most 128"),
        ({"provider_part_ids": ["part-1", "part-2", "part-1"]}, "must not repeat"),
    ],
)
def test_what_no_retry_can_fix_is_refused_before_any_request(
    client: Ringivo, respx_mock: respx.MockRouter, overrides: dict[str, object], message: str
) -> None:
    route = respx_mock.post(RECORD_URL).mock(return_value=httpx.Response(201))

    with pytest.raises(ValueError, match=message):
        client.messages.record(**_arguments(**overrides))  # type: ignore[arg-type]

    assert not route.called


def test_a_label_the_api_trims_is_accepted_and_sent_as_given(
    client: Ringivo, respx_mock: respx.MockRouter, response_example: dict[str, Any]
) -> None:
    route = respx_mock.post(RECORD_URL).mock(
        return_value=httpx.Response(201, json=response_example)
    )
    # 40 code points of emoji and a zero-width joiner, padded with spaces.
    label = "  " + "\U0001f436" * 39 + "‍  "

    client.messages.record(**_arguments(sender_label=label))  # type: ignore[arg-type]

    assert (
        json.loads(route.calls.last.request.content)["data"]["attributes"]["senderLabel"] == label
    )


# -- sender_label(): making a label from any text -----------------------------


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("Dana Smith", "Dana Smith"),
        ("  Dana \t\n Smith  ", "Dana Smith"),
        ("Dana\r\nSmith", "Dana Smith"),
        ("Dana Smith\x07", "Dana Smith"),
        ("Dr. Lee", "Dr. Lee"),
        ("x" * 50, "x" * MAX_SENDER_LABEL_CODE_POINTS),
        # A cut that ends on a space is trimmed again.
        ("a" * 39 + " bcd", "a" * 39),
        ("\U0001f436" * 45, "\U0001f436" * MAX_SENDER_LABEL_CODE_POINTS),
    ],
)
def test_sender_label_makes_a_valid_label(text: str, label: str) -> None:
    assert sender_label(text) == label


@pytest.mark.parametrize("text", ["", "   ", "\n\t", "​​"])
def test_sender_label_refuses_when_nothing_visible_is_left(text: str) -> None:
    with pytest.raises(ValueError, match="visible"):
        sender_label(text)


def test_a_made_label_is_always_accepted_by_record(
    client: Ringivo, respx_mock: respx.MockRouter, response_example: dict[str, Any]
) -> None:
    respx_mock.post(RECORD_URL).mock(return_value=httpx.Response(201, json=response_example))
    for text in ("  Dana \n Smith ", "y" * 90, "Dr. Lee\x00"):
        client.messages.record(**_arguments(sender_label=sender_label(text)))  # type: ignore[arg-type]


# -- The contract's limits, read from the spec --------------------------------


def _record_attributes(spec: dict[str, Any]) -> dict[str, Any]:
    request = spec["components"]["schemas"]["OutboundMessageRecordRequest"]
    return request["properties"]["data"]["properties"]["attributes"]["properties"]


def test_the_label_limit_is_the_specs(openapi_spec: dict[str, Any]) -> None:
    label = _record_attributes(openapi_spec)["senderLabel"]
    assert label["maxLength"] == MAX_SENDER_LABEL_CODE_POINTS
    assert label["minLength"] == 1


def test_the_attachment_limit_is_the_specs(openapi_spec: dict[str, Any]) -> None:
    assert _record_attributes(openapi_spec)["media"]["maxItems"] == MAX_MEDIA


def test_the_documented_attachment_sizes_are_the_specs(openapi_spec: dict[str, Any]) -> None:
    """The size limits are not checked here (only the API can see a link's
    size), but they are DOCUMENTED here, so a spec that changes them must
    fail this test instead of leaving the docstring behind."""
    import ringivo.messages

    description = openapi_spec["paths"]["/v1/outbound-messages"]["post"]["description"]
    flat = " ".join(description.split())
    assert "must be an attachment of at most 10 MB" in flat
    assert "at most 20 MB of attachments together" in flat
    assert "`text/plain` is refused" in flat

    documented = " ".join((ringivo.messages.__doc__ or "").split())
    assert "at most 10 attachments, at most 10 MB each and at most 20 MB together" in documented


def test_the_provider_id_limits_are_the_specs(openapi_spec: dict[str, Any]) -> None:
    already_sent = _record_attributes(openapi_spec)["alreadySent"]["properties"]
    assert already_sent["providerMessageId"]["maxLength"] == MAX_PROVIDER_ID_LENGTH
    assert already_sent["providerPartIds"]["items"]["maxLength"] == MAX_PROVIDER_ID_LENGTH
    assert already_sent["providerPartIds"]["minItems"] == 1


# -- What the API trims, and what it does not -----------------------------------


@pytest.mark.parametrize("separator", ["\x1c", "\x1d", "\x1e", "\x1f"])
def test_an_information_separator_is_a_control_character_not_space(
    client: Ringivo, respx_mock: respx.MockRouter, separator: str
) -> None:
    """Python's `str.isspace()` says True for U+001C-U+001F; the API's
    `[\\s\\p{Z}]` trim does not, so the label keeps it and is refused."""
    route = respx_mock.post(RECORD_URL).mock(return_value=httpx.Response(201))

    with pytest.raises(ValueError, match="one line"):
        client.messages.record(**_arguments(sender_label=f"{separator}Dana"))  # type: ignore[arg-type]

    assert not route.called
    assert sender_label(f"{separator}Dana{separator}") == "Dana"


@pytest.mark.parametrize("space", [" ", "\t", "\x85", "\u00a0", "\u3000", "\u2009"])
def test_white_space_the_api_trims_is_trimmed(
    client: Ringivo, respx_mock: respx.MockRouter, space: str, response_example: dict[str, Any]
) -> None:
    respx_mock.post(RECORD_URL).mock(return_value=httpx.Response(201, json=response_example))

    client.messages.record(**_arguments(sender_label=f"{space}Dana{space}"))  # type: ignore[arg-type]


def test_a_next_line_at_either_end_is_trimmed_but_not_inside(
    client: Ringivo, respx_mock: respx.MockRouter, response_example: dict[str, Any]
) -> None:
    """The API's PCRE trims U+0085 at either end and accepts "\\x85Rex"; inside
    the label it is still a control character."""
    route = respx_mock.post(RECORD_URL).mock(
        return_value=httpx.Response(201, json=response_example)
    )

    client.messages.record(**_arguments(sender_label="\x85Rex\x85"))  # type: ignore[arg-type]
    assert route.called

    with pytest.raises(ValueError, match="one line"):
        client.messages.record(**_arguments(sender_label="R\x85ex"))  # type: ignore[arg-type]
