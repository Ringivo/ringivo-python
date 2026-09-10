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
from typing import TYPE_CHECKING, Any, Final

from .errors import RingivoError
from .faxes import _data_object, _next_cursor, _next_link, _path_segment
from .models import FaxAccount, FaxAccountNumber, FaxAccountPage

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .client import Ringivo

__all__ = ["NOT_GIVEN", "FaxAccounts", "NotGiven"]

#: What this whole resource surface sends and accepts.
_JSONAPI = "application/vnd.api+json"

#: The `type` member every fax-account document carries.
_TYPE = "fax-accounts"

#: The page size `numbers()` asks for. It is the API's published ceiling, so
#: the walk below makes as few requests as the server allows.
_MAX_PAGE_SIZE = 100

#: What `_path_segment` calls this resource in its refusal.
_NOUN = "fax account"


class NotGiven:
    """The type of `NOT_GIVEN`. Write it in an annotation; never build one.

    It exists because a write on this surface has THREE states per field and
    Python's default argument gives you two. `default_from_e164=None` means
    "clear the default caller ID" and `retention_days=None` means "keep the
    pages for ever" — both are values the API is sent as `null` — so "the
    caller said nothing about this field" needs a value that is not None.

    It is falsey, like `None`, so a caller writing `if header_text:` gets
    the reading they expect. Nothing in this package branches on its
    truthiness: the check is always `isinstance(value, NotGiven)`, because
    an empty string is falsey too and is a perfectly good header line to
    ask for.
    """

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "NOT_GIVEN"


#: The one instance. Compare with `isinstance`, never with `==`.
NOT_GIVEN: Final[NotGiven] = NotGiven()


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

    def create(
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

        Args:
            customer: The customer this account is FOR. Required, and fixed
                for the account's life — every fax it holds carries the
                customer it was sent or received for, so `update()` cannot
                move it. A customer id that is not yours answers 404 on the
                relationship pointer, the same as one that names nothing.
            name: What a person calls this account.
            header_text: The line printed across the top of every page, up
                to 64 characters — the fax protocol's own column, not a
                product choice. Pass None or an empty string for NO header
                line at all: the renderer skips the overlay, page count
                included.
            default_from_e164: The caller ID a send falls back to when it
                names none. It may be set before the number is routed —
                whether this account holds it is asked at the send, not
                here.
            retention_days: Delete this account's fax pages once they are
                older than this many days. **None turns the rule off** —
                the pages are kept for ever.
            retention_pages: Keep only this many of the newest pages.
                **None turns the rule off** — there is no page limit.

        Leave an argument out and the platform's own default applies: one
        year of retention and no page limit, at the time of writing. This
        client deliberately sends nothing for an argument nobody named, so
        that policy stays the platform's rather than being frozen into an
        installed package.

        Numbers are not attached here: point a DID at the account through
        the routing API.

        Needs `fax-accounts:write`.
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

        response = self._client.request(
            "POST",
            "/v1/fax-accounts",
            accept=_JSONAPI,
            headers={"Content-Type": _JSONAPI},
            json=document,
        )
        return FaxAccount._from_resource(_data_object(response.json()))

    def update(
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

        A SPARSE PATCH: only the arguments you pass are sent, so changing a
        status leaves the retention rules exactly as they were. `None` is a
        value rather than an omission — it clears a nullable field, which
        for the two retention arguments means turning that prune rule OFF.

        Args:
            status: `active`, or `suspended` to stop this account SENDING
                while it goes on receiving. Suspending deletes nothing.

        Every other argument means what it means on `create()`.

        An account cannot be moved to another customer, and there is no
        argument here that would try.

        Raises:
            ValueError: No field was named. An empty PATCH spends a round
                trip and an audit entry to change nothing, and it is far
                more often a form that came back empty than an intention.

        Needs `fax-accounts:write`.
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

        response = self._client.request(
            "PATCH",
            f"/v1/fax-accounts/{_path_segment(fax_account_id, noun=_NOUN)}",
            accept=_JSONAPI,
            headers={"Content-Type": _JSONAPI},
            json=document,
        )
        return FaxAccount._from_resource(_data_object(response.json()))

    def delete(self, fax_account_id: str) -> None:
        """Delete a fax account. The pages go; the records stay.

        This DESTROYS the stored pages of every fax on the account and
        cannot be undone — download anything you want to keep first. The
        account then leaves your listings and the people granted it lose
        access. The fax records themselves survive, because they are the
        billing and audit evidence, and nothing bills after this.

        It is REFUSED while any number still routes to the account: that is
        an `ApiError` whose `status_code` is 409 and whose `code` is
        `fax_account_has_routed_numbers`. Move or release the numbers
        through the routing API, then delete. Branch on `code` rather than
        on the status — a fax that cannot be cancelled is a 409 too, and it
        carries no code at all.

        Returns None: the API answers 204 with no body.

        Needs `fax-accounts:write`.
        """
        self._client.request(
            "DELETE",
            f"/v1/fax-accounts/{_path_segment(fax_account_id, noun=_NOUN)}",
        )


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


def _given(attributes: Mapping[str, Any]) -> dict[str, Any]:
    """Every attribute the caller actually named — `None` included.

    `NOT_GIVEN` is dropped and `None` is KEPT, because the two mean
    different things on the wire: an absent member leaves the server's value
    exactly as it was, while `null` clears a nullable field. Collapsing them
    would make `retention_days=None` — "keep these pages for ever" —
    indistinguishable from not mentioning retention at all.
    """
    return {
        name: value for name, value in attributes.items() if not isinstance(value, NotGiven)
    }
