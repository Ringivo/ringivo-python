"""The fax surface again, awaited, and asserted on the WIRE.

The mirror of tests/test_faxes.py. `AsyncFaxes` is a sibling of `Faxes`
rather than a wrapper around it, so the bodies it builds and the query
strings it writes are its own code and get their own assertions: a twin
that spelled the multipart parts `documents` instead of `documents[]`
would pass the sync suite untouched.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
import respx

from ringivo import ApiError, AsyncRingivo, Fax, __version__

BASE_URL = "https://api.yourprovider.example"
TOKEN_URL = f"{BASE_URL}/oauth/token"
FAXES_URL = f"{BASE_URL}/v1/faxes"
FAX_ID = "0198c4a1-2b3c-7d4e-8f50-1a2b3c4d5e6f"
FAX_URL = f"{FAXES_URL}/{FAX_ID}"
ACCOUNT_ID = "0198c4a1-3c4d-7e5f-9061-2b3c4d5e6f70"


@pytest.fixture(autouse=True)
def _token(respx_mock: respx.MockRouter) -> None:
    """Every test here needs a credential to have been minted, not tested."""
    respx_mock.post(TOKEN_URL).mock(
        return_value=httpx.Response(
            200, json={"token_type": "Bearer", "access_token": "tok", "expires_in": 3600}
        )
    )


@pytest.fixture
def client() -> AsyncRingivo:
    return AsyncRingivo(base_url=BASE_URL, client_id="cid", client_secret="csecret")


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


@pytest.mark.anyio
async def test_send_uploads_the_pages_as_a_multipart_body(
    respx_mock: respx.MockRouter, client: AsyncRingivo, tmp_path: Path
) -> None:
    page = tmp_path / "chart-4471.pdf"
    page.write_bytes(b"%PDF-1.7 pretend")
    route = respx_mock.post(FAXES_URL).mock(return_value=httpx.Response(202, json=_accepted()))

    async with client:
        fax = await client.faxes.send(fax_account=ACCOUNT_ID, to="+13025556789", file=page)

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


@pytest.mark.anyio
async def test_send_takes_bytes_and_a_list_of_pages(
    respx_mock: respx.MockRouter, client: AsyncRingivo, tmp_path: Path
) -> None:
    page = tmp_path / "second.pdf"
    page.write_bytes(b"second-page-bytes")
    route = respx_mock.post(FAXES_URL).mock(return_value=httpx.Response(202, json=_accepted()))

    async with client:
        await client.faxes.send(
            fax_account=ACCOUNT_ID, to="+13025556789", file=[b"first-bytes", page]
        )

    body = route.calls.last.request.content.decode("utf-8", "replace")

    assert body.count('name="documents[]"') == 2
    assert "first-bytes" in body
    assert "second-page-bytes" in body


@pytest.mark.anyio
async def test_send_always_carries_an_idempotency_key_and_honours_the_one_given(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.post(FAXES_URL).mock(return_value=httpx.Response(202, json=_accepted()))

    async with client:
        await client.faxes.send(fax_account=ACCOUNT_ID, to="+1302", file=b"a")
        await client.faxes.send(fax_account=ACCOUNT_ID, to="+1302", file=b"a")
        await client.faxes.send(
            fax_account=ACCOUNT_ID, to="+1302", file=b"a", idempotency_key="chart-4471-attempt-1"
        )

    keys = [call.request.headers.get("Idempotency-Key") for call in route.calls]

    assert all(keys)
    assert keys[0] != keys[1], "a generated key must not repeat across sends"
    assert keys[2] == "chart-4471-attempt-1"


@pytest.mark.anyio
async def test_send_reports_whether_the_server_replayed_an_earlier_send(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.post(FAXES_URL).mock(
        return_value=httpx.Response(202, json=_accepted(), headers={"Idempotent-Replay": "true"})
    )

    async with client:
        replayed = await client.faxes.send(fax_account=ACCOUNT_ID, to="+1302", file=b"a")

    assert replayed.idempotent_replay is True

    respx_mock.post(FAXES_URL).mock(return_value=httpx.Response(202, json=_accepted()))

    async with AsyncRingivo(base_url=BASE_URL, client_id="c", client_secret="s") as fresh_client:
        fresh = await fresh_client.faxes.send(fax_account=ACCOUNT_ID, to="+1302", file=b"a")

    assert fresh.idempotent_replay is False


@pytest.mark.anyio
async def test_send_with_urls_posts_flat_json_and_never_a_jsonapi_document(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.post(FAXES_URL).mock(return_value=httpx.Response(202, json=_accepted()))

    async with client:
        await client.faxes.send(
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
    sent = httpx.Response(200, content=request.read()).json()

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


@pytest.mark.anyio
async def test_send_sends_tags_and_cover_page_as_json_typed_parts(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.post(FAXES_URL).mock(return_value=httpx.Response(202, json=_accepted()))

    async with client:
        await client.faxes.send(
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


@pytest.mark.anyio
async def test_send_refuses_to_guess_between_uploads_and_urls(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    async with client:
        with pytest.raises(ValueError, match="exactly one"):
            await client.faxes.send(fax_account=ACCOUNT_ID, to="+1302")

        with pytest.raises(ValueError, match="exactly one"):
            await client.faxes.send(
                fax_account=ACCOUNT_ID, to="+1302", file=b"a", urls=["https://example.test/a.pdf"]
            )


@pytest.mark.anyio
async def test_send_refuses_an_empty_document_before_anything_is_sent(
    respx_mock: respx.MockRouter, client: AsyncRingivo, tmp_path: Path
) -> None:
    """The same refusal, awaited — and asserted rather than assumed.

    `AsyncFaxes` reuses faxes.py's `_upload`, so this guard is inherited
    rather than mirrored. That is exactly why it is worth a test on this
    side: an async twin that grew its own copy of the upload helper would
    lose the check without a single line of faxes.py changing.
    """
    route = respx_mock.post(FAXES_URL).mock(return_value=httpx.Response(202, json=_accepted()))
    still_being_written = tmp_path / "chart-4471.pdf"
    still_being_written.write_bytes(b"")

    async with client:
        with pytest.raises(ValueError, match="empty document cannot be sent"):
            await client.faxes.send(fax_account=ACCOUNT_ID, to="+1302", file=b"")

        with pytest.raises(ValueError, match="empty document cannot be sent"):
            await client.faxes.send(fax_account=ACCOUNT_ID, to="+1302", file=still_being_written)

        with pytest.raises(ValueError, match="empty document cannot be sent"):
            await client.faxes.send(
                fax_account=ACCOUNT_ID, to="+1302", file=[b"%PDF-1.7 real", b""]
            )

    assert route.call_count == 0
    assert respx_mock.calls.call_count == 0, "an empty document reached the wire"


@pytest.mark.anyio
async def test_send_refuses_more_than_five_documents(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    async with client:
        with pytest.raises(ValueError, match="at most 5"):
            await client.faxes.send(fax_account=ACCOUNT_ID, to="+1302", file=[b"a"] * 6)


# -- get -------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_reads_a_jsonapi_document_into_the_public_dataclass(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.get(FAX_URL).mock(return_value=httpx.Response(200, json={"data": _fax_resource()}))

    async with client:
        fax = await client.faxes.get(FAX_ID)

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
    assert fax.raw["type"] == "faxes"


@pytest.mark.anyio
async def test_a_fax_id_stays_inside_its_own_path_segment(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    # The same escaping rule, and it has to be proved on this client too:
    # unquoted, `../fax-accounts/secret` normalises ON THE WIRE to
    # `/v1/fax-accounts/secret` — a different endpoint, read with this
    # client's token, that nobody asked for. Asserted on `raw_path`, which
    # is what goes out; `url.path` is a DECODED view and proves nothing.
    evil = "../fax-accounts/secret"
    route = respx_mock.route(host="api.yourprovider.example").mock(
        return_value=httpx.Response(200, json={"data": _fax_resource()})
    )

    async with client:
        await client.faxes.get(evil)

    assert route.calls.last.request.url.raw_path == b"/v1/faxes/..%2Ffax-accounts%2Fsecret"


@pytest.mark.anyio
async def test_get_speaks_jsonapi_and_can_side_load_the_attempts(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.get(FAX_URL).mock(
        return_value=httpx.Response(200, json={"data": _fax_resource()})
    )

    async with client:
        await client.faxes.get(FAX_ID, include="attempts")

    request = route.calls.last.request

    assert request.headers["accept"] == "application/vnd.api+json"
    assert request.url.params["include"] == "attempts"


@pytest.mark.anyio
async def test_a_fax_that_is_not_yours_raises_a_typed_404(
    respx_mock: respx.MockRouter, client: AsyncRingivo
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

    async with client:
        with pytest.raises(ApiError) as caught:
            await client.faxes.get(FAX_ID)

    assert caught.value.status_code == 404
    assert caught.value.code == "not_found"
    assert caught.value.errors[0].title == "Not found"


@pytest.mark.anyio
async def test_a_refused_send_carries_the_jsonapi_error_source(
    respx_mock: respx.MockRouter, client: AsyncRingivo
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

    async with client:
        with pytest.raises(ApiError) as caught:
            await client.faxes.send(fax_account=ACCOUNT_ID, to="not-e164", file=b"a")

    error = caught.value

    assert error.status_code == 422
    assert error.code == "validation_failed"
    assert error.errors[0].source == {"parameter": "to"}
    assert "The to field format is invalid." in str(error)


# -- list ------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_builds_the_filter_query_including_the_deep_object_tag(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.get(FAXES_URL).mock(return_value=httpx.Response(200, json={"data": []}))

    async with client:
        await client.faxes.list(
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


@pytest.mark.anyio
async def test_list_lifts_the_servers_own_cursor_out_of_the_next_link(
    respx_mock: respx.MockRouter, client: AsyncRingivo
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

    async with client:
        page = await client.faxes.list()

    assert len(page) == 1
    assert list(page)[0].id == FAX_ID
    assert page.next_cursor == "0198c4a1-next"
    assert page.next_url is not None and "page%5Bcursor%5D" in page.next_url


@pytest.mark.anyio
async def test_the_last_page_has_no_cursor_to_follow(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.get(FAXES_URL).mock(
        return_value=httpx.Response(200, json={"data": [], "links": {"next": None}})
    )

    async with client:
        page = await client.faxes.list()

    assert len(page) == 0
    assert page.next_cursor is None
    assert page.next_url is None


# -- cancel ----------------------------------------------------------------


@pytest.mark.anyio
async def test_cancel_posts_a_verb_and_returns_the_decision(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.post(f"{FAX_URL}/cancel").mock(
        return_value=httpx.Response(200, json={"data": {"id": FAX_ID, "status": "cancelled"}})
    )

    async with client:
        fax = await client.faxes.cancel(FAX_ID)

    assert route.calls.last.request.headers["accept"] == "application/json"
    assert fax.id == FAX_ID
    assert fax.status == "cancelled"


@pytest.mark.anyio
async def test_a_fax_the_far_end_answered_cannot_be_cancelled(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
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

    async with client:
        with pytest.raises(ApiError) as caught:
            await client.faxes.cancel(FAX_ID)

    assert caught.value.status_code == 409
    assert caught.value.code is None
    assert caught.value.errors[0].meta == {"reason": "answered"}


# -- media -----------------------------------------------------------------


@pytest.mark.anyio
async def test_media_mints_a_link_and_then_downloads_it_without_the_bearer(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    # The URL is pre-signed and lives on the tenant's OWN API host — media
    # is served through their branded proxy — and it is still fetched with
    # no bearer token. Same host is exactly why this test is worth having:
    # the URL is a capability for one document, the token reads every fax
    # this client can reach, and "it is our own host" is not a reason to
    # staple the second to the first.
    download_url = f"{BASE_URL}/media/0198c4a1/document.pdf?signature=abc"
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

    async with client:
        content = await client.faxes.media(FAX_ID)

    assert content == b"%PDF-1.7 the real pages"
    assert link.calls.last.request.headers["authorization"] == "Bearer tok"
    assert "authorization" not in download.calls.last.request.headers
    # It drops the token and NOTHING else: the download is still this SDK
    # asking, and an operator reading the tenant API host's access log should
    # see which client fetched the document.
    assert download.calls.last.request.headers["user-agent"] == f"Ringivo/Python {__version__}"
    assert link.calls.last.request.url.params["format"] == "pdf"


@pytest.mark.anyio
async def test_media_link_hands_back_the_capability_and_its_facts(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    route = respx_mock.get(f"{FAX_URL}/media").mock(
        return_value=httpx.Response(
            200,
            json={
                "url": f"{BASE_URL}/media/0198c4a1/document.tiff?signature=abc",
                "expires_at": "2026-08-16T11:07:31+00:00",
                "byte_size": 128,
                "sha256": "d" * 64,
            },
        )
    )

    async with client:
        media = await client.faxes.media_link(FAX_ID, format="tiff")

    assert route.calls.last.request.url.params["format"] == "tiff"
    assert media.url.endswith("signature=abc")
    assert media.byte_size == 128
    assert media.expires_at == datetime(2026, 8, 16, 11, 7, 31, tzinfo=timezone.utc)


@pytest.mark.anyio
async def test_a_fax_with_no_rendered_document_yet_is_a_typed_404(
    respx_mock: respx.MockRouter, client: AsyncRingivo
) -> None:
    respx_mock.get(f"{FAX_URL}/media").mock(
        return_value=httpx.Response(
            404, json={"errors": [{"status": "404", "code": "not_found", "title": "Not found"}]}
        )
    )

    async with client:
        with pytest.raises(ApiError) as caught:
            await client.faxes.media(FAX_ID)

    assert caught.value.status_code == 404
