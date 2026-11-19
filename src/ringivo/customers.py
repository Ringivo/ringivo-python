"""Your customers: list them, read one, and set the page in their phone apps.

-- THE CUSTOMER ITSELF IS READ ONLY HERE ---------------------------------------
This namespace lists customers and reads one. It has no `create()`, no
`update()` and no `delete()` of a customer. Its one write is the customer's
app page: `set_app_page()`, `get_app_page()` and `clear_app_page()` — the
web page the customer's phone apps show in their menu. app_pages.py says
what a page is and how a set behaves.

-- AN ACCOUNT-WIDE CREDENTIAL ONLY ----------------------------------------------
`list()` and `get()` need `customers:read`, and only a credential issued for
your whole reseller account can hold it. A credential issued for ONE
customer never does: the platform drops that scope from a customer
credential when the token is minted, so those two calls are refused for
such a client. The app page calls need `pbx-app-pages:read` or
`pbx-app-pages:write` instead; the write scope, too, is for an account-wide
credential only.

-- THE id IS WHAT THE REST OF THE API ASKS FOR ----------------------------------
A customer's `id` is the value `customer=` takes on `pbx.subscribers.list()`,
`pbx.devices.list()` and `pbx.call_records.list()`, and on the fax-account
calls. Reading it here is how an integration that knows a customer by name
or by code finds the id those calls need.

-- TWO FILTERS, AND NO sort -----------------------------------------------------
`list()` takes `ids` and `code`, and the cursor paging every other list here
takes. `ids` reads several customers by id in one request — the ids `list()`
and `get()` themselves hand back — and it combines with `code`. Use `get()`
when you want one customer and already hold its id.

The list is newest first. Like every other list in this package, it takes
no sort argument.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from .app_pages import _app_page, _app_page_body
from .faxes import _data_object, _next_cursor, _next_link, _path_segment
from .models import AppPage, Customer, CustomerPage

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .client import Ringivo

__all__ = ["Customers"]

#: What `_path_segment` calls this resource in its refusal.
_NOUN = "customer"

#: The refusal one bare string of ids earns, in the shape client.py and
#: webhook_endpoints.py refuse their own `Sequence[str]` arguments with.
_BARE_STRING_IDS = (
    "ids must be a list of customer ids, not one string: a str is read "
    'one character at a time, so ids="0198c4a1-7a10-7c3e-9d21-4f5a6b7c8d9e" '
    "asks for the thirty-six one-character ids that id is spelled with and "
    'the platform matches none of them. Pass ids=["0198c4a1-7a10-7c3e-9d21-4f5a6b7c8d9e"].'
)


class Customers:
    """The `client.customers` namespace."""

    def __init__(self, client: Ringivo) -> None:
        self._client = client

    def list(
        self,
        *,
        ids: Sequence[str] | None = None,
        code: str | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> CustomerPage:
        """One page of your customers, newest first.

        Args:
            ids: Several customers by id in one request, as a LIST —
                the ids `list()` and `get()` hand back. It combines with
                `code`. An empty sequence asks for nothing and is left
                off, exactly as `None` is.
            code: Only the customer whose `code` is exactly this value —
                the five-character code the platform assigns, which never
                changes.
            after: Walk forward: the previous page's
                `CustomerPage.next_cursor`. Mutually exclusive with
                `before` — passing both is refused with a 400.
            before: Walk backward from a cursor.
            page_size: Rows per page. The default is 25 and the ceiling is
                100.

        Raises:
            ValueError: `ids` was one string rather than a list of ids. A
                str is a `Sequence[str]`, so it would be read one character
                at a time — the refusal `_id_filter` explains.

        Needs `customers:read`.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
            # ONE `filter[id][]=<id>` PAIR PER ID, which is the only
            # shape the platform reads as a list: a comma-joined value
            # arrives as one id nothing matches, and the bracketless
            # `filter[id]=a&filter[id]=b` is kept by PHP as the single
            # string "b", which the filter then refuses. httpx writes the
            # repeated key for a tuple and nothing at all for None —
            # `_id_filter` is what makes sure it gets one or the other.
            "filter[id][]": _id_filter(ids),
            "filter[code]": code,
        }
        document = self._client.request("GET", "/v1/customers", params=params).json()
        return _page(document)

    def get(self, customer_id: str) -> Customer:
        """Read one customer.

        A customer that is not on your account answers 404, not 403 — the
        same answer an id that names nothing gives.

        Needs `customers:read`.
        """
        response = self._client.request(
            "GET",
            f"/v1/customers/{_path_segment(customer_id, noun=_NOUN)}",
        )
        return Customer._from_resource(_data_object(response.json()))

    def set_app_page(
        self,
        customer_id: str,
        *,
        url: str,
        label: str,
        icon: str | None = None,
    ) -> AppPage:
        """Set or replace the customer's app page.

        This is the page of every user of the customer that has no page of
        its own. The same page goes to the iOS app, the Android app and the
        web phone. The apps load `url` as you set it and add nothing about
        the user, so your page signs its users in itself. Never put a
        secret in `url`: anyone can read it.

        Safe to send again: a set the phone system already holds changes
        nothing. Send the same call again after a 502 (the phone system
        failed part way; `errors[0].meta["changedSettings"]` counts what was
        already changed) or a 409 titled `Change in progress` (`is_retryable()`
        is False for that 409; the README's "Retrying from a queue" says how
        to match it).

        Args:
            customer_id: The customer, as `customers.list()` returns it.
            url: The page's address: `https://` and a host name, at most
                2,000 characters. No IP address as the host, no user name
                or password, and no `[` or `]` (also not percent-encoded):
                each is a 422 on `/url`, and its `detail` says why.
            label: The text of the menu entry, 1 to 64 characters.
            icon: A Material icon name (lower-case letters, digits and
                `_`). Left off the request when None, and the API then
                uses `open_in_new`.

        Returns the `AppPage` as written. It is an echo of the set, not a
        read: `complete` is always True there, and `effective` is the page
        you sent. A page your provider set for many customers (`source`
        `default`) outranks it, and only `get_app_page()` shows that. To see
        the change applied, read the page a few seconds later and compare
        `page` with what you sent.

        Raises:
            ApiError: 422 for a refused member (its `source["pointer"]` names
                it; nothing is written), 409 for a customer with no phone
                system or a change in progress, 502 and 503 as above.

        Needs `pbx-app-pages:write`, on a credential for your whole account.
        """
        response = self._client.request(
            "POST",
            f"/v1/customers/{_path_segment(customer_id, noun=_NOUN)}/app-page",
            json=_app_page_body(url=url, label=label, icon=icon),
        )
        return _app_page(response.json())

    def get_app_page(self, customer_id: str) -> AppPage:
        """Read the customer's app page.

        `page` is None when the customer has no page of its own. A read
        shows a change a few seconds after a set or clear; `complete` is
        False while the three apps do not hold the same page yet.

        Needs `pbx-app-pages:read`.
        """
        response = self._client.request(
            "GET",
            f"/v1/customers/{_path_segment(customer_id, noun=_NOUN)}/app-page",
        )
        return _app_page(response.json())

    def clear_app_page(self, customer_id: str) -> None:
        """Remove the customer's app page.

        Its users then have no entry in the menu, except users with a page
        of their own. The API answers 204 also when there was no page, so
        this is safe to send again; send it again after a 502.

        Needs `pbx-app-pages:write`.
        """
        self._client.request(
            "DELETE",
            f"/v1/customers/{_path_segment(customer_id, noun=_NOUN)}/app-page",
        )


def _id_filter(ids: Sequence[str] | None) -> tuple[str, ...] | None:
    """The `filter[id][]` value: one id per pair, or the parameter left off.

    ONE BARE STRING IS REFUSED, for the reason client.py refuses
    `scopes="fax:read"` and webhook_endpoints.py refuses
    `events="fax.received"`: a str IS a `Sequence[str]`, so `ids="<an id>"`
    type-checks, and the tuple below reads it one character at a time. An id
    is thirty-six characters, so thirty-six one-character `filter[id][]`
    pairs reach the wire — measured with the guard removed, not assumed. The
    platform matches none of them and answers an empty page, which is a
    puzzle rather than a sentence, so the SHAPE is checked here instead.

    THE TUPLE IS BUILT BEFORE THE EMPTINESS CHECK, not `if not ids:` on the
    argument itself. A one-shot iterable — a generator, `map()`, a bare
    iterator — has no truthiness that means "empty", and handed to httpx
    unread it serialises as its own REPR: one pair reading `<generator
    object ...>`, measured the same way. Building the tuple first reads the
    argument exactly once and then checks what was actually read. This is
    the order `_events_for_create` already uses.

    An empty sequence returns None, so `_clean_params` drops the parameter
    before httpx ever sees it. That buys no new behaviour today and the
    claim is measured, not assumed: httpx writes nothing for an empty list
    or tuple either, so the wire is the same both ways. What it buys is
    ownership — "an empty list asks for nothing" becomes this package's
    guarantee rather than a dependency's handling of an empty value.

    Raises:
        ValueError: `ids` was one string rather than a list of ids.
    """
    if isinstance(ids, str):
        raise ValueError(_BARE_STRING_IDS)
    if ids is None:
        return None
    return tuple(ids) or None


def _page(document: Any) -> CustomerPage:
    """One `GET /v1/customers` body, as the page this package hands back."""
    if not isinstance(document, Mapping):
        document = {}

    data = document.get("data")
    customers = tuple(
        Customer._from_resource(item)
        for item in (data if isinstance(data, list) else [])
        if isinstance(item, Mapping)
    )
    return CustomerPage(
        customers=customers,
        next_url=_next_link(document),
        next_cursor=_next_cursor(document),
        raw=document,
    )
