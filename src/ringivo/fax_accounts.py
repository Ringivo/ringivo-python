"""Open a fax account, read one, list them, change one, delete one.

-- WHY THIS IS A SECOND MODULE AND NOT MORE OF faxes.py ------------------------
A fax and a fax account are different resources with different lifetimes,
different scopes and different bodies, and the two modules share exactly
four private helpers — the path escaper and the three JSON readers — which
are imported rather than copied for the reason async_faxes.py gives about
its own imports: one of them is a security control, and a second copy of a
security control is a second thing to get wrong.

-- THE BODIES HERE ARE JSON:API DOCUMENTS --------------------------------------
`POST /v1/faxes` is the odd one out on this API: its body is multipart or
flat JSON. Every fax-account write is an ordinary JSON:API document —
`{"data": {"type": "fax-accounts", "attributes": {...}}}` — sent AND
accepted as `application/vnd.api+json`. The content type is set explicitly
on each write, because httpx stamps `application/json` on a `json=` body
and this surface answers 415 to that.

-- SPARSE WRITES, AND THE SENTINEL THAT MAKES THEM POSSIBLE --------------------
`update()` sends only the attributes the caller named, so changing a
status leaves the retention rules alone. That needs THREE states per
argument, not two: send this value, send `null`, or send nothing. `None`
is already spoken for — it is how a caller CLEARS a nullable field
(`default_from_e164=None` removes the default caller ID; `retention_days=
None` turns the age rule off entirely) — so "not given" needs a value of
its own, and that is `NOT_GIVEN`.

`create()` takes the same sentinel for the same reason and a different
benefit: an attribute nobody named is ABSENT from the document, so the
platform's own defaults apply (one year, no page limit) rather than this
client inventing them. A client that filled in defaults would freeze
today's policy into an installed package.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from .errors import RingivoError
from .faxes import _data_object, _next_cursor, _next_link, _path_segment
from .models import FaxAccount, FaxAccountNumber, FaxAccountPage

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .client import Ringivo

__all__ = ["FaxAccounts"]

#: What this whole resource surface sends and accepts.
_JSONAPI = "application/vnd.api+json"

#: The `type` member every fax-account document carries.
_TYPE = "fax-accounts"

#: The page size `numbers()` asks for. It is the API's published ceiling, so
#: the walk below makes as few requests as the server allows.
_MAX_PAGE_SIZE = 100

#: What `_path_segment` calls this resource in its refusal.
_NOUN = "fax account"


class FaxAccounts:
    """The `client.fax_accounts` namespace."""

    def __init__(self, client: Ringivo) -> None:
        self._client = client

    def list(
        self,
        *,
        customer: str | None = None,
        status: str | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> FaxAccountPage:
        """One page of fax accounts, newest first.

        Which accounts you see depends on the credential: a token issued for
        a PERSON lists the accounts that person was granted, while a machine
        credential lists every account in its scope.

        Args:
            customer: Only this customer's accounts.
            status: `active` or `suspended`. A suspended account still
                receives faxes; it may not send them.
            after: Walk forward: the previous page's
                `FaxAccountPage.next_cursor`. Mutually exclusive with
                `before` — passing both is refused with a 400.
            before: Walk backward from a cursor — how you poll for rows that
                arrived since your last read.
            page_size: Rows per page. The default is 25 and the ceiling is
                100.

        Needs `fax:read`.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
            "filter[customer]": customer,
            "filter[status]": status,
        }
        document = self._client.request("GET", "/v1/fax-accounts", params=params).json()
        return _page(document)

    def get(self, fax_account_id: str) -> FaxAccount:
        """Read one fax account.

        An id that is not yours answers 404, the same as one that names
        nothing anywhere — a foreign account does not resolve rather than
        being fetched and then refused.

        Needs `fax:read`.
        """
        response = self._client.request(
            "GET",
            f"/v1/fax-accounts/{_path_segment(fax_account_id, noun=_NOUN)}",
        )
        return FaxAccount._from_resource(_data_object(response.json()))

    def numbers(self, fax_account_id: str) -> tuple[FaxAccountNumber, ...]:
        """EVERY number routed to this account, not one page of them.

        The collection is cursor-paginated, and this walks it to the end
        before returning. That is deliberate: a truncated list is
        indistinguishable from a complete one — every row on it is real — and
        "which numbers does this account hold?" is a question whose wrong
        answer looks exactly like the right one. An account holds a handful
        of DIDs, so the walk is one request in practice and asks for the
        ceiling page size to keep it that way.

        Attaching a number is NOT done here. A number points at one
        destination and that rule belongs to the number, so routing is
        `POST /v1/phone-numbers/{id}/routing` — reachable through
        `client.request()`.

        Raises:
            RingivoError: The server served the same cursor twice. A walk
                that trusted it would never end, and a hang is the one
                failure a caller cannot see.

        Needs `fax:read`.
        """
        path = f"/v1/fax-accounts/{_path_segment(fax_account_id, noun=_NOUN)}/numbers"
        found: list[FaxAccountNumber] = []
        cursor: str | None = None
        seen: set[str] = set()

        while True:
            document = self._client.request(
                "GET",
                path,
                params={"page[size]": _MAX_PAGE_SIZE, "page[after]": cursor},
            ).json()
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


def _page(document: Any) -> FaxAccountPage:
    """One `GET /v1/fax-accounts` body, as the page this package hands back."""
    if not isinstance(document, Mapping):
        document = {}

    data = document.get("data")
    accounts = tuple(
        FaxAccount._from_resource(item)
        for item in (data if isinstance(data, list) else [])
        if isinstance(item, Mapping)
    )
    return FaxAccountPage(
        accounts=accounts,
        next_url=_next_link(document),
        next_cursor=_next_cursor(document),
        raw=document,
    )


def _numbers(document: Any) -> tuple[FaxAccountNumber, ...]:
    """The `phone-numbers` resources in one page of the numbers relationship."""
    if not isinstance(document, Mapping):
        return ()

    data = document.get("data")
    return tuple(
        FaxAccountNumber._from_resource(item)
        for item in (data if isinstance(data, list) else [])
        if isinstance(item, Mapping)
    )
