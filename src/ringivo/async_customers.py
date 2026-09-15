"""Your customers: list them, and read one — awaited.

The SIBLING of customers.py, method for method: each body here is its
twin's body with an `await` on the line that goes to the network. The page
reader, the noun and faxes.py's path escaper are imported rather than
copied, for the reason async_fax_accounts.py gives about its own imports —
they are pure functions of their arguments, they touch no client, and one
of them is a security control.

Read customers.py for the whys: why only an account-wide credential can
call this, and why the list takes `code` but no filter by id.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .customers import _NOUN, _page
from .faxes import _data_object, _path_segment
from .models import Customer, CustomerPage

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
        code: str | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> CustomerPage:
        """One page of your customers, newest first.

        The awaited twin of `Customers.list`, and the same arguments mean
        the same things: `code` is an exact match, and `after` and
        `before` are mutually exclusive.

        Needs `customers:read`.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
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
