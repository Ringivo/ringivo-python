"""Send a fax, read one, list them, cancel one, fetch its pages — awaited.

The SIBLING of faxes.py, method for method. Each body here is its twin's
body with an `await` on the one line that goes to the network; nothing is
shared between the two classes, because the only thing they could share is
the awaiting itself.

What IS shared is the module-private helpers faxes.py already owns —
`_documents`, `_upload`, `_path_segment` and the small JSON readers below.
Those are pure functions of their arguments, they touch no client, and one
of them (`_path_segment`) is a security control: a second copy of it is a
second thing to get wrong. So they are imported, not duplicated.

Read faxes.py for the whys: why this layer is hand-rolled httpx rather
than the vendored generated client, and why `POST /v1/faxes` has two
mutually exclusive bodies.
"""

from __future__ import annotations

import json as jsonlib
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .faxes import (
    _JSON,
    _MAX_DOCUMENTS,
    _data_object,
    _documents,
    _next_cursor,
    _next_link,
    _path_segment,
    _upload,
)
from .models import Fax, FaxPage, MediaLink

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .async_client import AsyncRingivo

__all__ = ["AsyncFaxes"]


class AsyncFaxes:
    """The `client.faxes` namespace on `AsyncRingivo`."""

    def __init__(self, client: AsyncRingivo) -> None:
        self._client = client

    async def send(
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
            response = await self._client._request(
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

            response = await self._client._request(
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

    async def get(self, fax_id: str, *, include: str | None = None) -> Fax:
        """Read one fax and its document metadata.

        Args:
            fax_id: The fax's id.
            include: `attempts` to side-load the per-call attempt records,
                which then arrive in `fax.raw`'s sibling `included` member.
        """
        response = await self._client._request(
            "GET",
            f"/v1/faxes/{_path_segment(fax_id)}",
            params={"include": include},
        )
        return Fax._from_resource(_data_object(response.json()))

    async def list(
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

        response = await self._client._request("GET", "/v1/faxes", params=params)
        document = response.json()
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

    async def cancel(self, fax_id: str) -> Fax:
        """Withdraw a fax before the far end answers.

        200, not 202: the decision is complete when this returns and no
        later result undoes it. Once the call has been answered, or the fax
        has finished, it cannot be cancelled — that is an `ApiError` whose
        status is 409 and whose `errors[0].meta["reason"]` is `answered` or
        `terminal`. That refusal carries no `code`; the status is the
        contract.
        """
        response = await self._client._request(
            "POST",
            f"/v1/faxes/{_path_segment(fax_id)}/cancel",
            accept=_JSON,
        )
        return Fax._from_acknowledgement(_data_object(response.json()))

    async def media_link(self, fax_id: str, *, format: str = "pdf") -> MediaLink:
        """Mint a short-lived download URL for a fax's document.

        Args:
            format: `pdf` is what a person reads; `tiff` is what went on
                the wire.

        Every call mints a fresh capability and records who asked, so the
        URL is not something to cache past `expires_at` or to pass on.
        """
        response = await self._client._request(
            "GET",
            f"/v1/faxes/{_path_segment(fax_id)}/media",
            accept=_JSON,
            params={"format": format},
        )
        payload = response.json()
        return MediaLink._from_json(payload if isinstance(payload, Mapping) else {})

    async def media(self, fax_id: str, *, format: str = "pdf") -> bytes:
        """The document's bytes: mint the link, then follow it.

        The download itself goes out UNAUTHENTICATED. The URL is
        pre-signed and lives on the tenant's own API host, but it is a
        capability in its own right — one document, briefly — so this
        client's bearer token, which reads every fax, never travels with
        it.

        A fax accepted a second ago has no rendered PDF yet, and a purged
        one has none any more; both are an `ApiError` with status 404.
        """
        link = await self.media_link(fax_id, format=format)
        return await self._client._download(link.url)
