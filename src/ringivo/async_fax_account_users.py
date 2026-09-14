"""Who may read one fax account's faxes — awaited.

The SIBLING of fax_account_users.py, method for method. Each body here is
its twin's body with an `await` on the line that goes to the network;
nothing is shared between the two classes, because the only thing they
could share is the awaiting itself.

What IS shared is the module-private helpers fax_account_users.py already
owns — `_page` and the constants — plus faxes.py's `_path_segment` and
`_data_object` and fax_accounts.py's `_JSONAPI`. Those are pure values and
pure functions of their arguments, they touch no client, and one of them
(`_path_segment`) is a security control: a second copy of it is a second
thing to get wrong. So they are imported, not duplicated.

Read fax_account_users.py for the whys: what a grant is, why its write body
is a JSON:API document of nothing but relationships, and why this module
needs no sentinel.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .fax_account_users import (
    _FAX_ACCOUNT_TYPE,
    _NOUN,
    _TYPE,
    _USER_TYPE,
    _page,
)
from .fax_accounts import _JSONAPI
from .faxes import _data_object, _path_segment
from .models import FaxAccountUser, FaxAccountUserPage

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .async_client import AsyncRingivo

__all__ = ["AsyncFaxAccountUsers"]


class AsyncFaxAccountUsers:
    """The `client.fax_account_users` namespace on `AsyncRingivo`."""

    def __init__(self, client: AsyncRingivo) -> None:
        self._client = client

    async def list(
        self,
        *,
        fax_account: str | None = None,
        user: str | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> FaxAccountUserPage:
        """One page of grants, newest first. Needs `fax:read`.

        The awaited twin of `FaxAccountUsers.list`, and the same arguments
        mean the same things — including the snake_cased filter names,
        which are the API's own spelling and not a slip.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
            "filter[fax_account]": fax_account,
            "filter[user]": user,
        }
        response = await self._client.request("GET", "/v1/fax-account-users", params=params)
        return _page(response.json())

    async def get(self, fax_account_user_id: str) -> FaxAccountUser:
        """Read one grant. Needs `fax:read`."""
        response = await self._client.request(
            "GET",
            f"/v1/fax-account-users/{_path_segment(fax_account_user_id, noun=_NOUN)}",
        )
        return FaxAccountUser._from_resource(_data_object(response.json()))

    async def create(self, *, fax_account: str, user: str) -> FaxAccountUser:
        """Grant one user access to one fax account's content.

        The awaited twin of `FaxAccountUsers.create`: the same required
        pair, the same document of nothing but relationships, and the same
        rule that the account may be one the caller does not hold a grant
        on themselves. Needs `fax-accounts:write`.
        """
        document = {
            "data": {
                "type": _TYPE,
                "relationships": {
                    "faxAccount": {"data": {"type": _FAX_ACCOUNT_TYPE, "id": fax_account}},
                    "user": {"data": {"type": _USER_TYPE, "id": user}},
                },
            }
        }

        response = await self._client.request(
            "POST",
            "/v1/fax-account-users",
            accept=_JSONAPI,
            headers={"Content-Type": _JSONAPI},
            json=document,
        )
        return FaxAccountUser._from_resource(_data_object(response.json()))

    async def delete(self, fax_account_user_id: str) -> None:
        """Withdraw a grant. The access goes; nothing else does.

        The awaited twin of `FaxAccountUsers.delete`, and the only way to
        undo a grant — the resource has no update route. Needs
        `fax-accounts:write`.
        """
        await self._client.request(
            "DELETE",
            f"/v1/fax-account-users/{_path_segment(fax_account_user_id, noun=_NOUN)}",
        )
