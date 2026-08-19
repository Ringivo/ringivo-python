"""What this client hands back: frozen, snake_cased, and ours.

Nothing generated ever crosses the public boundary. The generated models
under `ringivo._generated` are regenerated wholesale from the spec, so a
caller who held one would be holding a type whose fields, names and
nullability can change with a tool upgrade they never asked for. These
dataclasses change only when this package decides they do.

They are FROZEN because a fax is a record of something that already
happened. Assigning to one would look like it changed the fax and would
change nothing at all.

Every model keeps the JSON object it was built from in `raw`. A field the
API adds after this release still reaches the caller through it, so a new
server field never has to wait for a new SDK.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

__all__ = ["Fax", "FaxDocument", "FaxPage", "MediaLink"]


def _parse_datetime(value: Any) -> datetime | None:
    """An ISO-8601 instant as the API writes it, or None.

    The API writes both `...T11:02:31.000000Z` and `...T11:02:31+00:00`.
    `datetime.fromisoformat` only learned to read the `Z` form in Python
    3.11, and this package supports 3.10, so the `Z` is translated here
    rather than left to the standard library. An unparseable value yields
    None instead of raising: a timestamp this client cannot read is not a
    reason to refuse the caller their fax, and the original string is still
    in `raw`.
    """
    if not isinstance(value, str) or not value:
        return None
    text = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _text(source: Mapping[str, Any], key: str) -> str | None:
    value = source.get(key)
    return value if isinstance(value, str) else None


def _integer(source: Mapping[str, Any], key: str) -> int | None:
    value = source.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _boolean(source: Mapping[str, Any], key: str) -> bool | None:
    value = source.get(key)
    return value if isinstance(value, bool) else None


def _mapping(source: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = source.get(key)
    return value if isinstance(value, Mapping) else None


@dataclass(frozen=True)
class FaxDocument:
    """One of a fax's documents, described but never reachable from here.

    No object key and no URL is published on a fax. The bytes are reached
    only through `client.faxes.media()`, which mints a short-lived link and
    records who asked.
    """

    kind: str | None = None
    ordinal: int | None = None
    content_type: str | None = None
    byte_size: int | None = None
    sha256: str | None = None
    pages: int | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _from_json(cls, source: Mapping[str, Any]) -> FaxDocument:
        return cls(
            kind=_text(source, "kind"),
            ordinal=_integer(source, "ordinal"),
            content_type=_text(source, "contentType"),
            byte_size=_integer(source, "byteSize"),
            sha256=_text(source, "sha256"),
            pages=_integer(source, "pages"),
            raw=source,
        )


@dataclass(frozen=True)
class Fax:
    """One fax, inbound or outbound.

    `from_` carries the trailing underscore PEP 8 prescribes for a field
    whose name is a Python keyword; every other name is the API's own,
    snake_cased.

    Two constructors fill this in, and they do not fill in the same
    amount. A fax read with `faxes.get()` or `faxes.list()` is complete. A
    fax returned by `faxes.send()` or `faxes.cancel()` is the flat
    acknowledgement those endpoints answer — the fields it does not carry
    are None, and `faxes.get()` is where the rest lives.
    """

    id: str
    status: str | None = None
    direction: str | None = None
    from_: str | None = None
    to: str | None = None
    failure_code: str | None = None
    pages_total: int | None = None
    pages_transferred: int | None = None
    partial: bool | None = None
    attempt_count: int | None = None
    resolution: str | None = None
    client_reference: str | None = None
    cover_page: Mapping[str, Any] | None = None
    read: bool | None = None
    archived: bool | None = None
    tags: Mapping[str, Any] | None = None
    documents: tuple[FaxDocument, ...] = ()
    created_at: datetime | None = None
    completed_at: datetime | None = None
    idempotent_replay: bool | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _from_resource(cls, resource: Mapping[str, Any]) -> Fax:
        """Build from a JSON:API resource object — `faxes.get()`/`list()`."""
        attributes = _mapping(resource, "attributes") or {}
        documents = attributes.get("documents")

        return cls(
            id=_text(resource, "id") or "",
            status=_text(attributes, "status"),
            direction=_text(attributes, "direction"),
            from_=_text(attributes, "from"),
            to=_text(attributes, "to"),
            failure_code=_text(attributes, "failureCode"),
            pages_total=_integer(attributes, "pagesTotal"),
            pages_transferred=_integer(attributes, "pagesTransferred"),
            partial=_boolean(attributes, "partial"),
            attempt_count=_integer(attributes, "attemptCount"),
            resolution=_text(attributes, "resolution"),
            client_reference=_text(attributes, "clientReference"),
            cover_page=_mapping(attributes, "coverPage"),
            read=_boolean(attributes, "read"),
            archived=_boolean(attributes, "archived"),
            tags=_mapping(attributes, "tags"),
            documents=tuple(
                FaxDocument._from_json(d)
                for d in (documents if isinstance(documents, list) else [])
                if isinstance(d, Mapping)
            ),
            created_at=_parse_datetime(attributes.get("createdAt")),
            completed_at=_parse_datetime(attributes.get("completedAt")),
            raw=resource,
        )

    @classmethod
    def _from_acknowledgement(
        cls,
        payload: Mapping[str, Any],
        *,
        idempotent_replay: bool | None = None,
    ) -> Fax:
        """Build from the flat `data` object `send` and `cancel` answer.

        Their bodies are snake_cased plain JSON, not JSON:API documents —
        which is why this is a second constructor rather than a flag on the
        first one.
        """
        return cls(
            id=_text(payload, "id") or "",
            status=_text(payload, "status"),
            direction=_text(payload, "direction"),
            from_=_text(payload, "from"),
            to=_text(payload, "to"),
            client_reference=_text(payload, "client_reference"),
            created_at=_parse_datetime(payload.get("created_at")),
            idempotent_replay=idempotent_replay,
            raw=payload,
        )


@dataclass(frozen=True)
class FaxPage:
    """One page of `faxes.list()`, newest first.

    `next_cursor` is the server's own cursor, read from
    `meta.page.nextCursor` — never one this client built. The cursor
    encodes the row AND the direction, and its meaning belongs to the
    server; pass it straight back as `after=` to read the following page.
    It is None on the last page.

    `next_url` mirrors `links.next` — present on every page but the last,
    where it is absent.
    """

    faxes: tuple[Fax, ...] = ()
    next_url: str | None = None
    next_cursor: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def __iter__(self) -> Iterator[Fax]:
        return iter(self.faxes)

    def __len__(self) -> int:
        return len(self.faxes)

    def __getitem__(self, index: int) -> Fax:
        return self.faxes[index]


@dataclass(frozen=True)
class MediaLink:
    """A short-lived capability, plus the facts about what is behind it.

    Every call mints a fresh one and writes an audit entry naming who
    asked, so do not cache it past `expires_at` or pass it on: anyone
    holding this URL reads that document with no further authorization.
    """

    url: str
    expires_at: datetime | None = None
    byte_size: int | None = None
    sha256: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _from_json(cls, payload: Mapping[str, Any]) -> MediaLink:
        return cls(
            url=_text(payload, "url") or "",
            expires_at=_parse_datetime(payload.get("expires_at")),
            byte_size=_integer(payload, "byte_size"),
            sha256=_text(payload, "sha256"),
            raw=payload,
        )
