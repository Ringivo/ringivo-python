"""What this client hands back: frozen, snake_cased, and ours.

Nothing generated ever crosses the public boundary. The `TypedDict`s in
`ringivo._generated_types` are rewritten wholesale from the spec, so a
caller who held one would be holding a shape whose fields, names and
nullability can change with a tool upgrade or a spec sync they never asked
for. These dataclasses change only when this package decides they do — and
they read the wire defensively rather than trusting those shapes, which is
why the readers below check every value's type instead of assuming it.

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

__all__ = [
    "Fax",
    "FaxAccount",
    "FaxAccountNumber",
    "FaxAccountPage",
    "FaxAccountUser",
    "FaxAccountUserPage",
    "FaxDocument",
    "FaxPage",
    "MediaLink",
    "WebhookDelivery",
    "WebhookDeliveryPage",
    "WebhookEndpoint",
    "WebhookEndpointPage",
]


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


def _strings(source: Mapping[str, Any], key: str) -> tuple[str, ...] | None:
    """A list of names as a tuple, or None when the member is not a list.

    AN EMPTY TUPLE AND None ARE NOT THE SAME READING, which is why this does
    not flatten one into the other. On a webhook endpoint's `events` the API
    publishes back exactly what was written — `null` and `[]` both mean
    "every event in scope", and it keeps them apart on purpose so a client
    that sent `[]` can see its write was understood. So `null`, a missing
    member and a value of the wrong type all read None here, while `[]`
    reads `()`.

    A non-string item is dropped rather than raising, for the reason every
    other reader in this module gives: the whole value is still in `raw`.
    """
    value = source.get(key)
    if not isinstance(value, list):
        return None
    return tuple(item for item in value if isinstance(item, str))


def _relationship_id(resource: Mapping[str, Any], name: str) -> str | None:
    """The id inside a to-one relationship's linkage, or None.

    THE LINKAGE IS OPTIONAL IN THE DOCUMENT, so None here does not mean the
    resource has no such relation. JSON:API lets a server answer a
    relationship with `links` alone and no `data` member at all, and this
    API's own schema marks the member `NotRequired`. So a None reads
    "the server did not send the linkage on this response", never "there is
    no customer" — and `raw` still carries whatever did arrive.
    """
    relationships = _mapping(resource, "relationships")
    relation = _mapping(relationships, name) if relationships else None
    data = _mapping(relation, "data") if relation else None
    return _text(data, "id") if data else None


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


@dataclass(frozen=True)
class FaxAccount:
    """One fax account: a customer's container for numbers, faxes and settings.

    `retention_days` and `retention_pages` are the two prune rules, and
    **None means the rule is OFF** — pages are kept for ever, or without a
    count limit. The API writes `null` for that, so None is the honest
    reading of it; it is also what you get if a server stops sending the
    member at all, and `raw` is where the two can be told apart.

    `customer_id` is the customer this account belongs to, when the server
    sends the relationship linkage. It is None when the server answers the
    relationship with links alone, which is legal and says nothing about the
    account (see `_relationship_id`).

    An account is never moved between customers: every fax it holds carries
    the customer it was sent or received for, so `update()` cannot change it
    and naming a different one is refused.
    """

    id: str
    name: str | None = None
    header_text: str | None = None
    default_from_e164: str | None = None
    retention_days: int | None = None
    retention_pages: int | None = None
    status: str | None = None
    customer_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _from_resource(cls, resource: Mapping[str, Any]) -> FaxAccount:
        """Build from a JSON:API resource object — every fax-account call."""
        attributes = _mapping(resource, "attributes") or {}

        return cls(
            id=_text(resource, "id") or "",
            name=_text(attributes, "name"),
            header_text=_text(attributes, "headerText"),
            default_from_e164=_text(attributes, "defaultFromE164"),
            retention_days=_integer(attributes, "retentionDays"),
            retention_pages=_integer(attributes, "retentionPages"),
            status=_text(attributes, "status"),
            customer_id=_relationship_id(resource, "customer"),
            created_at=_parse_datetime(attributes.get("createdAt")),
            updated_at=_parse_datetime(attributes.get("updatedAt")),
            raw=resource,
        )


@dataclass(frozen=True)
class FaxAccountPage:
    """One page of `fax_accounts.list()`, newest first.

    The same shape as `FaxPage`, and for the same reasons: `next_cursor` is
    the server's own cursor read out of `meta.page.nextCursor`, never one
    this client built, and it is None on the last page. `next_url` mirrors
    `links.next`, which is absent rather than null at the end.
    """

    accounts: tuple[FaxAccount, ...] = ()
    next_url: str | None = None
    next_cursor: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def __iter__(self) -> Iterator[FaxAccount]:
        return iter(self.accounts)

    def __len__(self) -> int:
        return len(self.accounts)

    def __getitem__(self, index: int) -> FaxAccount:
        return self.accounts[index]


@dataclass(frozen=True)
class FaxAccountNumber:
    """One number routed to a fax account.

    It is a `phone-numbers` resource — the routing API's own object, read
    here through the account it points at. This model carries the members a
    fax integration needs and leaves the rest in `raw`, which is where a
    number's messaging and voice blocks stay.

    Attaching a number is NOT this SDK's act and not this account's: a number
    points at one destination, and that rule belongs to the number
    (`POST /v1/phone-numbers/{id}/routing`, reachable through
    `client.request()`).
    """

    id: str
    e164: str | None = None
    status: str | None = None
    country: str | None = None
    activated_at: datetime | None = None
    created_at: datetime | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _from_resource(cls, resource: Mapping[str, Any]) -> FaxAccountNumber:
        attributes = _mapping(resource, "attributes") or {}

        return cls(
            id=_text(resource, "id") or "",
            e164=_text(attributes, "e164"),
            status=_text(attributes, "status"),
            country=_text(attributes, "country"),
            activated_at=_parse_datetime(attributes.get("activatedAt")),
            created_at=_parse_datetime(attributes.get("createdAt")),
            raw=resource,
        )


@dataclass(frozen=True)
class FaxAccountUser:
    """One grant: a person may read one fax account's content.

    A ROW HERE IS A PAIR AND A FACT, not a user and not an account. It says
    that this user may read this account's faxes and pages, and it exists or
    it does not — there is no route that changes one, so a grant is
    withdrawn by deleting it and re-made by creating another.

    It is the answer to "who can see this account's faxes?", which is why
    the API publishes `user_email` on the row: a page of ids answers nobody's
    question. The email is the grantee's at the time of the read, not a copy
    this grant owns.

    `fax_account_id` and `user_id` are the two halves of the pair, read out
    of the relationship linkages. Either is None when the server answered
    that relationship with links alone — legal in JSON:API, and a statement
    about the response rather than about the grant (see `_relationship_id`).
    `raw` still carries whatever did arrive.

    Reading a grant needs `fax:read`; making or withdrawing one needs
    `fax-accounts:write`. The split is the point: administering an account
    is permission-gated, while reading its content is grant-gated.
    """

    id: str
    fax_account_id: str | None = None
    user_id: str | None = None
    user_email: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _from_resource(cls, resource: Mapping[str, Any]) -> FaxAccountUser:
        """Build from a JSON:API resource object — every grant call."""
        attributes = _mapping(resource, "attributes") or {}

        return cls(
            id=_text(resource, "id") or "",
            fax_account_id=_relationship_id(resource, "faxAccount"),
            user_id=_relationship_id(resource, "user"),
            user_email=_text(attributes, "userEmail"),
            created_at=_parse_datetime(attributes.get("createdAt")),
            updated_at=_parse_datetime(attributes.get("updatedAt")),
            raw=resource,
        )


@dataclass(frozen=True)
class FaxAccountUserPage:
    """One page of `fax_account_users.list()`, newest first.

    The same shape as `FaxAccountPage`, and for the same reasons:
    `next_cursor` is the server's own cursor read out of
    `meta.page.nextCursor`, never one this client built, and it is None on
    the last page. `next_url` mirrors `links.next`, which is absent rather
    than null at the end.

    The rows are called `grants` because that is what they are: one row per
    (user, fax account) pair. An empty page is a real answer — nobody has
    been granted this account, and that is not the same as an account that
    does not exist, which is a 404.
    """

    grants: tuple[FaxAccountUser, ...] = ()
    next_url: str | None = None
    next_cursor: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def __iter__(self) -> Iterator[FaxAccountUser]:
        return iter(self.grants)

    def __len__(self) -> int:
        return len(self.grants)

    def __getitem__(self, index: int) -> FaxAccountUser:
        return self.grants[index]


@dataclass(frozen=True)
class WebhookEndpoint:
    """One registered endpoint: where the platform calls you, and about what.

    `scope_type` and `scope_id` say what this endpoint hears about — a
    tenant, a customer or one fax account — and they are fixed for its life.
    The three are matched as a containment order, so a reseller-wide
    endpoint and a per-account one both hear about the same fax.

    `events` is the list of event names asked for, and **None or an empty
    tuple both mean "every event in scope"**. The API publishes the list
    back exactly as it was written rather than normalising it, so the two
    are kept apart here too: None is the `null` it sent, `()` is the `[]`.

    `secret` IS ONLY EVER FILLED IN ONCE PER SECRET. It carries a value on
    the object `create()` returns and on the one `rotate_secret()` returns,
    and it is None on every other read — the platform keeps no readable
    copy, so a None here is an honest statement and not a gap. Store it when
    you first see it.

    `secret_previous_expires_at` is the deadline the PREVIOUS secret stops
    signing at, and it is None outside a rotation's 24-hour grace window.
    During that window a delivery's signature header carries two `v1`
    values, newest first, and `webhooks.verify()` accepts either.
    """

    id: str
    scope_type: str | None = None
    scope_id: str | None = None
    url: str | None = None
    events: tuple[str, ...] | None = None
    active: bool | None = None
    secret: str | None = None
    secret_previous_expires_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _from_resource(cls, resource: Mapping[str, Any]) -> WebhookEndpoint:
        """Build from a JSON:API resource object — every endpoint call."""
        attributes = _mapping(resource, "attributes") or {}

        return cls(
            id=_text(resource, "id") or "",
            scope_type=_text(attributes, "scopeType"),
            scope_id=_text(attributes, "scopeId"),
            url=_text(attributes, "url"),
            events=_strings(attributes, "events"),
            active=_boolean(attributes, "active"),
            secret=_text(attributes, "secret"),
            secret_previous_expires_at=_parse_datetime(attributes.get("secretPreviousExpiresAt")),
            created_at=_parse_datetime(attributes.get("createdAt")),
            updated_at=_parse_datetime(attributes.get("updatedAt")),
            raw=resource,
        )


@dataclass(frozen=True)
class WebhookEndpointPage:
    """One page of `webhook_endpoints.list()`, newest first.

    The same shape as `FaxAccountPage`, and for the same reasons:
    `next_cursor` is the server's own cursor read out of
    `meta.page.nextCursor`, never one this client built, and it is None on
    the last page. `next_url` mirrors `links.next`, which is absent rather
    than null at the end.

    No endpoint on this page carries a secret. Only the create and the
    rotate that minted one ever publish it.
    """

    endpoints: tuple[WebhookEndpoint, ...] = ()
    next_url: str | None = None
    next_cursor: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def __iter__(self) -> Iterator[WebhookEndpoint]:
        return iter(self.endpoints)

    def __len__(self) -> int:
        return len(self.endpoints)

    def __getitem__(self, index: int) -> WebhookEndpoint:
        return self.endpoints[index]


@dataclass(frozen=True)
class WebhookDelivery:
    """One delivery the platform still owes you, or gave up on.

    THIS IS EVIDENCE OF A FAILURE, NOT A HISTORY. A delivery that reaches
    your endpoint leaves no row at all: a row appears when an attempt
    fails, moves along the retry ladder, and is removed the moment a later
    attempt succeeds. So `status` is `pending` — still on the ladder — or
    `dead`, which is what an outage cost you. There is no `delivered`.

    `endpoint_id` is the endpoint this was for, when the server sends the
    relationship linkage; it is None when the server answers that
    relationship with links alone, which is legal and says nothing about
    the delivery (see `_relationship_id`).

    `payload_sha256` is the digest of the exact bytes that were signed. The
    body itself is never published here, so an integrator who kept what
    they received can prove it is what was sent, and nobody who only reads
    this collection learns the contents of somebody's fax.

    `attempt_no` counts the POSTs made, not the ones that failed.
    `status_code` is what your server answered and is None when it was
    never reached — `error` is why, in that case.

    The API also publishes a `deliveredAt` member. It is not read into this
    model: it is always `null`, kept only so a client generated against an
    older spec still parses, and treating it as a status would be wrong in
    both directions. It is still in `raw`.
    """

    id: str
    endpoint_id: str | None = None
    event_id: str | None = None
    event_type: str | None = None
    payload_sha256: str | None = None
    status: str | None = None
    attempt_no: int | None = None
    status_code: int | None = None
    duration_ms: int | None = None
    error: str | None = None
    next_attempt_at: datetime | None = None
    dead_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _from_resource(cls, resource: Mapping[str, Any]) -> WebhookDelivery:
        """Build from a JSON:API resource object — both delivery calls."""
        attributes = _mapping(resource, "attributes") or {}

        return cls(
            id=_text(resource, "id") or "",
            endpoint_id=_relationship_id(resource, "endpoint"),
            event_id=_text(attributes, "eventId"),
            event_type=_text(attributes, "eventType"),
            payload_sha256=_text(attributes, "payloadSha256"),
            status=_text(attributes, "status"),
            attempt_no=_integer(attributes, "attemptNo"),
            status_code=_integer(attributes, "statusCode"),
            duration_ms=_integer(attributes, "durationMs"),
            error=_text(attributes, "error"),
            next_attempt_at=_parse_datetime(attributes.get("nextAttemptAt")),
            dead_at=_parse_datetime(attributes.get("deadAt")),
            created_at=_parse_datetime(attributes.get("createdAt")),
            updated_at=_parse_datetime(attributes.get("updatedAt")),
            raw=resource,
        )


@dataclass(frozen=True)
class WebhookDeliveryPage:
    """One page of `webhook_deliveries.list()`, newest first.

    The same shape and the same cursor rules as `FaxAccountPage`. An empty
    page is the good news here: nothing is owed and nothing was given up
    on.
    """

    deliveries: tuple[WebhookDelivery, ...] = ()
    next_url: str | None = None
    next_cursor: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def __iter__(self) -> Iterator[WebhookDelivery]:
        return iter(self.deliveries)

    def __len__(self) -> int:
        return len(self.deliveries)

    def __getitem__(self, index: int) -> WebhookDelivery:
        return self.deliveries[index]
