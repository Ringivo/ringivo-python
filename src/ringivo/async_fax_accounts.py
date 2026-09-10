"""Open a fax account, read one, list them, change one, delete one — awaited.

The SIBLING of fax_accounts.py, method for method. Each body here is its
twin's body with an `await` on the line that goes to the network; nothing
is shared between the two classes, because the only thing they could share
is the awaiting itself.

What IS shared is the module-private helpers fax_accounts.py already owns —
the sentinel, `_given`, `_page`, `_numbers` and the constants — plus
faxes.py's `_path_segment` and `_data_object`. Those are pure functions of
their arguments, they touch no client, and one of them (`_path_segment`) is
a security control: a second copy of it is a second thing to get wrong. So
they are imported, not duplicated.

Read fax_accounts.py for the whys: why the write bodies are JSON:API
documents with an explicit content type, and why "not given" needs a value
of its own.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from .errors import RingivoError
from .fax_accounts import (
    NOT_GIVEN,
    _JSONAPI,
    _MAX_PAGE_SIZE,
    _NOUN,
    _TYPE,
    NotGiven,
    _given,
    _numbers,
    _page,
)
from .faxes import _data_object, _next_cursor, _path_segment
from .models import FaxAccount, FaxAccountNumber, FaxAccountPage

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .async_client import AsyncRingivo

__all__ = ["AsyncFaxAccounts"]


class AsyncFaxAccounts:
    """The `client.fax_accounts` namespace on `AsyncRingivo`."""

    def __init__(self, client: AsyncRingivo) -> None:
        self._client = client

    async def list(
        self,
        *,
        customer: str | None = None,
        status: str | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> FaxAccountPage:
        """One page of fax accounts, newest first. Needs `fax:read`.

        The awaited twin of `FaxAccounts.list`, and the same arguments mean
        the same things.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
            "filter[customer]": customer,
            "filter[status]": status,
        }
        response = await self._client.request("GET", "/v1/fax-accounts", params=params)
        return _page(response.json())

    async def get(self, fax_account_id: str) -> FaxAccount:
        """Read one fax account. Needs `fax:read`."""
        response = await self._client.request(
            "GET",
            f"/v1/fax-accounts/{_path_segment(fax_account_id, noun=_NOUN)}",
        )
        return FaxAccount._from_resource(_data_object(response.json()))

    async def numbers(self, fax_account_id: str) -> tuple[FaxAccountNumber, ...]:
        """EVERY number routed to this account, not one page. Needs `fax:read`.

        The walk, the ceiling page size and the repeated-cursor refusal are
        `FaxAccounts.numbers`'s, for the reasons written there.
        """
        path = f"/v1/fax-accounts/{_path_segment(fax_account_id, noun=_NOUN)}/numbers"
        found: list[FaxAccountNumber] = []
        cursor: str | None = None
        seen: set[str] = set()

        while True:
            response = await self._client.request(
                "GET",
                path,
                params={"page[size]": _MAX_PAGE_SIZE, "page[after]": cursor},
            )
            document = response.json()
            found.extend(_numbers(document))

            cursor = _next_cursor(document if isinstance(document, Mapping) else {})
            if cursor is None:
                return tuple(found)
            if cursor in seen:
                raise RingivoError(
                    f"the API served the cursor {cursor!r} twice while listing the numbers on "
                    f"fax account {fax_account_id}: walking it again would never end. "
                    f"{len(found)} numbers were read before this."
                )
            seen.add(cursor)

    async def create(
        self,
        *,
        customer: str,
        name: str,
        header_text: str | None | NotGiven = NOT_GIVEN,
        default_from_e164: str | None | NotGiven = NOT_GIVEN,
        retention_days: int | None | NotGiven = NOT_GIVEN,
        retention_pages: int | None | NotGiven = NOT_GIVEN,
    ) -> FaxAccount:
        """Open a fax account for one of your customers.

        The awaited twin of `FaxAccounts.create`: same arguments, same
        meanings, same rule that an argument nobody named is ABSENT from the
        document so the platform's own default applies. Needs
        `fax-accounts:write`.
        """
        attributes: dict[str, Any] = {"name": name}
        attributes.update(
            _given(
                {
                    "headerText": header_text,
                    "defaultFromE164": default_from_e164,
                    "retentionDays": retention_days,
                    "retentionPages": retention_pages,
                }
            )
        )

        document = {
            "data": {
                "type": _TYPE,
                "attributes": attributes,
                "relationships": {
                    "customer": {"data": {"type": "customers", "id": customer}},
                },
            }
        }

        response = await self._client.request(
            "POST",
            "/v1/fax-accounts",
            accept=_JSONAPI,
            headers={"Content-Type": _JSONAPI},
            json=document,
        )
        return FaxAccount._from_resource(_data_object(response.json()))

    async def update(
        self,
        fax_account_id: str,
        *,
        name: str | NotGiven = NOT_GIVEN,
        header_text: str | None | NotGiven = NOT_GIVEN,
        default_from_e164: str | None | NotGiven = NOT_GIVEN,
        retention_days: int | None | NotGiven = NOT_GIVEN,
        retention_pages: int | None | NotGiven = NOT_GIVEN,
        status: str | NotGiven = NOT_GIVEN,
    ) -> FaxAccount:
        """Change a fax account's settings, or suspend it.

        A SPARSE PATCH, exactly as `FaxAccounts.update` describes: only the
        arguments you pass are sent, and `None` clears a nullable field
        rather than meaning "no opinion". Needs `fax-accounts:write`.

        Raises:
            ValueError: No field was named.
        """
        attributes = _given(
            {
                "name": name,
                "headerText": header_text,
                "defaultFromE164": default_from_e164,
                "retentionDays": retention_days,
                "retentionPages": retention_pages,
                "status": status,
            }
        )
        if not attributes:
            raise ValueError(
                "update() needs at least one field to change: name=, header_text=, "
                "default_from_e164=, retention_days=, retention_pages= or status=. "
                "Pass None to clear a nullable field — that counts as a change."
            )

        document = {"data": {"type": _TYPE, "id": fax_account_id, "attributes": attributes}}

        response = await self._client.request(
            "PATCH",
            f"/v1/fax-accounts/{_path_segment(fax_account_id, noun=_NOUN)}",
            accept=_JSONAPI,
            headers={"Content-Type": _JSONAPI},
            json=document,
        )
        return FaxAccount._from_resource(_data_object(response.json()))

    async def delete(self, fax_account_id: str) -> None:
        """Delete a fax account. The pages go; the records stay.

        The awaited twin of `FaxAccounts.delete`, including the refusal: a
        number still routed to the account makes this an `ApiError` with
        status 409 and code `fax_account_has_routed_numbers`. Needs
        `fax-accounts:write`.
        """
        await self._client.request(
            "DELETE",
            f"/v1/fax-accounts/{_path_segment(fax_account_id, noun=_NOUN)}",
        )
