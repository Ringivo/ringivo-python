"""Who may read one fax account's faxes: list the grants, read one, grant
access, withdraw it.

-- WHAT A GRANT IS -------------------------------------------------------------
A row on this collection is a PAIR AND A FACT: this user may read this fax
account's content. It is not a user and not an account, and it holds no
settings of its own — which is why there is no update route on it. A grant
exists or it does not; you withdraw one by deleting it and re-make it by
creating another.

It exists because administering an account and reading its content are
gated differently. Holding the account write permission lets somebody
manage the account without a grant; a grant is how that person hands ONE
account's content to somebody who holds no such permission — a
customer-facing staffer, say, who should see this customer's faxes and no
others.

-- WHY A THIRD MODULE AND NOT MORE OF fax_accounts.py --------------------------
The same reason fax_accounts.py gives for not being more of faxes.py: a
different resource, with a different lifetime, different scopes and a
different body. It shares the four private helpers every module here
shares — the path escaper and the three JSON readers — imported rather
than copied, because one of them is a security control and a second copy
of a security control is a second thing to get wrong.

-- THE BODY IS A JSON:API DOCUMENT, AND IT IS ALL RELATIONSHIPS ----------------
`{"data": {"type": "fax-account-users", "relationships": {...}}}`, sent AND
accepted as `application/vnd.api+json`, with the content type set
explicitly because httpx stamps `application/json` on a `json=` body and
this surface answers 415 to that.

The document carries NO attributes member at all, and that is not an
omission this client makes: both of a grant's members are relationships,
and the one attribute the API publishes back — the grantee's email — is a
read of the user rather than anything a caller writes.

-- NO SENTINEL HERE ------------------------------------------------------------
fax_accounts.py needs `NOT_GIVEN` because its PATCH is sparse and a field
there has three states: send this value, send `null`, send nothing. This
resource has no PATCH and no optional member on its write, so every
argument is required and two states are enough. The sentinel is
deliberately not imported: an argument that cannot be omitted does not
need a value meaning "omitted".
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from .fax_accounts import _JSONAPI
from .faxes import _data_object, _next_cursor, _next_link, _path_segment
from .models import FaxAccountUser, FaxAccountUserPage

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .client import Ringivo

__all__ = ["FaxAccountUsers"]

#: The `type` member every grant document carries.
_TYPE = "fax-account-users"

#: The `type` member of the account half of the pair.
_FAX_ACCOUNT_TYPE = "fax-accounts"

#: The `type` member of the user half of the pair.
_USER_TYPE = "users"

#: What `_path_segment` calls this resource in its refusal.
_NOUN = "fax account user"


class FaxAccountUsers:
    """The `client.fax_account_users` namespace."""

    def __init__(self, client: Ringivo) -> None:
        self._client = client

    def list(
        self,
        *,
        fax_account: str | None = None,
        user: str | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> FaxAccountUserPage:
        """One page of grants, newest first.

        The two filters answer the two questions this collection is for:
        `fax_account=` is "who can see this account's faxes?", and `user=`
        is "what can this person see?".

        Args:
            fax_account: Only grants on this fax account.
            user: Only grants held by this user.
            after: Walk forward: the previous page's
                `FaxAccountUserPage.next_cursor`. Mutually exclusive with
                `before` — passing both is refused with a 400.
            before: Walk backward from a cursor.
            page_size: Rows per page. The default is 25 and the ceiling is
                100.

        Needs `fax:read`.
        """
        # THE FILTER NAMES ARE snake_case AND THE REST OF THIS RESOURCE IS
        # NOT. `filter[fax_account]` is the API's own spelling, while the
        # relationship it filters on is `faxAccount` and every attribute is
        # camelCase too. The asymmetry is real and deliberate on the
        # server's side — filters are query parameters, not document
        # members — so "correcting" either half here would send a filter
        # the API ignores, which reads back as a page of everything.
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
            "filter[fax_account]": fax_account,
            "filter[user]": user,
        }
        document = self._client.request(
            "GET", "/v1/fax-account-users", params=params
        ).json()
        return _page(document)

    def get(self, fax_account_user_id: str) -> FaxAccountUser:
        """Read one grant.

        An id that is not yours answers 404, the same as one that names
        nothing anywhere.

        Needs `fax:read`.
        """
        response = self._client.request(
            "GET",
            f"/v1/fax-account-users/{_path_segment(fax_account_user_id, noun=_NOUN)}",
        )
        return FaxAccountUser._from_resource(_data_object(response.json()))

    def create(self, *, fax_account: str, user: str) -> FaxAccountUser:
        """Grant one user access to one fax account's content.

        Args:
            fax_account: The account whose faxes and pages this user may
                read. It MAY be an account you do not hold a grant on
                yourself: administering an account is permission-gated
                while reading its content is grant-gated, so somebody has
                to be able to add the first member.
            user: The person who gets the access.

        Both are required and neither can be changed afterwards, because
        there is nothing here to change — a grant is a pair and a fact.
        Point it at a different account by deleting this one and creating
        another.

        Making the same grant twice is the server's question to answer, not
        this client's: the pair is what the row IS, so a duplicate is
        refused as an `ApiError` rather than quietly making a second row.

        A fax account or a user that is not yours answers 404 on the
        relationship pointer, the same as one that names nothing anywhere —
        a foreign id does not resolve rather than being fetched and then
        refused.

        Needs `fax-accounts:write`.
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

        response = self._client.request(
            "POST",
            "/v1/fax-account-users",
            accept=_JSONAPI,
            headers={"Content-Type": _JSONAPI},
            json=document,
        )
        return FaxAccountUser._from_resource(_data_object(response.json()))

    def delete(self, fax_account_user_id: str) -> None:
        """Withdraw a grant. The access goes; nothing else does.

        The user stops being able to read this account's faxes and pages.
        Nothing is deleted but the grant itself — not the account, not the
        user, not one fax — and a user who reaches the account by
        permission rather than by this grant still reaches it.

        This is the ONLY way to undo a grant: the resource has no update
        route, because a grant holds nothing that could be updated.

        Returns None: the API answers 204 with no body.

        Needs `fax-accounts:write`.
        """
        self._client.request(
            "DELETE",
            f"/v1/fax-account-users/{_path_segment(fax_account_user_id, noun=_NOUN)}",
        )


def _page(document: Any) -> FaxAccountUserPage:
    """One `GET /v1/fax-account-users` body, as the page this package hands back."""
    if not isinstance(document, Mapping):
        document = {}

    data = document.get("data")
    grants = tuple(
        FaxAccountUser._from_resource(item)
        for item in (data if isinstance(data, list) else [])
        if isinstance(item, Mapping)
    )
    return FaxAccountUserPage(
        grants=grants,
        next_url=_next_link(document),
        next_cursor=_next_cursor(document),
        raw=document,
    )
