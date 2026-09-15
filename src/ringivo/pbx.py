"""Your customers' phone systems: who is on them, what is registered, what
was called — and one write, which asks a phone to ring.

-- WHY ONE NAMESPACE WITH THREE COLLECTIONS INSIDE IT --------------------------
`client.pbx.users`, `client.pbx.devices` and `client.pbx.call_records` are
three resources of ONE subject, and the subject is the thing that makes
them legible: a subscriber, the registrations that subscriber's phones have
made, and the calls that came and went. Hanging them flat off the client
would put `client.devices` next to `client.faxes` and leave a reader
guessing which product's devices those are.

-- EVERY READ IS SCOPED, AND THERE IS NO UNSCOPED FORM -------------------------
The platform narrows every `/v1/pbx/` read to the phone-system domains of
the customers your credential may reach. A credential that reaches no such
customer is REFUSED WITH A 400 rather than handed an empty page, so
"nobody has a phone system yet" can never read as "nobody has any users".
That refusal arrives as an `ApiError`, like any other.

-- THIS SURFACE DOES NOT WRITE THE PHONE SYSTEM --------------------------------
Every attribute on `users` and `devices` is read-only, which is why neither
has a `create()`, an `update()` or a `delete()`. The one write in this
module is `users.call()`, and it does not write the phone system either: it
asks the switch to place a call and gets an acknowledgement back.

-- THE TWO SCOPES ARE NOT THE THREE COLLECTIONS --------------------------------
`pbx-users:read` reaches BOTH `users` and `devices` — a registration is
read as part of the subscriber it belongs to, not as a resource of its own.
`pbx-call-records:read` is separate, because a call log is a different
sensitivity from a directory: who called whom, and for how long, is the
half a reseller most often wants to withhold. `users.call()` needs
`pbx-calls:write`, which is a third scope again, for the obvious reason
that it makes somebody's phone ring.

-- TIMESTAMPS: TEXT ON TWO OF THEM, INSTANTS ON THE THIRD ----------------------
A user's and a device's timestamps are served as the phone system stores
them — TEXT, in a format the switch has never published — so this client
publishes them as `str` rather than guessing (models.py says why at
length). A call record's three instants are real `datetime`s: the switch
stores those as Unix epochs, and the API publishes them as RFC 3339 in UTC.

-- THE DATE RANGE ON call_records IS NOT AN ORDINARY FILTER --------------------
The phone system keeps one table per month, so `started_after` and
`started_before` decide which tables are opened at all. With no range you
get the current and previous month — not everything. A range wider than 13
months is refused with a 400 carrying `meta: {"filter": {"maxMonths": 13}}`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from .fax_accounts import _JSONAPI
from .faxes import _data_object, _next_cursor, _next_link, _path_segment
from .models import (
    CallRecord,
    CallRecordPage,
    PbxCall,
    PbxDevice,
    PbxDevicePage,
    PbxUser,
    PbxUserPage,
)

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .client import Ringivo

__all__ = ["Pbx", "PbxCallRecords", "PbxDevices", "PbxUsers"]

#: What `_path_segment` calls each resource in its refusal.
_USER_NOUN = "PBX user"
_DEVICE_NOUN = "PBX device"
_CALL_RECORD_NOUN = "call record"

#: The `type` member the click-to-dial request and its answer both carry.
#: A call REQUEST is its own resource — it is not a `users` write and not a
#: call record, which does not exist until the call has happened.
_CALLS_TYPE = "calls"


class Pbx:
    """The `client.pbx` namespace: three collections and one action."""

    def __init__(self, client: Ringivo) -> None:
        self.users = PbxUsers(client)
        self.devices = PbxDevices(client)
        self.call_records = PbxCallRecords(client)


class PbxUsers:
    """The `client.pbx.users` namespace."""

    def __init__(self, client: Ringivo) -> None:
        self._client = client

    def list(
        self,
        *,
        customer: str | None = None,
        user: str | None = None,
        search: str | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> PbxUserPage:
        """One page of subscribers, extension first.

        Args:
            customer: Only the subscribers of this customer's phone system.
            user: EXACT match on the extension — `101` does not match
                `1010`. This is the extension, not a `users` id.
            search: Case-insensitive substring match on the display name,
                first name, last name or extension. The one argument behind
                a directory search box.
            after: Walk forward: the previous page's
                `PbxUserPage.next_cursor`. Mutually exclusive with
                `before` — passing both is refused with a 400.
            before: Walk backward from a cursor.
            page_size: Rows per page. The default is 25 and the ceiling is
                100.

        Needs `pbx-users:read`. A credential that reaches no customer with
        a phone system is refused with a 400, not given an empty page.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
            "filter[customer]": customer,
            "filter[user]": user,
            "filter[search]": search,
        }
        document = self._client.request("GET", "/v1/pbx/users", params=params).json()
        return _user_page(document)

    def get(self, pbx_user_id: str) -> PbxUser:
        """Read one subscriber.

        A subscriber outside your customers' domains answers 404, not 403 —
        the same answer an id that names nothing anywhere gives, because
        telling the two apart would tell you the other one exists.

        Needs `pbx-users:read`.
        """
        response = self._client.request(
            "GET",
            f"/v1/pbx/users/{_path_segment(pbx_user_id, noun=_USER_NOUN)}",
        )
        return PbxUser._from_resource(_data_object(response.json()))

    def call(
        self,
        pbx_user_id: str,
        *,
        destination: str,
        caller_id: str | None = None,
        auto_answer: bool = False,
        device: str | None = None,
    ) -> PbxCall:
        """Ask this subscriber's phone to call somebody: click-to-dial.

        The phone system rings THIS SUBSCRIBER's phone and connects it to
        `destination`, so the call goes out as them rather than as the
        credential that asked for it.

        Returns as soon as the request is ACCEPTED (202), which is the
        whole of what a `PbxCall` says: it was handed to the phone system
        and `status` is `requested`, the only value this endpoint ever
        publishes. Nothing came back to say a phone rang or a person
        answered.

        AND THE ID IT HANDS BACK IS NOT A CALL-RECORD ID. It names the call
        on the PHONE SYSTEM — it is the SIP Call-ID the call is placed
        under — while a call record's id comes from the switch's CDR row.
        To find the records this call wrote, pass it to
        `call_records.list(call_id=...)` once the call has ended. See
        `PbxCall`.

        THIS IS NOT SAFE TO RETRY BLINDLY. A call is undoable by nothing —
        a real phone rings and a person picks it up — and this action
        carries no idempotency key, unlike `faxes.send()`. If you never saw
        the answer, find out what happened before asking again. A 502 is
        the exception and says so: the phone system refused the request or
        could not be reached, NOTHING WAS DIALLED, and the status it
        answered with is in `errors[0].meta["vendor_status"]` — so a
        refusal and an outage can be told apart before you try again.

        Args:
            pbx_user_id: The subscriber whose phone places the call. A
                subscriber your credential cannot reach answers 404, not
                403.
            destination: What to dial — an E.164 number with its `+`, or an
                extension of 2 to 7 digits on that subscriber's own domain,
                which the phone system completes itself.
            caller_id: The number the called party sees. E.164, with or
                without the `+`, and a ten-digit North American number is
                accepted too and answered with its country code. A value
                that is not a telephone number is refused rather than
                ignored. Left off the request when you do not pass one, and
                the subscriber's own is used.
            device: Which of that subscriber's registered devices to call
                from, as a `devices` id. It MUST belong to this subscriber:
                one that does not is refused with a 422 pointing at
                `/data/attributes/device`, whether it is somebody else's or
                does not exist — the two are not told apart, and nothing is
                dialled. Left off the request when you do not pass one, and
                the phone system rings that subscriber's devices as it
                normally would.
            auto_answer: Ask the subscriber's own phone to go off-hook by
                itself instead of ringing. Sent on every request, because it
                is a fact about the call rather than a setting to leave
                alone.

        The answer echoes what was actually SENT to the phone system, which
        is not always what you typed: `caller_id` comes back as E.164
        WITHOUT the plus.

        Needs `pbx-calls:write`.
        """
        response = self._client.request(
            "POST",
            f"/v1/pbx/users/{_path_segment(pbx_user_id, noun=_USER_NOUN)}/calls",
            accept=_JSONAPI,
            headers={"Content-Type": _JSONAPI},
            json=_call_document(
                destination=destination,
                caller_id=caller_id,
                auto_answer=auto_answer,
                device=device,
            ),
        )
        return PbxCall._from_resource(_data_object(response.json()))


class PbxDevices:
    """The `client.pbx.devices` namespace."""

    def __init__(self, client: Ringivo) -> None:
        self._client = client

    def list(
        self,
        *,
        customer: str | None = None,
        user: str | None = None,
        registered: bool | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> PbxDevicePage:
        """One page of registrations, by address of record.

        Args:
            customer: Only the registrations on this customer's phone
                system.
            user: Only this subscriber's registrations, BY `users` ID — not
                by extension, which is what the same-named filter on
                `users.list()` takes. An id you cannot reach answers an
                empty page rather than a refusal.
            registered: `True` for registrations that have not expired,
                `False` for the rest. Leave it off for both.
            after: Walk forward: the previous page's
                `PbxDevicePage.next_cursor`. Mutually exclusive with
                `before`.
            before: Walk backward from a cursor.
            page_size: Rows per page. The default is 25 and the ceiling is
                100.

        Needs `pbx-users:read` — the SAME scope as `users`, not one of its
        own: a registration is read as part of the subscriber it belongs
        to.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
            "filter[customer]": customer,
            "filter[user]": user,
            "filter[registered]": registered,
        }
        document = self._client.request("GET", "/v1/pbx/devices", params=params).json()
        return _device_page(document)

    def get(self, pbx_device_id: str) -> PbxDevice:
        """Read one registration.

        A registration outside your customers' domains answers 404, not
        403. So does one that has expired and been swept: the row exists
        because something registered, and it stops existing when nothing
        does.

        Needs `pbx-users:read`.
        """
        response = self._client.request(
            "GET",
            f"/v1/pbx/devices/{_path_segment(pbx_device_id, noun=_DEVICE_NOUN)}",
        )
        return PbxDevice._from_resource(_data_object(response.json()))


class PbxCallRecords:
    """The `client.pbx.call_records` namespace."""

    def __init__(self, client: Ringivo) -> None:
        self._client = client

    def list(
        self,
        *,
        customer: str | None = None,
        started_after: str | None = None,
        started_before: str | None = None,
        direction: str | None = None,
        user: str | None = None,
        call_id: str | None = None,
        include_hidden: bool | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> CallRecordPage:
        """One page of calls, newest first.

        THE DATE RANGE DECIDES WHICH MONTHS ARE READ, and that is not an
        ordinary filter: the phone system keeps one table per month, so
        `started_after` and `started_before` decide which tables are opened
        at all. Pass neither and you get the current and previous month —
        not everything there is. A range wider than 13 months is refused
        with a 400 carrying `meta: {"filter": {"maxMonths": 13}}`, so
        backfilling a longer history means walking it a window at a time.

        Args:
            customer: Only the calls on this customer's phone system.
            started_after: Calls that started at or after this moment, RFC
                3339 — `"2026-09-01T00:00:00Z"`.
            started_before: Calls that started at or before this moment,
                RFC 3339.
            direction: `inbound`, `outbound` or `on-net`. A word outside
                that list is refused with a 400 rather than answered with
                an empty page, which is why this client passes the value
                through instead of keeping a copy of the vocabulary that
                would go stale here. There is no filter on disposition:
                each `CallRecord` still carries `disposition`, and the list
                takes no argument for it.
            user: Calls with this subscriber on EITHER leg — placed by them
                or taken by them — by `users` id, not by extension.
            call_id: The records of ONE click-to-dial call. Pass the `id`
                that `users.call()` returned. The call record appears once
                the call has ended. One call writes two records: by default
                the list returns the visible dial-out record, and the hidden
                leg that rang the subscriber comes back only with
                `include_hidden=True`. THE DATE RANGE STILL APPLIES: the
                call id is matched only inside the months your range
                covers, and with no `started_after` or `started_before`
                that is the current and the previous month. To find an
                older call, pass a range that covers when it was placed. So
                an empty page means the call has not ended yet, it was
                placed outside the range, or the id names no call. It is
                never an error.
            include_hidden: `True` also returns the records the phone
                system marks hidden. They are left out by default, which is
                what the phone system's own call log does; a direct `get()`
                serves one either way.
            after: Walk forward: the previous page's
                `CallRecordPage.next_cursor`. Mutually exclusive with
                `before`.
            before: Walk backward from a cursor.
            page_size: Rows per page. The default is 25 and the ceiling is
                100.

        Needs `pbx-call-records:read`, which is a separate scope from
        `pbx-users:read`: a call log is a different sensitivity from a
        directory.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
            "filter[customer]": customer,
            "filter[started-after]": started_after,
            "filter[started-before]": started_before,
            "filter[direction]": direction,
            "filter[user]": user,
            "filter[call-id]": call_id,
            "filter[include-hidden]": include_hidden,
        }
        document = self._client.request("GET", "/v1/pbx/call-records", params=params).json()
        return _call_record_page(document)

    def get(self, call_record_id: str) -> CallRecord:
        """Read one call.

        A HIDDEN RECORD IS SERVED HERE. The list leaves it out and a direct
        read does not — the same asymmetry the phone system's own portal
        has, and the reason `hidden` is a fact about where a record can be
        found rather than about whether it exists.

        A call on a domain your credential cannot reach answers 404, not
        403.

        Needs `pbx-call-records:read`.
        """
        response = self._client.request(
            "GET",
            f"/v1/pbx/call-records/{_path_segment(call_record_id, noun=_CALL_RECORD_NOUN)}",
        )
        return CallRecord._from_resource(_data_object(response.json()))


def _call_document(
    *,
    destination: str,
    caller_id: str | None,
    auto_answer: bool,
    device: str | None,
) -> dict[str, Any]:
    """The JSON:API document `users.call()` posts.

    `caller-id` and `device` are LEFT OUT when they were not passed, rather
    than sent as null. They are optional members of a create, and on a
    create there is nothing to clear: an absent `caller-id` means "use the
    subscriber's own", which is not the same request as one naming no
    caller id at all. That is why neither takes the `NOT_GIVEN` sentinel
    the sparse PATCHes in fax_accounts.py need — two states are enough
    here, so `None` can be the spelling of "I said nothing".

    `auto-answer` is different and is always sent: it is a fact about this
    call, it has a default the caller can see in the signature, and `False`
    is a real value rather than a silence.
    """
    attributes: dict[str, Any] = {"destination": destination, "auto-answer": auto_answer}
    if caller_id is not None:
        attributes["caller-id"] = caller_id
    if device is not None:
        attributes["device"] = device

    return {"data": {"type": _CALLS_TYPE, "attributes": attributes}}


def _user_page(document: Any) -> PbxUserPage:
    """One `GET /v1/pbx/users` body, as the page this package hands back."""
    if not isinstance(document, Mapping):
        document = {}

    return PbxUserPage(
        users=tuple(PbxUser._from_resource(item) for item in _resources(document)),
        next_url=_next_link(document),
        next_cursor=_next_cursor(document),
        raw=document,
    )


def _device_page(document: Any) -> PbxDevicePage:
    """One `GET /v1/pbx/devices` body, as the page this package hands back."""
    if not isinstance(document, Mapping):
        document = {}

    return PbxDevicePage(
        devices=tuple(PbxDevice._from_resource(item) for item in _resources(document)),
        next_url=_next_link(document),
        next_cursor=_next_cursor(document),
        raw=document,
    )


def _call_record_page(document: Any) -> CallRecordPage:
    """One `GET /v1/pbx/call-records` body, as the page handed back."""
    if not isinstance(document, Mapping):
        document = {}

    return CallRecordPage(
        call_records=tuple(CallRecord._from_resource(item) for item in _resources(document)),
        next_url=_next_link(document),
        next_cursor=_next_cursor(document),
        raw=document,
    )


def _resources(document: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """The `data` member's resource objects, and nothing that is not one.

    The three page readers above differ only in which model they build, so
    the defensive read they share lives here rather than three times: a
    `data` that is missing or is not a list reads as no rows, and an item
    that is not an object is dropped rather than raising.
    """
    data = document.get("data")
    return [item for item in (data if isinstance(data, list) else []) if isinstance(item, Mapping)]
