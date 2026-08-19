"""The fax surface, asserted on the WIRE.

Every test here checks the request that went out or the object that came
back, never an internal call. That is deliberate: `send()`'s whole job is to
build one of two very different bodies, `list()`'s is to build a query
string, and `media()`'s is to make two requests of which exactly one carries
our bearer token. None of that is observable from the return value alone.

The bodies are the ones the spec publishes — a `multipart/form-data` with
`documents[]` parts, or flat JSON whose `documents` is a list of https URLs,
and never a JSON:API document. A body carrying `data` is refused outright by
the server rather than half-obeyed, which is why the negative assertion in
test_send_with_urls_posts_flat_json is there.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
import respx

from ringivo import ApiError, Fax, Ringivo, __version__

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
FAXES_URL = f"{BASE_URL}/v1/faxes"
FAX_ID = "0198c4a1-2b3c-7d4e-8f50-1a2b3c4d5e6f"
FAX_URL = f"{FAXES_URL}/{FAX_ID}"
ACCOUNT_ID = "0198c4a1-3c4d-7e5f-9061-2b3c4d5e6f70"


@pytest.fixture(autouse=True)
def _token(respx_mock: respx.MockRouter) -> None:
    """Every test here needs a credential to have been minted, not tested.

    respx's own `respx_mock` fixture, rather than the `@respx.mock`
    decorator, because a decorator starts AFTER fixtures run — routes
    registered here would then survive into the next test.
    """
    respx_mock.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json={"token_type": "Bearer", "access_token": "tok", "expires_in": 3600}
        )
    )


@pytest.fixture
def client() -> Ringivo:
    return Ringivo(base_url=BASE_URL, client_id="cid", client_secret="csecret")


def _accepted(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": FAX_ID,
        "status": "queued",
        "direction": "outbound",
        "from": "+14075550100",
        "to": "+13025556789",
        "client_reference": "chart-4471",
        "created_at": "2026-08-16T11:02:31+00:00",
    }
    data.update(overrides)
    return {"data": data}


def _fax_resource() -> dict[str, object]:
    return {
        "type": "faxes",
        "id": FAX_ID,
        "attributes": {
            "direction": "inbound",
            "status": "received",
            "failureCode": None,
            "from": "+13025556789",
            "to": "+14075550100",
            "pagesTotal": 3,
            "pagesTransferred": 3,
            "partial": False,
            "attemptCount": 1,
            "resolution": "fine",
            "clientReference": None,
            "coverPage": None,
            "read": False,
            "archived": False,
            "tags": {"clinic": "north"},
            "documents": [
                {
                    "kind": "pdf",
                    "ordinal": 0,
                    "contentType": "application/pdf",
                    "byteSize": 40960,
                    "sha256": "a" * 64,
                    "pages": 3,
                }
            ],
            "createdAt": "2026-08-16T11:02:31.000000Z",
            "completedAt": "2026-08-16T11:03:04.000000Z",
        },
    }


# -- send ------------------------------------------------------------------


def test_send_uploads_the_pages_as_a_multipart_body(
    respx_mock: respx.MockRouter, client: Ringivo, tmp_path: Path
) -> None:
    page = tmp_path / "chart-4471.pdf"
    page.write_bytes(b"%PDF-1.7 pretend")
    route = respx_mock.post(FAXES_URL).mock(return_value=httpx.Response(202, json=_accepted()))

    with client:
        fax = client.faxes.send(fax_account=ACCOUNT_ID, to="+13025556789", file=page)

    request = route.calls.last.request
    body = request.content.decode("utf-8", "replace")

    assert request.headers["content-type"].startswith("multipart/form-data")
    # The four endpoints that are not JSON:API say so, and this is one.
    assert request.headers["accept"] == "application/json"
    assert 'name="fax_account"' in body
    assert ACCOUNT_ID in body
    assert 'name="to"' in body
    # `documents[]` is how the spec says to spell the file parts.
    assert 'name="documents[]"; filename="chart-4471.pdf"' in body
    assert "%PDF-1.7 pretend" in body
    assert fax.id == FAX_ID
    assert fax.status == "queued"
    assert isinstance(fax, Fax)


def test_send_takes_bytes_and_a_list_of_pages(
    respx_mock: respx.MockRouter, client: Ringivo, tmp_path: Path
) -> None:
    page = tmp_path / "second.pdf"
    page.write_bytes(b"second-page-bytes")
    route = respx_mock.post(FAXES_URL).mock(return_value=httpx.Response(202, json=_accepted()))

    with client:
        client.faxes.send(fax_account=ACCOUNT_ID, to="+13025556789", file=[b"first-bytes", page])

    body = route.calls.last.request.content.decode("utf-8", "replace")

    assert body.count('name="documents[]"') == 2
    assert "first-bytes" in body
    assert "second-page-bytes" in body


def test_send_always_carries_an_idempotency_key_and_honours_the_one_given(
    respx_mock: respx.MockRouter,
    client: Ringivo,
) -> None:
    # The header is MANDATORY on this endpoint, and it is what makes a retry
    # of a request whose response was never seen safe. A caller who does not
    # supply one still gets a valid single send; a caller who intends to
    # retry supplies their own and reuses it.
    route = respx_mock.post(FAXES_URL).mock(return_value=httpx.Response(202, json=_accepted()))

    with client:
        client.faxes.send(fax_account=ACCOUNT_ID, to="+1302", file=b"a")
        client.faxes.send(fax_account=ACCOUNT_ID, to="+1302", file=b"a")
        client.faxes.send(
            fax_account=ACCOUNT_ID, to="+1302", file=b"a", idempotency_key="chart-4471-attempt-1"
        )

    keys = [call.request.headers.get("Idempotency-Key") for call in route.calls]

    assert all(keys)
    assert keys[0] != keys[1], "a generated key must not repeat across sends"
    assert keys[2] == "chart-4471-attempt-1"


def test_send_reports_whether_the_server_replayed_an_earlier_send(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # `Idempotent-Replay: true` is the ONLY thing that tells a replay from a
    # fresh accept — the body is the same fax either way — so it would be
    # unrecoverable if this client dropped it.
    respx_mock.post(FAXES_URL).mock(
        return_value=httpx.Response(202, json=_accepted(), headers={"Idempotent-Replay": "true"})
    )

    with client:
        replayed = client.faxes.send(fax_account=ACCOUNT_ID, to="+1302", file=b"a")

    assert replayed.idempotent_replay is True

    respx_mock.post(FAXES_URL).mock(return_value=httpx.Response(202, json=_accepted()))

    with Ringivo(base_url=BASE_URL, client_id="c", client_secret="s") as fresh_client:
        fresh = fresh_client.faxes.send(fax_account=ACCOUNT_ID, to="+1302", file=b"a")

    assert fresh.idempotent_replay is False


def test_send_with_urls_posts_flat_json_and_never_a_jsonapi_document(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.post(FAXES_URL).mock(return_value=httpx.Response(202, json=_accepted()))

    with client:
        client.faxes.send(
            fax_account=ACCOUNT_ID,
            to="+13025556789",
            urls=["https://records.acme-vet.example/charts/4471.pdf"],
            from_="+14075550100",
            resolution="fine",
            client_reference="chart-4471",
            tags={"clinic": "north"},
            cover_page={"to_name": "Dr Ruiz", "subject": "Records"},
        )

    request = route.calls.last.request
    body = request.read()
    sent = httpx.Response(200, content=body).json()

    assert request.headers["content-type"].startswith("application/json")
    assert sent == {
        "fax_account": ACCOUNT_ID,
        "to": "+13025556789",
        "from": "+14075550100",
        "resolution": "fine",
        "client_reference": "chart-4471",
        "tags": {"clinic": "north"},
        "cover_page": {"to_name": "Dr Ruiz", "subject": "Records"},
        "documents": ["https://records.acme-vet.example/charts/4471.pdf"],
    }
    # A body carrying `data` is refused outright rather than half-obeyed.
    assert "data" not in sent


def test_send_sends_tags_and_cover_page_as_json_typed_parts(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The spec's multipart `encoding` gives both members `contentType:
    # application/json`, so they travel as JSON-typed form fields rather than
    # as bare strings a server would have to guess at.
    route = respx_mock.post(FAXES_URL).mock(return_value=httpx.Response(202, json=_accepted()))

    with client:
        client.faxes.send(
            fax_account=ACCOUNT_ID,
            to="+1302",
            file=b"a",
            tags={"clinic": "north"},
            cover_page={"to_name": "Dr Ruiz"},
        )

    body = route.calls.last.request.content.decode("utf-8", "replace")

    assert 'name="tags"\r\nContent-Type: application/json\r\n\r\n{"clinic": "north"}' in body
    assert 'name="cover_page"\r\nContent-Type: application/json' in body
    # A form field, not an upload: no filename, or a server reads it as a page.
    assert 'name="tags"; filename' not in body


def test_send_refuses_to_guess_between_uploads_and_urls(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # Uploads and URLs may not be mixed in one request, and a send with
    # neither has nothing to fax. Both are refused here rather than at the
    # server, because the server's answer would be a 422 the caller has to
    # read a spec to understand.
    with client:
        with pytest.raises(ValueError, match="exactly one"):
            client.faxes.send(fax_account=ACCOUNT_ID, to="+1302")

        with pytest.raises(ValueError, match="exactly one"):
            client.faxes.send(
                fax_account=ACCOUNT_ID, to="+1302", file=b"a", urls=["https://example.test/a.pdf"]
            )


def test_send_refuses_an_empty_document_before_anything_is_sent(
    respx_mock: respx.MockRouter, client: Ringivo, tmp_path: Path
) -> None:
    """A zero-byte page has nothing to fax, and it is caught here.

    The server refuses it too, but only after the upload — and the file
    that is empty is usually the one another process is still writing, so
    the caller wants to be told WHICH document, not handed a 422 about the
    whole send.

    The CALL COUNT is the assertion that carries the weight: a check that
    ran after the POST would satisfy `pytest.raises` just as well, and
    would have spent the request and burned the idempotency key.
    """
    route = respx_mock.post(FAXES_URL).mock(return_value=httpx.Response(202, json=_accepted()))
    still_being_written = tmp_path / "chart-4471.pdf"
    still_being_written.write_bytes(b"")

    with client:
        with pytest.raises(ValueError, match="empty document cannot be sent"):
            client.faxes.send(fax_account=ACCOUNT_ID, to="+1302", file=b"")

        with pytest.raises(ValueError, match="empty document cannot be sent"):
            client.faxes.send(fax_account=ACCOUNT_ID, to="+1302", file=still_being_written)

        # One good page beside an empty one is still the whole send refused:
        # a fax with a blank page in the middle is not what was asked for.
        with pytest.raises(ValueError, match="empty document cannot be sent"):
            client.faxes.send(fax_account=ACCOUNT_ID, to="+1302", file=[b"%PDF-1.7 real", b""])

    assert route.call_count == 0
    # Nothing at all, not even the token: the refusal happens before the
    # first request this client would otherwise have to make.
    assert respx_mock.calls.call_count == 0, "an empty document reached the wire"


def test_send_refuses_more_than_five_documents(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The ceiling counts uploads PLUS urls, which is why it is checked on the
    # total rather than on each body.
    with client, pytest.raises(ValueError, match="at most 5"):
        client.faxes.send(fax_account=ACCOUNT_ID, to="+1302", file=[b"a"] * 6)


# -- get -------------------------------------------------------------------


def test_get_reads_a_jsonapi_document_into_the_public_dataclass(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(FAX_URL).mock(return_value=httpx.Response(200, json={"data": _fax_resource()}))

    with client:
        fax = client.faxes.get(FAX_ID)

    assert fax.id == FAX_ID
    assert fax.direction == "inbound"
    assert fax.status == "received"
    assert fax.from_ == "+13025556789"
    assert fax.to == "+14075550100"
    assert fax.pages_total == 3
    assert fax.partial is False
    assert fax.read is False
    assert fax.tags == {"clinic": "north"}
    assert fax.created_at == datetime(2026, 8, 16, 11, 2, 31, tzinfo=timezone.utc)
    assert fax.completed_at == datetime(2026, 8, 16, 11, 3, 4, tzinfo=timezone.utc)
    assert len(fax.documents) == 1
    assert fax.documents[0].kind == "pdf"
    assert fax.documents[0].byte_size == 40960
    # The whole resource object is kept, so a member the API adds after this
    # release still reaches the caller.
    assert fax.raw["type"] == "faxes"


def test_a_fax_id_stays_inside_its_own_path_segment(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # A fax id is whatever the caller's own system handed them, and an id
    # carrying `/` or `..` must not be able to steer the request at a
    # DIFFERENT endpoint. Unquoted, `../fax-accounts/secret` normalises on the
    # wire to `/v1/fax-accounts/secret` — a real resource, read with this
    # client's token, that the caller never asked for.
    #
    # Asserted on `raw_path`, which is what goes on the wire. `url.path` is a
    # DECODED view and shows `/v1/faxes/../fax-accounts/secret` even when the
    # escaping is correct, so a test written against it proves nothing.
    evil = "../fax-accounts/secret"
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(200, json={"data": _fax_resource()})
    )

    with client:
        client.faxes.get(evil)

    assert route.calls.last.request.url.raw_path == b"/v1/faxes/..%2Ffax-accounts%2Fsecret"


def test_get_speaks_jsonapi_and_can_side_load_the_attempts(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(FAX_URL).mock(
        return_value=httpx.Response(200, json={"data": _fax_resource()})
    )

    with client:
        client.faxes.get(FAX_ID, include="attempts")

    request = route.calls.last.request

    assert request.headers["accept"] == "application/vnd.api+json"
    assert request.url.params["include"] == "attempts"


def test_a_fax_that_is_not_yours_raises_a_typed_404(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(FAX_URL).mock(
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
        client.faxes.get(FAX_ID)

    assert caught.value.status_code == 404
    assert caught.value.code == "not_found"
    assert caught.value.errors[0].title == "Not found"


def test_a_refused_send_carries_the_jsonapi_error_source(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.post(FAXES_URL).mock(
        return_value=httpx.Response(
            422,
            json={
                "errors": [
                    {
                        "status": "422",
                        "code": "validation_failed",
                        "title": "Invalid request",
                        "detail": "The to field format is invalid.",
                        "source": {"parameter": "to"},
                    }
                ]
            },
        )
    )

    with client, pytest.raises(ApiError) as caught:
        client.faxes.send(fax_account=ACCOUNT_ID, to="not-e164", file=b"a")

    error = caught.value

    assert error.status_code == 422
    assert error.code == "validation_failed"
    assert error.errors[0].source == {"parameter": "to"}
    assert "The to field format is invalid." in str(error)


# -- list ------------------------------------------------------------------


def test_list_builds_the_filter_query_including_the_deep_object_tag(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # `filter[tag][clinic]=north` — one query member per tag name, and two of
    # them mean BOTH. The wrapper is the part that matters: the generated
    # client drops it (see tests/test_generated_import.py), and a filter that
    # silently does nothing answers 200 with the WHOLE collection to a caller
    # who believes they narrowed it.
    route = respx_mock.get(FAXES_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    with client:
        client.faxes.list(
            direction="outbound",
            status="delivered",
            read=False,
            archived=None,
            tags={"clinic": "north", "site": "east"},
            page_size=50,
            cursor="0198c4a1",
        )

    params = route.calls.last.request.url.params

    assert params["filter[direction]"] == "outbound"
    assert params["filter[status]"] == "delivered"
    assert params["filter[read]"] == "false"
    assert params["filter[tag][clinic]"] == "north"
    assert params["filter[tag][site]"] == "east"
    assert params["page[size]"] == "50"
    assert params["page[cursor]"] == "0198c4a1"
    # An unset filter is absent, not empty: `filter[archived]=` would be a
    # 400 rather than "no opinion".
    assert "filter[archived]" not in params
    assert "filter[to]" not in params


def test_list_lifts_the_servers_own_cursor_out_of_the_next_link(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(FAXES_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [_fax_resource()],
                "links": {"next": f"{FAXES_URL}?page%5Bcursor%5D=0198c4a1-next&page%5Bsize%5D=50"},
            },
        )
    )

    with client:
        page = client.faxes.list()

    assert len(page) == 1
    assert list(page)[0].id == FAX_ID
    assert page.next_cursor == "0198c4a1-next"
    assert page.next_url is not None and "page%5Bcursor%5D" in page.next_url


def test_the_last_page_has_no_cursor_to_follow(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(FAXES_URL).mock(
        return_value=httpx.Response(200, json={"data": [], "links": {"next": None}})
    )

    with client:
        page = client.faxes.list()

    assert len(page) == 0
    assert page.next_cursor is None
    assert page.next_url is None


# -- cancel ----------------------------------------------------------------


def test_cancel_posts_a_verb_and_returns_the_decision(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.post(f"{FAX_URL}/cancel").mock(
        return_value=httpx.Response(200, json={"data": {"id": FAX_ID, "status": "cancelled"}})
    )

    with client:
        fax = client.faxes.cancel(FAX_ID)

    assert route.calls.last.request.headers["accept"] == "application/json"
    assert fax.id == FAX_ID
    assert fax.status == "cancelled"


def test_a_fax_the_far_end_answered_cannot_be_cancelled(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # This refusal carries no `code` — the status is the contract, and the
    # reason is in `meta`. A caller must be able to read it without one.
    respx_mock.post(f"{FAX_URL}/cancel").mock(
        return_value=httpx.Response(
            409,
            json={
                "errors": [
                    {
                        "status": "409",
                        "title": "Fax not cancellable",
                        "detail": "That fax's call has already been answered.",
                        "meta": {"reason": "answered"},
                    }
                ]
            },
        )
    )

    with client, pytest.raises(ApiError) as caught:
        client.faxes.cancel(FAX_ID)

    assert caught.value.status_code == 409
    assert caught.value.code is None
    assert caught.value.errors[0].meta == {"reason": "answered"}


# -- media -----------------------------------------------------------------


def test_media_mints_a_link_and_then_downloads_it_without_the_bearer(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    # The URL is pre-signed and points at an object store that is NOT the
    # API. Sending our bearer token there would hand a third party a
    # credential that reads every fax this client can reach.
    download_url = "https://objects.example.net/fax/0198c4a1/document.pdf?signature=abc"
    link = respx_mock.get(f"{FAX_URL}/media").mock(
        return_value=httpx.Response(
            200,
            json={
                "url": download_url,
                "expires_at": "2026-08-16T11:07:31+00:00",
                "byte_size": 40960,
                "sha256": "c" * 64,
            },
        )
    )
    download = respx_mock.get(download_url).mock(
        return_value=httpx.Response(200, content=b"%PDF-1.7 the real pages")
    )

    with client:
        content = client.faxes.media(FAX_ID)

    assert content == b"%PDF-1.7 the real pages"
    assert link.calls.last.request.headers["authorization"] == "Bearer tok"
    assert "authorization" not in download.calls.last.request.headers
    # It drops the token and NOTHING else: the download is still this SDK
    # asking, and an operator reading an object store's access log should see
    # which client fetched the document.
    assert download.calls.last.request.headers["user-agent"] == f"Ringivo/Python {__version__}"
    assert link.calls.last.request.url.params["format"] == "pdf"


def test_media_link_hands_back_the_capability_and_its_facts(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    route = respx_mock.get(f"{FAX_URL}/media").mock(
        return_value=httpx.Response(
            200,
            json={
                "url": "https://objects.example.net/fax/0198c4a1/document.tiff?signature=abc",
                "expires_at": "2026-08-16T11:07:31+00:00",
                "byte_size": 128,
                "sha256": "d" * 64,
            },
        )
    )

    with client:
        media = client.faxes.media_link(FAX_ID, format="tiff")

    assert route.calls.last.request.url.params["format"] == "tiff"
    assert media.url.endswith("signature=abc")
    assert media.byte_size == 128
    assert media.expires_at == datetime(2026, 8, 16, 11, 7, 31, tzinfo=timezone.utc)


def test_a_fax_with_no_rendered_document_yet_is_a_typed_404(
    respx_mock: respx.MockRouter, client: Ringivo
) -> None:
    respx_mock.get(f"{FAX_URL}/media").mock(
        return_value=httpx.Response(
            404, json={"errors": [{"status": "404", "code": "not_found", "title": "Not found"}]}
        )
    )

    with client, pytest.raises(ApiError) as caught:
        client.faxes.media(FAX_ID)

    assert caught.value.status_code == 404
