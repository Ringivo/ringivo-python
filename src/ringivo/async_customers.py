"""Your customers: list them, read one, and set their app page — awaited.

The SIBLING of customers.py, method for method: each body here is its
twin's body with an `await` on the line that goes to the network. The page
reader, the noun and faxes.py's path escaper are imported rather than
copied, for the reason async_fax_accounts.py gives about its own imports —
they are pure functions of their arguments, they touch no client, and one
of them is a security control.

Read customers.py for the whys: why only an account-wide credential can
call this, and what the list's `ids` and `code` each ask for.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from .app_pages import _app_page, _app_page_body
from .customers import _NOUN, _id_filter, _page
from .faxes import _data_object, _path_segment
from .models import AppPage, Customer, CustomerPage

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .async_client import AsyncRingivo

__all__ = ["AsyncCustomers"]


class AsyncCustomers:
    """The `client.customers` namespace on `AsyncRingivo`."""

    def __init__(self, client: AsyncRingivo) -> None:
        self._client = client

    async def list(
        self,
        *,
        ids: Sequence[str] | None = None,
        code: str | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> CustomerPage:
        """One page of your customers, newest first.

        The awaited twin of `Customers.list`, and the same arguments mean
        the same things: `ids` reads several customers by id in one
        request and combines with `code`, `code` is an exact match, and
        `after` and `before` are mutually exclusive.

        Raises:
            ValueError: `ids` was one string rather than a list of ids,
                refused by the same `_id_filter` the sync twin calls.

        Needs `customers:read`.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
            # One `filter[id][]=<id>` pair per id, and an empty sequence
            # asks for nothing. `_id_filter` is imported rather than
            # copied, so the bare-string refusal and the reason behind the
            # bracketed key both keep a single home in customers.py.
            "filter[id][]": _id_filter(ids),
            "filter[code]": code,
        }
        response = await self._client.request("GET", "/v1/customers", params=params)
        return _page(response.json())

    async def get(self, customer_id: str) -> Customer:
        """Read one customer.

        The awaited twin of `Customers.get`. A customer that is not on your
        account answers 404, not 403.

        Needs `customers:read`.
        """
        response = await self._client.request(
            "GET",
            f"/v1/customers/{_path_segment(customer_id, noun=_NOUN)}",
        )
        return Customer._from_resource(_data_object(response.json()))

    async def set_app_page(
        self,
        customer_id: str,
        *,
        url: str,
        label: str,
        icon: str | None = None,
    ) -> AppPage:
        """Set or replace the customer's app page.

        The awaited twin of `Customers.set_app_page`: the same flat JSON
        body, `icon` left off when None, and safe to send again after a 502
        or a 409 titled `Change in progress`.

        Needs `pbx-app-pages:write`, on a credential for your whole account.
        """
        response = await self._client.request(
            "POST",
            f"/v1/customers/{_path_segment(customer_id, noun=_NOUN)}/app-page",
            json=_app_page_body(url=url, label=label, icon=icon),
        )
        return _app_page(response.json())

    async def get_app_page(self, customer_id: str) -> AppPage:
        """Read the customer's app page.

        The awaited twin of `Customers.get_app_page`. `page` is None when
        the customer has no page of its own.

        Needs `pbx-app-pages:read`.
        """
        response = await self._client.request(
            "GET",
            f"/v1/customers/{_path_segment(customer_id, noun=_NOUN)}/app-page",
        )
        return _app_page(response.json())

    async def clear_app_page(self, customer_id: str) -> None:
        """Remove the customer's app page.

        The awaited twin of `Customers.clear_app_page`: 204 also when there
        was no page.

        Needs `pbx-app-pages:write`.
        """
        await self._client.request(
            "DELETE",
            f"/v1/customers/{_path_segment(customer_id, noun=_NOUN)}/app-page",
        )
