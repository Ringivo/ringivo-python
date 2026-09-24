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
    "CallRecord",
    "CallRecordPage",
    "Customer",
    "CustomerPage",
    "Fax",
    "FaxAccount",
    "FaxAccountNumber",
    "FaxAccountPage",
    "FaxAccountUser",
    "FaxAccountUserPage",
    "FaxDocument",
    "FaxPage",
    "MediaLink",
    "PbxCall",
    "PbxDevice",
    "PbxDevicePage",
    "PbxSubscriber",
    "PbxSubscriberPage",
    "Recording",
    "Transcript",
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
    not flatten one into the other. On a webhook endpoint's `events`, a
    write must name at least one event type. `None` or `()` can still come
    back from a row the rule never reached, and the platform treats it as
    every event in scope. So `null`, a missing member and a value of the
    wrong type all read None here, while `[]` reads `()`.

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


def _relationship_ids(resource: Mapping[str, Any], name: str) -> tuple[str, ...] | None:
    """Every id inside a to-MANY relationship's linkage, or None.

    The to-many twin of `_relationship_id`, and it keeps the same
    distinction the singular one does: None means THE SERVER DID NOT SEND
    THE LINKAGE — a `links`-only relationship is legal JSON:API and this
    API's schema marks the member `NotRequired` — while `()` means it sent
    an empty list, which really is "none of them".

    Flattening the two would turn "we did not tell you" into "there are
    none", and on a user's `devices` those read very differently: one says
    nothing, the other says nobody has registered a phone.
    """
    relationships = _mapping(resource, "relationships")
    relation = _mapping(relationships, name) if relationships else None
    if relation is None:
        return None
    data = relation.get("data")
    if not isinstance(data, list):
        return None
    return tuple(
        identifier
        for item in data
        if isinstance(item, Mapping) and (identifier := _text(item, "id")) is not None
    )


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

    `events` is the list of event names asked for. **A write must name at
    least one** — `None` or an empty tuple can still come back here, from a
    row the rule never reached, and the platform treats either reading as
    "every event in scope". This client tells the two apart rather than
    flattening one into the other — None is the `null` the API sent, `()`
    is the `[]` — so `raw` still carries the exact shape a read returned.

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


@dataclass(frozen=True)
class PbxSubscriber:
    """One subscriber on a customer's phone system — a person or a machine.

    `user` is the extension and `domain` is the phone system it lives on;
    together they are what `id` is computed from, which is why the id is
    the same one wherever this subscriber is read.

    -- `kind` SAYS WHAT THIS ROW IS ---------------------------------------
    A phone system holds people AND machines: auto attendants, call
    queues, AI agents, the domain's settings template. `kind` is the
    platform's word for which one this is — `user` for a person, then
    `autoAttendant`, `callQueue`, `aiAgent`, `conference`, `department`,
    `site`, `ringGroup`, `trunk`, `timeOfDay`, `domain` and `system`.
    `system` is any machine the platform has no word for yet; an unknown
    marker is never read as `user`. It is a `str`, not an enum, and WIDE ON
    PURPOSE: a word added to the API later parses as itself rather than
    failing, so treat a word you do not know as `system`.

    For a click-to-call picker, list with `kind="user"` and
    `has_devices=True`: a subscriber with no device cannot place a call.

    EVERY FIELD HERE IS READ-ONLY. This surface does not write the phone
    system, so there is no `update()` and no argument that would try.

    -- THE THREE TIMESTAMPS ARE TEXT, AND THAT IS DELIBERATE --------------
    `created_at` and `updated_at` are `str`, not `datetime`, unlike every
    other model in this module. The API serves them exactly as the phone
    system stores them and says why: the switch has never published what
    format it writes, so a parse here would be a guess, and a WRONG guess
    is silent — an instant that is off by a time zone looks like an
    instant. A string a caller can read, log and compare is the honest
    answer, and the day the format is published this can become a
    `datetime` without anybody having been misled first.

    `customer_id` and `device_ids` come off the relationship linkages, so
    each is None when the server answered that relationship with links
    alone (see `_relationship_id` and `_relationship_ids`) — a statement
    about the response, never about the subscriber.
    """

    id: str
    user: str | None = None
    domain: str | None = None
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    scope: str | None = None
    group: str | None = None
    site: str | None = None
    presence: str | None = None
    caller_id_number: str | None = None
    caller_id_name: str | None = None
    time_zone: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    kind: str | None = None
    customer_id: str | None = None
    device_ids: tuple[str, ...] | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _from_resource(cls, resource: Mapping[str, Any]) -> PbxSubscriber:
        """Build from a JSON:API resource object — both PBX-subscriber reads."""
        attributes = _mapping(resource, "attributes") or {}

        return cls(
            id=_text(resource, "id") or "",
            user=_text(attributes, "user"),
            domain=_text(attributes, "domain"),
            display_name=_text(attributes, "displayName"),
            first_name=_text(attributes, "firstName"),
            last_name=_text(attributes, "lastName"),
            email=_text(attributes, "email"),
            scope=_text(attributes, "scope"),
            group=_text(attributes, "group"),
            site=_text(attributes, "site"),
            presence=_text(attributes, "presence"),
            caller_id_number=_text(attributes, "callerIdNumber"),
            caller_id_name=_text(attributes, "callerIdName"),
            time_zone=_text(attributes, "timeZone"),
            created_at=_text(attributes, "createdAt"),
            updated_at=_text(attributes, "updatedAt"),
            kind=_text(attributes, "kind"),
            customer_id=_relationship_id(resource, "customer"),
            device_ids=_relationship_ids(resource, "devices"),
            raw=resource,
        )


@dataclass(frozen=True)
class PbxSubscriberPage:
    """One page of `pbx.subscribers.list()`, by extension unless you sorted it.

    The same shape and the same cursor rules as `FaxAccountPage`:
    `next_cursor` is the server's own cursor read out of
    `meta.page.nextCursor`, never one this client built, and it is None on
    the last page. `next_url` mirrors `links.next`, which is absent rather
    than null at the end.
    """

    subscribers: tuple[PbxSubscriber, ...] = ()
    next_url: str | None = None
    next_cursor: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def __iter__(self) -> Iterator[PbxSubscriber]:
        return iter(self.subscribers)

    def __len__(self) -> int:
        return len(self.subscribers)

    def __getitem__(self, index: int) -> PbxSubscriber:
        return self.subscribers[index]


@dataclass(frozen=True)
class PbxDevice:
    """One REGISTRATION, not one handset.

    The row exists because something sent a SIP REGISTER, and it
    disappears when nothing does. So a phone that is unplugged does not
    become `registered=False` — it stops being here at all, and the rows
    that are here with `registered=False` are registrations that ran out
    before anything renewed them.

    `registered` is DERIVED by the API from `registration_expires_at`, and
    it is the field to read: the two timestamps beside it are the phone
    system's own text (see `PbxSubscriber` for why this module does not parse
    them), so comparing them yourself would mean guessing the format the
    API refused to guess.

    `user` is the subscriber's extension — a string off the registration,
    not the `subscribers` resource. `subscriber_id` is that resource's id,
    read off the `subscriber` relationship linkage.
    """

    id: str
    aor: str | None = None
    user: str | None = None
    domain: str | None = None
    mode: str | None = None
    user_agent: str | None = None
    contact: str | None = None
    transport: str | None = None
    received_from: str | None = None
    registered_at: str | None = None
    registration_expires_at: str | None = None
    registered: bool | None = None
    auto_answer: bool | None = None
    created_at: str | None = None
    customer_id: str | None = None
    subscriber_id: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _from_resource(cls, resource: Mapping[str, Any]) -> PbxDevice:
        """Build from a JSON:API resource object — both device calls."""
        attributes = _mapping(resource, "attributes") or {}

        return cls(
            id=_text(resource, "id") or "",
            aor=_text(attributes, "aor"),
            user=_text(attributes, "user"),
            domain=_text(attributes, "domain"),
            mode=_text(attributes, "mode"),
            user_agent=_text(attributes, "userAgent"),
            contact=_text(attributes, "contact"),
            transport=_text(attributes, "transport"),
            received_from=_text(attributes, "receivedFrom"),
            registered_at=_text(attributes, "registeredAt"),
            registration_expires_at=_text(attributes, "registrationExpiresAt"),
            registered=_boolean(attributes, "registered"),
            auto_answer=_boolean(attributes, "autoAnswer"),
            created_at=_text(attributes, "createdAt"),
            customer_id=_relationship_id(resource, "customer"),
            subscriber_id=_relationship_id(resource, "subscriber"),
            raw=resource,
        )


@dataclass(frozen=True)
class PbxDevicePage:
    """One page of `pbx.devices.list()`, by address of record.

    The same shape and the same cursor rules as `FaxAccountPage`.
    """

    devices: tuple[PbxDevice, ...] = ()
    next_url: str | None = None
    next_cursor: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def __iter__(self) -> Iterator[PbxDevice]:
        return iter(self.devices)

    def __len__(self) -> int:
        return len(self.devices)

    def __getitem__(self, index: int) -> PbxDevice:
        return self.devices[index]


@dataclass(frozen=True)
class CallRecord:
    """One call, as the phone system recorded it.

    THIS SHAPE HAS NO BACKWARD COMPATIBILITY WITH `ringivo` BEFORE 0.10.0,
    `type` IS RENAMED `direction` IN 0.11.0, AND ITS VALUE `onNet` IS RENAMED
    `internal` IN 0.12.0 (a call that stayed inside one domain). The console rebuilt
    `GET /v1/pbx/call-records` as one clean camelCase surface — the owner's
    ruling was that a correct shape matters more than a migration path — and
    then renamed the member that says which way the call went, because
    JSON:API reserves `type` for the resource object itself and a resource
    may not carry an attribute of that name. `vendor_type` is gone with
    nothing standing in for it, and `from_user`/`from_uri`/`to_user`/
    `to_uri`/`dialed`/`by_user`/`term_user`/`tag` are gone. Reach for the
    extended tier (below) for the raw material those used to carry.

    -- TWO TIERS -----------------------------------------------------------
    Everything from `direction` through `hidden` is the STANDARD set and is on
    every response. `vendor_id` onward through `raw_request_user` is the
    EXTENDED tier — the phone system's own raw values — and each of those
    fields is None unless you named it in `fields=` on `list()`. A sparse
    fieldset NARROWS rather than adds, so asking for one extended field
    without also naming the standard ones you want leaves the rest of this
    object at their defaults too; see `PbxCallRecords.list`.

    -- THE THREE INSTANTS ARE REAL DATETIMES --------------------------------
    Unlike `PbxSubscriber` and `PbxDevice`, whose timestamps stay strings,
    `started_at`, `answered_at` and `released_at` are parsed: the switch
    stores them as Unix epochs and the API publishes them as RFC 3339 in
    UTC, which is the one timestamp shape that carries no zone ambiguity.
    `answered_at` is None when nobody answered.

    -- direction AND disposition ARE ONE INTEGER, SPLIT IN TWO --------------
    The phone system records a single number carrying both which way the
    call went and whether anybody picked it up. `direction` is `inbound`,
    `outbound` or `internal`; `disposition` is `answered` or `missed`, and
    `inbound` is the only `direction` that can be either. A number this API
    has no word for is published as ITS OWN DIGITS in `direction` rather
    than as null, so a vocabulary that grows at the switch's end never
    erases a call from your reading of it. Match on the values you know and let the
    rest fall through; do not assume the set is closed.

    -- A `*_number` FIELD IS E.164 OR NOTHING -------------------------------
    `from_number`, `to_number` and `dialed_number` carry `+14075550101` or
    None — never an extension, a dial code or a star code. An extension is
    in `from_extension`, `routed_by_extension` or `answering_extension`
    instead; the raw value the switch wrote is in the extended tier
    (`raw_from_user`, `raw_to_user`, `raw_request_user`). So you can group,
    join and de-duplicate on the three `*_number` fields without checking
    their shape first.

    `duration_seconds` is the call end to end and `talk_seconds` is how
    much of it anybody was talking.

    `has_recording` says a recording is HELD; it is not itself the audio.
    Fetch the call's captures with `pbx.call_records.recordings(record.id)`
    — each `Recording` carries its own short-lived `content_url` to
    download from. A transcript, when one was requested, comes back the
    same way from `pbx.call_records.transcripts(record.id)`.

    `hidden` is the phone system's own flag, and it decides where a record
    can be found rather than whether it exists: hidden records are left out
    of `list()` unless you ask for them with `include_hidden=True`, and a
    direct `get()` serves one either way.

    `customer_id`, `from_subscriber_id` and `to_subscriber_id` come off the
    relationship linkages (`customer`, `fromSubscriber`, `toSubscriber`), so each
    is None when the server answered that relationship with links alone
    (see `_relationship_id`) — a statement about the response, never about
    the call. An outside caller has no subscriber to point at, so
    `from_subscriber_id` is None on every inbound call from off the phone
    system.
    """

    id: str
    direction: str | None = None
    disposition: str | None = None
    tenant_id: str | None = None
    domain: str | None = None
    territory: str | None = None
    from_number: str | None = None
    from_extension: str | None = None
    from_name: str | None = None
    to_number: str | None = None
    dialed_number: str | None = None
    routed_by_extension: str | None = None
    answering_extension: str | None = None
    started_at: datetime | None = None
    answered_at: datetime | None = None
    released_at: datetime | None = None
    duration_seconds: int | None = None
    talk_seconds: int | None = None
    release_code: str | None = None
    release_text: str | None = None
    has_recording: bool | None = None
    hidden: bool | None = None
    # -- EXTENDED: served only when named in fields= on list() ------------
    vendor_id: str | None = None
    orig_call_id: str | None = None
    term_call_id: str | None = None
    by_action: str | None = None
    terminated_to: str | None = None
    codec: str | None = None
    hostname: str | None = None
    raw_from_uri: str | None = None
    raw_from_user: str | None = None
    raw_to_user: str | None = None
    raw_request_user: str | None = None
    customer_id: str | None = None
    from_subscriber_id: str | None = None
    to_subscriber_id: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _from_resource(cls, resource: Mapping[str, Any]) -> CallRecord:
        """Build from a JSON:API resource object — both call-record calls."""
        attributes = _mapping(resource, "attributes") or {}

        return cls(
            id=_text(resource, "id") or "",
            direction=_text(attributes, "direction"),
            disposition=_text(attributes, "disposition"),
            tenant_id=_text(attributes, "tenantId"),
            domain=_text(attributes, "domain"),
            territory=_text(attributes, "territory"),
            from_number=_text(attributes, "fromNumber"),
            from_extension=_text(attributes, "fromExtension"),
            from_name=_text(attributes, "fromName"),
            to_number=_text(attributes, "toNumber"),
            dialed_number=_text(attributes, "dialedNumber"),
            routed_by_extension=_text(attributes, "routedByExtension"),
            answering_extension=_text(attributes, "answeringExtension"),
            started_at=_parse_datetime(attributes.get("startedAt")),
            answered_at=_parse_datetime(attributes.get("answeredAt")),
            released_at=_parse_datetime(attributes.get("releasedAt")),
            duration_seconds=_integer(attributes, "durationSeconds"),
            talk_seconds=_integer(attributes, "talkSeconds"),
            release_code=_text(attributes, "releaseCode"),
            release_text=_text(attributes, "releaseText"),
            has_recording=_boolean(attributes, "hasRecording"),
            hidden=_boolean(attributes, "hidden"),
            vendor_id=_text(attributes, "vendorId"),
            orig_call_id=_text(attributes, "origCallId"),
            term_call_id=_text(attributes, "termCallId"),
            by_action=_text(attributes, "byAction"),
            terminated_to=_text(attributes, "terminatedTo"),
            codec=_text(attributes, "codec"),
            hostname=_text(attributes, "hostname"),
            raw_from_uri=_text(attributes, "rawFromUri"),
            raw_from_user=_text(attributes, "rawFromUser"),
            raw_to_user=_text(attributes, "rawToUser"),
            raw_request_user=_text(attributes, "rawRequestUser"),
            customer_id=_relationship_id(resource, "customer"),
            from_subscriber_id=_relationship_id(resource, "fromSubscriber"),
            to_subscriber_id=_relationship_id(resource, "toSubscriber"),
            raw=resource,
        )


@dataclass(frozen=True)
class CallRecordPage:
    """One page of `pbx.call_records.list()`, newest first.

    The same shape and the same cursor rules as `FaxAccountPage`.

    NO RECORD ON THIS PAGE IS HIDDEN unless you asked for them: the list
    leaves hidden records out by default, the way the phone system's own
    call log does, and a direct `get()` serves one regardless.
    """

    call_records: tuple[CallRecord, ...] = ()
    next_url: str | None = None
    next_cursor: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def __iter__(self) -> Iterator[CallRecord]:
        return iter(self.call_records)

    def __len__(self) -> int:
        return len(self.call_records)

    def __getitem__(self, index: int) -> CallRecord:
        return self.call_records[index]


@dataclass(frozen=True)
class Recording:
    """One capture of a call, from `pbx.call_records.recordings()`.

    THERE IS NO PAGE HERE, on purpose: `recordings()` answers every capture
    of ONE call — bounded by that call's own two legs, never a growing
    table — so this package returns a plain `tuple[Recording, ...]` rather
    than a `...Page` with a cursor. The console's own schema calls this out
    the same way: `RecordingCollectionDocument` carries no `links` or
    `meta.page` member to walk.

    `id` is derived from the phone system's own `(call id, capture id)`
    pair, so it is stable across regions and a supersede reuses it rather
    than minting a new one.

    `content_url` is a signed, time-limited link to the audio, freshly
    minted on every call to `recordings()` — do not cache it past
    `expires_at` or hand it to anyone else; whoever holds the URL can fetch
    the audio with no further authorization. `duration` is null when the
    phone system never reported one for this capture, which is not the
    same as a missing recording — `byte_size` still describes real bytes.

    `superseded` is False on a first capture and becomes True once a
    longer capture of the same call replaced the audio behind this same
    `id` — the id does not change, but `byte_size` and `sha256` do.
    """

    id: str
    ccc_id: str | None = None
    duration: int | None = None
    byte_size: int | None = None
    sha256: str | None = None
    superseded: bool | None = None
    content_url: str | None = None
    expires_at: datetime | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _from_resource(cls, resource: Mapping[str, Any]) -> Recording:
        """Build from one `recordings` resource object.

        The attribute keys are KEBAB-CASE on the wire (`ccc-id`,
        `byte-size`, `content-url`, `expires-at`) — this endpoint's own
        spelling, unlike the camelCase `CallRecordAttributes` block.
        """
        attributes = _mapping(resource, "attributes") or {}

        return cls(
            id=_text(resource, "id") or "",
            ccc_id=_text(attributes, "ccc-id"),
            duration=_integer(attributes, "duration"),
            byte_size=_integer(attributes, "byte-size"),
            sha256=_text(attributes, "sha256"),
            superseded=_boolean(attributes, "superseded"),
            content_url=_text(attributes, "content-url"),
            expires_at=_parse_datetime(attributes.get("expires-at")),
            raw=resource,
        )


@dataclass(frozen=True)
class Transcript:
    """The transcript of one capture, from `pbx.call_records.transcripts()`.

    ONE ITEM PER RECORDING OF THE CALL, not one per transcript that
    exists: a capture with no words yet still appears here, with
    `status="pending"` and every other field None, so a caller can tell
    "no transcript yet" from "no recording at all". There is a third
    state, `failed`, but this collection never reports it — telling a
    permanent failure from a wait costs a lookup this list does not pay;
    that distinction belongs to the single-transcript endpoint, which this
    client does not yet wrap.

    NO PAGE HERE either, for the same reason `Recording` has none: this is
    the captures of one call, and the console's own
    `TranscriptCollectionDocument` carries no `links` or `meta.page` to
    walk.

    `id` is the RECORDING's id, not a separate transcript id — a
    transcript is keyed one-to-one by the capture it is of, so it is the
    same id `recordings()` published for the same capture.

    `content_url` is a signed, time-limited link to the stored transcript
    document (the speech-to-text provider's own response, not the audio) —
    same rule as `Recording.content_url`: do not cache it past
    `expires_at`. Every field but `id`, `ccc_id` and `status` is None while
    `status` is `"pending"`.
    """

    id: str
    ccc_id: str | None = None
    status: str | None = None
    language: str | None = None
    duration: int | None = None
    byte_size: int | None = None
    sha256: str | None = None
    provider: str | None = None
    model: str | None = None
    content_url: str | None = None
    expires_at: datetime | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _from_resource(cls, resource: Mapping[str, Any]) -> Transcript:
        """Build from one `transcripts` resource object.

        KEBAB-CASE attribute keys, the same as `Recording._from_resource`
        and for the same reason: this is that endpoint's own spelling.
        """
        attributes = _mapping(resource, "attributes") or {}

        return cls(
            id=_text(resource, "id") or "",
            ccc_id=_text(attributes, "ccc-id"),
            status=_text(attributes, "status"),
            language=_text(attributes, "language"),
            duration=_integer(attributes, "duration"),
            byte_size=_integer(attributes, "byte-size"),
            sha256=_text(attributes, "sha256"),
            provider=_text(attributes, "provider"),
            model=_text(attributes, "model"),
            content_url=_text(attributes, "content-url"),
            expires_at=_parse_datetime(attributes.get("expires-at")),
            raw=resource,
        )


@dataclass(frozen=True)
class PbxCall:
    """A call the platform was ASKED to place, answered before it rings.

    `pbx.subscribers.call()` returns one of these with a 202, which is the whole
    shape of the promise: the request was accepted and handed to the phone
    system, and `status` is `requested` — the only value this endpoint ever
    publishes. Nothing here says a phone rang, a person answered, or a call
    connected.

    `id` IS NOT A CALL-RECORD ID, BUT IT FINDS THE CALL'S RECORDS. The
    platform mints it before the call exists and hands it to the phone
    system as the SIP Call-ID the call is placed under, so it names the call
    ON THE PHONE SYSTEM. A call record's own id comes from the switch's CDR
    row, so the two ids differ: do not pass this one to
    `pbx.call_records.get()`. Pass it to
    `pbx.call_records.list(call_id=call.id)` instead. The call record
    appears there once the call has ended. One call writes two records —
    the leg that rang the subscriber and the leg that dialled out — and by
    default the list returns the visible dial-out record; the hidden ring
    leg comes back only with `include_hidden=True`.

    THE LIST'S DATE RANGE STILL APPLIES. The call id is matched only inside
    the months your range covers, and with no `started_after` or
    `started_before` that is the current and the previous month. To find an
    older call, pass a range that covers when it was placed. So an empty
    page means the call has not ended yet, it was placed outside the range,
    or the id names no call. It is never an error.

    THE ATTRIBUTES ARE WHAT WAS SENT TO THE SWITCH, not what you typed, and
    `caller_id` is where the two differ: this platform stores every caller
    id as E.164 **without** the plus, so a request for `+14074366118` comes
    back as `14074366118`. It is None when the request named none and the
    subscriber's own was used.

    `device` is the `devices` id the call originates from, and None when
    none was named. It is an attribute the answer echoes rather than a
    relationship, which is why it is spelled `device` and not `device_id`.

    There is no relationships block on this resource at all: a call request
    is answered before the call exists, so there is nothing yet to point
    at.
    """

    id: str
    destination: str | None = None
    caller_id: str | None = None
    auto_answer: bool | None = None
    device: str | None = None
    status: str | None = None
    requested_at: datetime | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _from_resource(cls, resource: Mapping[str, Any]) -> PbxCall:
        """Build from the JSON:API resource object the 202 carries.

        `requested_at` is a real instant, and the spec now says so rather
        than this package inferring it: `PbxCallAttributes.requestedAt` is
        `{type: string, format: date-time}`. It is the platform's own
        timestamp, minted here — which is why it is parsed while a user's
        and a device's are not (see `PbxSubscriber`).
        """
        attributes = _mapping(resource, "attributes") or {}

        return cls(
            id=_text(resource, "id") or "",
            destination=_text(attributes, "destination"),
            caller_id=_text(attributes, "callerId"),
            auto_answer=_boolean(attributes, "autoAnswer"),
            device=_text(attributes, "device"),
            status=_text(attributes, "status"),
            requested_at=_parse_datetime(attributes.get("requestedAt")),
            raw=resource,
        )


@dataclass(frozen=True)
class Customer:
    """One of your customers: a business you sell to.

    `id` is what the rest of this API asks for when it asks for a customer —
    `customer=` on `pbx.subscribers.list()`, `pbx.devices.list()` and
    `pbx.call_records.list()`, and on the fax-account calls.

    -- THE ADDRESS IS THE SERVICE ADDRESS ------------------------------------
    `address_lines`, `city`, `region`, `postal_code` and `country` are the
    service address as it was validated. `region` is the state or province,
    and `country` is ISO 3166-1 alpha-2. `address_lines` keeps the reading
    `_strings` gives every list in this module: `()` means the server sent
    an empty list, and None means it sent no list at all.

    -- WHERE THE DATA IS KEPT, AND WHICH REGION SERVES IT --------------------
    `data_residency_country` is the country this customer's data is kept in.
    It is set when the customer is created and never changes.
    `region_preference` is `partner_default`, `use1` or `usw1`, and
    `effective_region` is what that preference resolves to now. For
    `partner_default` that is your account's current default region, so it
    moves when your default moves.

    -- WITHOUT A PHONE SYSTEM, FIVE FIELDS ARE None --------------------------
    `pbx` says whether this customer has a phone system. When it is False,
    `residential`, `call_limit`, `call_limit_external`, `transports` and
    `provisioning_state` are None. `transports` keeps the server's order,
    because the order is data: it is the order the SIP transports are
    offered in DNS, first preferred.

    `region_preference`, `transports` and `provisioning_state` are passed
    through as text rather than checked against a copy of the vocabulary
    that would go stale here. Match on the values you know and let the rest
    fall through.

    `created_at` and `updated_at` are real datetimes: the platform writes
    them itself, in RFC 3339.

    There is no relationships block to read: the resource carries none.
    """

    id: str
    name: str | None = None
    code: str | None = None
    country: str | None = None
    address_lines: tuple[str, ...] | None = None
    city: str | None = None
    region: str | None = None
    postal_code: str | None = None
    time_zone: str | None = None
    data_residency_country: str | None = None
    region_preference: str | None = None
    effective_region: str | None = None
    pbx: bool | None = None
    residential: bool | None = None
    call_limit: int | None = None
    call_limit_external: int | None = None
    transports: tuple[str, ...] | None = None
    provisioning_state: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def _from_resource(cls, resource: Mapping[str, Any]) -> Customer:
        """Build from a JSON:API resource object — both customer calls."""
        attributes = _mapping(resource, "attributes") or {}

        return cls(
            id=_text(resource, "id") or "",
            name=_text(attributes, "name"),
            code=_text(attributes, "code"),
            country=_text(attributes, "country"),
            address_lines=_strings(attributes, "addressLines"),
            city=_text(attributes, "city"),
            region=_text(attributes, "region"),
            postal_code=_text(attributes, "postalCode"),
            time_zone=_text(attributes, "timeZone"),
            data_residency_country=_text(attributes, "dataResidencyCountry"),
            region_preference=_text(attributes, "regionPreference"),
            effective_region=_text(attributes, "effectiveRegion"),
            pbx=_boolean(attributes, "pbx"),
            residential=_boolean(attributes, "residential"),
            call_limit=_integer(attributes, "callLimit"),
            call_limit_external=_integer(attributes, "callLimitExternal"),
            transports=_strings(attributes, "transports"),
            provisioning_state=_text(attributes, "provisioningState"),
            created_at=_parse_datetime(attributes.get("createdAt")),
            updated_at=_parse_datetime(attributes.get("updatedAt")),
            raw=resource,
        )


@dataclass(frozen=True)
class CustomerPage:
    """One page of `customers.list()`, newest first.

    The same shape and the same cursor rules as `FaxAccountPage`.

    This collection also carries an exact count of every matching customer
    in `meta.page.total`. This page does not publish it as a field, as no
    other page in this package does; read it from
    `page.raw["meta"]["page"]["total"]`.
    """

    customers: tuple[Customer, ...] = ()
    next_url: str | None = None
    next_cursor: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    def __iter__(self) -> Iterator[Customer]:
        return iter(self.customers)

    def __len__(self) -> int:
        return len(self.customers)

    def __getitem__(self, index: int) -> Customer:
        return self.customers[index]
