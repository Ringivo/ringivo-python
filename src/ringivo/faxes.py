"""Send a fax, read one, list them, cancel one, fetch its pages.

-- WHY THIS IS HAND-ROLLED httpx AND NOT A GENERATED CLIENT --------------------
Up to 0.2.1 this package also vendored a whole generated client —
openapi-python-client output, 159 files, most of the wheel — kept as "the
typed record of the entire endpoint surface". 0.2.2 deleted it. Nothing
imported it, pyright was configured to skip it, and one of its endpoint
modules raised `NameError` the moment anything imported it, so the record it
was keeping had never been checked. What stands in its place is types alone
— `_generated_types.py`, one `TypedDict` per schema, which pyright DOES
check — and a public escape hatch, `Ringivo.request`, for the endpoints this
layer does not wrap.

The four reasons that client was never on the call path are the same four
that make a generated runtime the wrong shape here, and they are concrete
rather than stylistic:

1. `send_fax` COULD NOT BE IMPORTED. openapi-python-client 0.29.0 omits the
   `Unset` import for an endpoint whose requestBody declares two content
   types, and `POST /v1/faxes` declares multipart and JSON. 0.29.0 is still
   that generator's latest release.

2. `list_faxes` SERIALISED `filter[tag]` WRONGLY. Its deepObject handling
   ended with `params.update(json_filtertag)`, which puts `{"clinic":
   "north"}` on the query string as `clinic=north` — the `filter[tag]`
   wrapper dropped, so the filter silently did nothing while the caller
   believed they had narrowed the collection. What this module sends
   instead is asserted by tests/test_faxes.py::
   test_list_builds_the_filter_query_including_the_deep_object_tag.

3. The generated functions RETURNED their error documents rather than
   raising, so a wrapper had to inspect the status of every response
   anyway. Typed exceptions (errors.py) are what a caller can branch on.

4. The generated models spelled every field `X | None | Unset`, and
   `failure_code` as a union of three enum classes — the nullable-enum
   split. Unwrapping that for each of eighteen attributes is more code than
   reading the wire JSON, and a field the API adds tomorrow disappears until
   the next regenerate. The dataclasses in models.py read the JSON and keep
   the whole object in `.raw`, so a new server field reaches the caller
   immediately.

-- THE TWO SEND BODIES ---------------------------------------------------------
`POST /v1/faxes` takes EITHER `multipart/form-data` with `documents[]` file
parts OR flat JSON whose `documents` is a list of https URLs, and never both
in one request. `send()` takes `file=` for the first and `urls=` for the
second, and refuses to guess if it is given both or neither.
"""

from __future__ import annotations

import json as jsonlib
import mimetypes
import os
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from .models import Fax, FaxPage, MediaLink

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .client import Ringivo

__all__ = ["Faxes"]

#: The media type the four non-JSON:API endpoints speak.
_JSON = "application/json"

#: The ceiling counts uploads PLUS urls — it is the same five on both bodies.
_MAX_DOCUMENTS = 5


class Faxes:
    """The `client.faxes` namespace."""

    def __init__(self, client: Ringivo) -> None:
        self._client = client

    def send(
        self,
        *,
        fax_account: str,
        to: str,
        file: Path | bytes | Sequence[Path | bytes] | None = None,
        urls: Sequence[str] | None = None,
        from_: str | None = None,
        resolution: str | None = None,
        client_reference: str | None = None,
        tags: Mapping[str, str] | None = None,
        cover_page: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> Fax:
        """Send one outbound fax.

        Args:
            fax_account: The account to send from.
            to: The destination in E.164 — this string is dialled, so
                nothing looser will do.
            file: The pages to upload: one `Path`, one `bytes`, or a
                sequence of up to five of either. Give this or `urls`. A
                zero-byte page refuses the whole send, before any request
                goes out.
            urls: Up to five `https` URLs to fetch the pages from instead.
            from_: The caller ID. Omit it to use the account's default; a
                number the account does not hold is refused.
            resolution: `fine` or `standard`.
            client_reference: Your own reference, echoed back on the fax.
            tags: Your own flat labels. Replaced wholesale on a write.
            cover_page: `to_name`, `from_name`, `subject`, `message`.
            idempotency_key: Your key for this send. **A fresh UUID is
                generated when you do not pass one**, which makes a single
                call safe; pass your own — and reuse it — if you intend to
                retry a send whose response you never saw. Reusing a key
                replays the first fax instead of sending a second.

        Returns:
            The accepted fax. `202` means accepted, not sent: the render
            and the call happen afterwards, so this carries the
            acknowledgement fields only. Watch it finish with `get()`.
            `idempotent_replay` is True when the server said this response
            replays an earlier send — the only thing that tells the two
            apart, because the body is the same fax either way.
        """
        documents = _documents(file)
        if bool(documents) == bool(urls):
            raise ValueError(
                "send() needs exactly one of file= (uploaded pages) or urls= "
                "(https links); uploads and URLs may not be mixed in one request"
            )

        count = len(documents) + len(urls or ())
        if count > _MAX_DOCUMENTS:
            raise ValueError(
                f"a fax carries at most {_MAX_DOCUMENTS} documents, uploads and URLs "
                f"counted together; got {count}"
            )

        fields: dict[str, Any] = {"fax_account": fax_account, "to": to}
        if from_ is not None:
            fields["from"] = from_
        if resolution is not None:
            fields["resolution"] = resolution
        if client_reference is not None:
            fields["client_reference"] = client_reference

        headers = {"Idempotency-Key": idempotency_key or str(uuid.uuid4())}

        if urls:
            if tags is not None:
                fields["tags"] = dict(tags)
            if cover_page is not None:
                fields["cover_page"] = dict(cover_page)
            fields["documents"] = list(urls)
            response = self._client.request(
                "POST",
                "/v1/faxes",
                accept=_JSON,
                headers=headers,
                json=fields,
            )
        else:
            parts: list[tuple[str, Any]] = []
            # `tags` and `cover_page` are JSON-typed parts, as the spec's
            # multipart `encoding` says — a filename of None makes them form
            # fields rather than uploads while keeping the content type.
            if tags is not None:
                parts.append(("tags", (None, jsonlib.dumps(dict(tags)), _JSON)))
            if cover_page is not None:
                parts.append(("cover_page", (None, jsonlib.dumps(dict(cover_page)), _JSON)))
            for index, document in enumerate(documents):
                parts.append(("documents[]", _upload(document, index)))

            response = self._client.request(
                "POST",
                "/v1/faxes",
                accept=_JSON,
                headers=headers,
                data=fields,
                files=parts,
            )

        payload = _data_object(response.json())
        replayed = response.headers.get("Idempotent-Replay") == "true"
        return Fax._from_acknowledgement(payload, idempotent_replay=replayed)

    def get(self, fax_id: str, *, include: str | None = None) -> Fax:
        """Read one fax and its document metadata.

        Args:
            fax_id: The fax's id.
            include: `attempts` to side-load the per-call attempt records,
                which then arrive in `fax.raw`'s sibling `included` member.
        """
        response = self._client.request(
            "GET",
            f"/v1/faxes/{_path_segment(fax_id)}",
            params={"include": include},
        )
        return Fax._from_resource(_data_object(response.json()))

    def list(
        self,
        *,
        fax_account: str | None = None,
        direction: str | None = None,
        status: str | None = None,
        from_: str | None = None,
        to: str | None = None,
        client_reference: str | None = None,
        created_after: str | None = None,
        created_before: str | None = None,
        read: bool | None = None,
        archived: bool | None = None,
        tags: Mapping[str, str] | None = None,
        include: str | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> FaxPage:
        """One page of faxes, newest first — the inbox and the outbox together.

        The collection is cursor-paginated. Sortable fields are
        `createdAt` and `id`, newest first by default. A cursor is bound
        to the sort and filter it was minted under; replaying it against a
        different one is refused with a 400, rather than silently walking
        a re-sorted set.

        Args:
            after: Walk forward: the previous page's `FaxPage.next_cursor`.
                Mutually exclusive with `before` — passing both is refused
                with a 400.
            before: Walk backward from a cursor — how you poll for rows
                that arrived since your last read. Mutually exclusive with
                `after`.
            page_size: Rows per page. The default is 25 and the ceiling is
                100.
            tags: Match on your own tags, one member per tag name. Two of
                them mean BOTH, never either.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
            "include": include,
            "filter[fax_account]": fax_account,
            "filter[direction]": direction,
            "filter[status]": status,
            "filter[from]": from_,
            "filter[to]": to,
            "filter[client_reference]": client_reference,
            "filter[created_after]": created_after,
            "filter[created_before]": created_before,
            "filter[read]": read,
            "filter[archived]": archived,
        }
        for name, value in (tags or {}).items():
            params[f"filter[tag][{name}]"] = value

        document = self._client.request("GET", "/v1/faxes", params=params).json()
        if not isinstance(document, Mapping):
            document = {}

        data = document.get("data")
        faxes = tuple(
            Fax._from_resource(item)
            for item in (data if isinstance(data, list) else [])
            if isinstance(item, Mapping)
        )
        return FaxPage(
            faxes=faxes,
            next_url=_next_link(document),
            next_cursor=_next_cursor(document),
            raw=document,
        )

    def cancel(self, fax_id: str) -> Fax:
        """Withdraw a fax before the far end answers.

        200, not 202: the decision is complete when this returns and no
        later result undoes it. Once the call has been answered, or the fax
        has finished, it cannot be cancelled — that is an `ApiError` whose
        status is 409 and whose `errors[0].meta["reason"]` is `answered` or
        `terminal`. That refusal carries no `code`; the status is the
        contract.
        """
        response = self._client.request(
            "POST",
            f"/v1/faxes/{_path_segment(fax_id)}/cancel",
            accept=_JSON,
        )
        return Fax._from_acknowledgement(_data_object(response.json()))

    def media_link(self, fax_id: str, *, format: str = "pdf") -> MediaLink:
        """Mint a short-lived download URL for a fax's document.

        Args:
            format: `pdf` is what a person reads; `tiff` is what went on
                the wire.

        Every call mints a fresh capability and records who asked, so the
        URL is not something to cache past `expires_at` or to pass on.
        """
        response = self._client.request(
            "GET",
            f"/v1/faxes/{_path_segment(fax_id)}/media",
            accept=_JSON,
            params={"format": format},
        )
        payload = response.json()
        return MediaLink._from_json(payload if isinstance(payload, Mapping) else {})

    def media(self, fax_id: str, *, format: str = "pdf") -> bytes:
        """The document's bytes: mint the link, then follow it.

        The download itself goes out UNAUTHENTICATED. The URL is
        pre-signed and lives on the tenant's own API host, but it is a
        capability in its own right — one document, briefly — so this
        client's bearer token, which reads every fax, never travels with
        it.

        A fax accepted a second ago has no rendered PDF yet, and a purged
        one has none any more; both are an `ApiError` with status 404.
        """
        return self._client._download(self.media_link(fax_id, format=format).url)


def _documents(file: Path | bytes | Sequence[Path | bytes] | None) -> tuple[Path | bytes, ...]:
    if file is None:
        return ()
    if isinstance(file, (bytes, bytearray, memoryview)):
        return (bytes(file),)
    if isinstance(file, (str, os.PathLike)):
        return (Path(file),)
    if isinstance(file, Sequence):
        return tuple(_documents(item)[0] for item in file)
    raise TypeError(
        f"file= takes a pathlib.Path, bytes, or a sequence of them; got {type(file).__name__}"
    )


def _upload(document: Path | bytes, index: int) -> tuple[str, bytes, str]:
    """One `documents[]` part: a name, the bytes, and a declared type.

    The declared type is a courtesy for anything reading the request, not a
    claim: the server sniffs the BYTES, and neither the name nor the header
    decides what a document is.

    An empty document is refused HERE, and here is the only place that
    works: this is where a `Path` and a `bytes` value — two very different
    things on the way in — have both become the same read bytes. It runs
    while the multipart body is still being assembled, so a refusal costs
    no request and burns no idempotency key.
    """
    if isinstance(document, Path):
        name = document.name
        content = document.read_bytes()
    else:
        name = f"document-{index}"
        content = bytes(document)

    if not content:
        raise ValueError(
            f"an empty document cannot be sent: {name} is zero bytes. A file another "
            f"process is still writing is the usual cause."
        )

    guessed, _ = mimetypes.guess_type(name)
    return (name, content, guessed or "application/octet-stream")


def _path_segment(value: str) -> str:
    """One path segment, escaped so an id cannot steer the request.

    `safe=""` — nothing is left unescaped, `/` least of all. An id is
    whatever the caller's own system handed them, and an unescaped
    `../fax-accounts/secret` normalises ON THE WIRE to
    `/v1/fax-accounts/secret`: a different endpoint, read with this client's
    token, that nobody asked for. Ids are UUIDs in practice, so this escapes
    nothing on the happy path and costs nothing.
    """
    if not value:
        raise ValueError("a fax id is required")
    return quote(value, safe="")


def _data_object(payload: Any) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    data = payload.get("data")
    return data if isinstance(data, Mapping) else {}


def _next_link(document: Mapping[str, Any]) -> str | None:
    links = document.get("links")
    if not isinstance(links, Mapping):
        return None
    following = links.get("next")
    return following if isinstance(following, str) and following else None


def _next_cursor(document: Mapping[str, Any]) -> str | None:
    """The server's own cursor for the page that follows.

    Read out of `meta.page.nextCursor`, never `links.next` — the API
    documents the meta field as the authoritative mirror, present on every
    page including the last, where it is `null`. Never rebuilt — the value
    is read back out of what the server minted, so the client is passing
    the server its own token.
    """
    meta = document.get("meta")
    if not isinstance(meta, Mapping):
        return None
    page = meta.get("page")
    if not isinstance(page, Mapping):
        return None
    cursor = page.get("nextCursor")
    return cursor if isinstance(cursor, str) and cursor else None
