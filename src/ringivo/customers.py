"""Your customers: list them, and read one.

-- READS ONLY -------------------------------------------------------------------
This namespace lists customers and reads one. It has no `create()`, no
`update()` and no `delete()`, because the API publishes none of them here.

-- AN ACCOUNT-WIDE CREDENTIAL ONLY ----------------------------------------------
Both calls need `customers:read`, and only a credential issued for your whole
reseller account can hold it. A credential issued for ONE customer never
does: the platform drops that scope from a customer credential when the
token is minted, so every call here is refused for such a client.

-- THE id IS WHAT THE REST OF THE API ASKS FOR ----------------------------------
A customer's `id` is the value `customer=` takes on `pbx.users.list()`,
`pbx.devices.list()` and `pbx.call_records.list()`, and on the fax-account
calls. Reading it here is how an integration that knows a customer by name
or by code finds the id those calls need.

-- ONE FILTER, AND NO sort ------------------------------------------------------
`list()` takes `code`, and the cursor paging every other list here takes. The
API also documents a filter by id, and this release leaves it out on
purpose: the spec declares it as a plain array, which goes on the wire as
repeated `filter[id]=` pairs, while the platform reads the filter as a list
only in the bracket form `filter[id][]=`. PHP keeps only the last of the
repeated pairs, as one string, and the platform's filter does not read a
string as a list. Adding the filter later changes no existing call. Use
`get()` for one customer by id.

The list is newest first. Like every other list in this package, it takes
no sort argument.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from .faxes import _data_object, _next_cursor, _next_link, _path_segment
from .models import Customer, CustomerPage

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .client import Ringivo

__all__ = ["Customers"]

#: What `_path_segment` calls this resource in its refusal.
_NOUN = "customer"


class Customers:
    """The `client.customers` namespace."""

    def __init__(self, client: Ringivo) -> None:
        self._client = client

    def list(
        self,
        *,
        code: str | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> CustomerPage:
        """One page of your customers, newest first.

        Args:
            code: Only the customer whose `code` is exactly this value —
                the five-character code the platform assigns, which never
                changes.
            after: Walk forward: the previous page's
                `CustomerPage.next_cursor`. Mutually exclusive with
                `before` — passing both is refused with a 400.
            before: Walk backward from a cursor.
            page_size: Rows per page. The default is 25 and the ceiling is
                100.

        Needs `customers:read`.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
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
