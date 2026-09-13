"""Register a webhook endpoint, read one, list them, change one, remove one.

-- REGISTERING IS THE HALF THAT WAS MISSING -------------------------------------
webhooks.py verifies a delivery that has already arrived. Nothing said where
it should arrive, so every integrator had to register their endpoint by hand
in a console or through `client.request()`. This module is the other half of
that contract, and the two are written to be read together: `create()` hands
you the secret `webhooks.verify()` wants.

-- THE SECRET IS READABLE EXACTLY ONCE PER SECRET ------------------------------
`create()` and `rotate_secret()` are the only calls whose answer carries the
signing secret. Every other read publishes `"secret": null`, and that is an
honest statement rather than a gap: the platform keeps no readable copy, so
there is no call that could hand it back. Store it the moment you have it.

A rotation therefore does not replace the secret at once — it MINTS a new
one and starts a clock. The previous secret goes on signing for a 24-hour
grace window, `secret_previous_expires_at` is the deadline, and during the
window a delivery's header carries two `v1` signatures, newest first.
`webhooks.verify()` tries every one of them, so a rotation costs no
deliveries as long as your own copy is rolled before the deadline.

-- THE BODIES HERE ARE JSON:API DOCUMENTS --------------------------------------
Exactly as in fax_accounts.py: `{"data": {"type": "webhook-endpoints",
"attributes": {...}}}`, sent AND accepted as `application/vnd.api+json`,
with the content type set explicitly on each write because httpx stamps
`application/json` on a `json=` body and this surface answers 415 to that.

-- SPARSE WRITES, AND THE SENTINEL SHARED WITH FAX ACCOUNTS --------------------
`update()` sends only the members the caller named, so switching an endpoint
off leaves its event list alone. That needs the same three states per
argument fax_accounts.py sets out — send this value, send `null`, send
nothing — so this module IMPORTS that module's `NOT_GIVEN` rather than
inventing a second sentinel: a caller comparing with `isinstance` must get
the same answer whichever namespace they are in.

`events=None` is a VALUE here and not an omission. `None` and `[]` both mean
"every event in scope", and the API publishes the list back verbatim rather
than normalising it, so a client that sent `[]` can see its write was
understood.

-- A KNOWN DEFECT IN THE VENDORED SPEC ----------------------------------------
`spec/openapi.yaml` marks `url` as REQUIRED in `WebhookEndpointUpdateRequest`.
The server does not require it: a PATCH is merged over the stored attributes
before it is validated, exactly as it is for a fax account, so `update()`
here is sparse like `fax_accounts.update()`. A correction to the spec is in
flight; a reader who checks the document and finds this file disagreeing with
it is looking at that defect and not at a bug here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from .fax_accounts import NOT_GIVEN, _JSONAPI, NotGiven, _given
from .faxes import _data_object, _next_cursor, _next_link, _path_segment
from .models import WebhookEndpoint, WebhookEndpointPage

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .client import Ringivo

__all__ = ["WebhookEndpoints"]

#: The `type` member every webhook-endpoint document carries.
_TYPE = "webhook-endpoints"

#: What `_path_segment` calls this resource in its refusal.
_NOUN = "webhook endpoint"


class WebhookEndpoints:
    """The `client.webhook_endpoints` namespace."""

    def __init__(self, client: Ringivo) -> None:
        self._client = client

    def list(
        self,
        *,
        scope_type: str | None = None,
        scope_id: str | None = None,
        active: bool | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> WebhookEndpointPage:
        """One page of registered endpoints, newest first.

        No endpoint on the page carries a secret — see the module docstring.

        Args:
            scope_type: `tenant`, `customer` or `fax_account`.
            scope_id: The id of the tenant, customer or fax account an
                endpoint hears about.
            active: Only the endpoints that are switched on, or only the
                ones that are off. `False` is sent rather than dropped.
            after: Walk forward: the previous page's
                `WebhookEndpointPage.next_cursor`. Mutually exclusive with
                `before` — passing both is refused with a 400.
            before: Walk backward from a cursor.
            page_size: Rows per page. The default is 25 and the ceiling is
                100.

        Needs `webhooks:read`. A `fax:read` token lists only the
        FAX-ACCOUNT-SCOPED endpoints: customer- and tenant-scoped ones are
        absent from its page rather than refused, so an empty result under a
        `fax:*` token says nothing about whether a wider endpoint exists.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
            "filter[scope_type]": scope_type,
            "filter[scope_id]": scope_id,
            "filter[active]": active,
        }
        document = self._client.request("GET", "/v1/webhook-endpoints", params=params).json()
        return _page(document)

    def get(self, webhook_endpoint_id: str) -> WebhookEndpoint:
        """Read one endpoint. `secret` is always None here.

        An endpoint your token cannot reach answers 404, exactly as an id
        that names nothing anywhere does — so a `fax:*` token reading a
        customer- or tenant-scoped endpoint gets the same answer as for a
        typo, on purpose.

        Needs `webhooks:read`, or `fax:read` for a fax-account-scoped
        endpoint.
        """
        response = self._client.request(
            "GET",
            f"/v1/webhook-endpoints/{_path_segment(webhook_endpoint_id, noun=_NOUN)}",
        )
        return WebhookEndpoint._from_resource(_data_object(response.json()))

    def create(
        self,
        *,
        url: str,
        scope_type: str,
        scope_id: str,
        events: Sequence[str] | None | NotGiven = NOT_GIVEN,
        active: bool | NotGiven = NOT_GIVEN,
    ) -> WebhookEndpoint:
        """Register an endpoint, and read its signing secret for the only time.

        **The returned `WebhookEndpoint.secret` is the only copy you will
        ever be handed — store it now; there is no way to read it back.**
        Every later read of this endpoint answers `secret: null`, because
        the platform keeps no readable copy of it.

        Args:
            url: Where to POST. `https` only, on a public host: plain http,
                credentials in the URL, a private address literal and a
                non-http scheme are each refused at registration. A hostname
                that does not resolve yet IS accepted, so you can register
                before you publish DNS.
            scope_type: `tenant`, `customer` or `fax_account` — what this
                endpoint hears about.
            scope_id: The id of that tenant, customer or fax account.
                Neither this nor `scope_type` can be changed afterwards: the
                delivery record is the evidence of what THAT scope was told,
                so a different scope is a new endpoint.
            events: The event names you want, as a LIST. `None` or `[]`
                both mean EVERY event in scope, and the list is published
                back verbatim rather than normalised. Leave it out and the
                platform decides what a new endpoint hears. An event name
                this platform does not publish is a 422 — a typo would
                otherwise subscribe you to silence.
            active: `False` registers an endpoint that is switched off.

        Raises:
            ValueError: `events` was one string rather than a list of names.
                A str is a `Sequence[str]`, so it would be read one
                character at a time.

        Needs `webhooks:write`, or `fax:write` for a `fax_account`-scoped
        endpoint only: naming a `customer` or `tenant` scope with a `fax:*`
        token is refused with a 422.

        A scope you may not use and a scope that does not exist are refused
        with the SAME message, on purpose — telling them apart would make
        this field a way to discover which ids are real.
        """
        attributes: dict[str, Any] = {"url": url, "scopeType": scope_type, "scopeId": scope_id}
        attributes.update(_given({"events": _events(events), "active": active}))

        document = {"data": {"type": _TYPE, "attributes": attributes}}

        response = self._client.request(
            "POST",
            "/v1/webhook-endpoints",
            accept=_JSONAPI,
            headers={"Content-Type": _JSONAPI},
            json=document,
        )
        return WebhookEndpoint._from_resource(_data_object(response.json()))

    def update(
        self,
        webhook_endpoint_id: str,
        *,
        url: str | NotGiven = NOT_GIVEN,
        events: Sequence[str] | None | NotGiven = NOT_GIVEN,
        active: bool | NotGiven = NOT_GIVEN,
    ) -> WebhookEndpoint:
        """Change an endpoint's URL, its event list, or its switch.

        A SPARSE PATCH: only the arguments you pass are sent, so switching
        an endpoint off leaves its event list exactly as it was, and adding
        an event is `update(id, events=[...])` with nothing else named.
        `events=None` is a VALUE — every event in scope — rather than an
        omission.

        `scope_type` and `scope_id` cannot change and there is no argument
        here that would try: a different scope is a new endpoint.

        The returned endpoint carries `secret: None`. A PATCH does not mint
        a secret; `rotate_secret()` is the call that does.

        Raises:
            ValueError: No member was named. An empty PATCH spends a round
                trip and an audit entry to change nothing, and it is far
                more often a form that came back empty than an intention.
            ValueError: `events` was one string rather than a list of names.

        Needs `webhooks:write`, or `fax:write` for a fax-account-scoped
        endpoint.
        """
        attributes = _given({"url": url, "events": _events(events), "active": active})
        if not attributes:
            raise ValueError(
                "update() needs at least one member to change: url=, events= or active=. "
                "Pass events=None or events=[] to hear about every event in scope — that "
                "counts as a change."
            )

        document = {"data": {"type": _TYPE, "id": webhook_endpoint_id, "attributes": attributes}}

        response = self._client.request(
            "PATCH",
            f"/v1/webhook-endpoints/{_path_segment(webhook_endpoint_id, noun=_NOUN)}",
            accept=_JSONAPI,
            headers={"Content-Type": _JSONAPI},
            json=document,
        )
        return WebhookEndpoint._from_resource(_data_object(response.json()))

    def delete(self, webhook_endpoint_id: str) -> None:
        """Remove an endpoint. The fan-out stops at once.

        THE DELIVERY RECORD SURVIVES. "Why did our integration stop hearing
        about faxes?" is answered by the deliveries of the endpoint somebody
        removed, so `webhook_deliveries.list()` still reaches them.

        Returns None: the API answers 204 with no body.

        Needs `webhooks:write`, or `fax:write` for a fax-account-scoped
        endpoint.
        """
        self._client.request(
            "DELETE",
            f"/v1/webhook-endpoints/{_path_segment(webhook_endpoint_id, noun=_NOUN)}",
        )

    def rotate_secret(self, webhook_endpoint_id: str) -> WebhookEndpoint:
        """Mint a new signing secret, and start the grace window.

        A verb rather than a PATCH, because it MINTS A CREDENTIAL and starts
        a clock. The returned `WebhookEndpoint.secret` is the new secret and
        the only copy you will be handed — store it now.

        The PREVIOUS secret goes on signing for a 24-hour grace window and
        `secret_previous_expires_at` is its deadline. During the window a
        delivery's signature header carries two `v1` values, newest first,
        and `webhooks.verify()` accepts either — so roll your own copy
        before the deadline and the rotation costs you no deliveries.

        Sends no body.

        Needs `webhooks:write`, or `fax:write` for a fax-account-scoped
        endpoint.
        """
        response = self._client.request(
            "POST",
            f"/v1/webhook-endpoints/{_path_segment(webhook_endpoint_id, noun=_NOUN)}/rotate-secret",
            accept=_JSONAPI,
        )
        return WebhookEndpoint._from_resource(_data_object(response.json()))


def _page(document: Any) -> WebhookEndpointPage:
    """One `GET /v1/webhook-endpoints` body, as the page this package hands back."""
    if not isinstance(document, Mapping):
        document = {}

    data = document.get("data")
    endpoints = tuple(
        WebhookEndpoint._from_resource(item)
        for item in (data if isinstance(data, list) else [])
        if isinstance(item, Mapping)
    )
    return WebhookEndpointPage(
        endpoints=endpoints,
        next_url=_next_link(document),
        next_cursor=_next_cursor(document),
        raw=document,
    )


def _events(events: Sequence[str] | None | NotGiven) -> list[str] | None | NotGiven:
    """The `events` member as the wire wants it, with all three states kept.

    `NOT_GIVEN` and `None` pass through untouched, because `_given` must
    still be able to tell "said nothing" from "said every event in scope".
    Anything else becomes a `list`, so the member is a JSON array whatever
    sequence the caller reached for — a tuple would serialise the same way,
    but a caller who passed one should not have to know that.

    ONE BARE STRING IS REFUSED, for the reason client.py refuses
    `scopes="fax:read"`: a str IS a `Sequence[str]`, to the type checker and
    to `list()`, so `events="fax.received"` type-checks and then asks to be
    subscribed to twelve one-character event names — measured, with the
    guard removed: `['f', 'a', 'x', '.', 'r', 'e', 'c', 'e', 'i', 'v', 'e',
    'd']` reached the wire. The platform answers 422 naming events the
    caller never typed, which is a puzzle rather than a sentence, so the
    SHAPE is checked here, in the one place that builds this member, and
    `create()` and `update()` on both classes inherit it.

    Raises:
        ValueError: `events` was one string rather than a list of names.
    """
    if isinstance(events, str):
        raise ValueError(
            "events must be a list of event names, not one string: a str is read "
            'one character at a time, so events="fax.received" asks for twelve '
            "events that do not exist and the platform refuses every one of them. "
            'Pass events=["fax.received"].'
        )
    if isinstance(events, NotGiven) or events is None:
        return events
    return list(events)
