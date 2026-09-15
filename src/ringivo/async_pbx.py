"""Your customers' phone systems, and one call placed into them — awaited.

The SIBLING of pbx.py, method for method: each body here is its twin's
body with an `await` on the line that goes to the network. The three page
readers, the request builder, the nouns and faxes.py's path escaper are
imported rather than copied, for the reason async_fax_accounts.py gives
about its own imports — they are pure functions of their arguments, they
touch no client, and one of them is a security control.

Read pbx.py for the whys: why one namespace holds three collections, why
every `/v1/pbx/` read is scoped and an unreachable credential is a 400
rather than an empty page, why `devices` shares the `users` scope, why two
of the three resources publish their timestamps as text, and why the date
range on `call_records` decides which months are read at all.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .fax_accounts import _JSONAPI
from .faxes import _data_object, _path_segment
from .models import (
    CallRecord,
    CallRecordPage,
    PbxCall,
    PbxDevice,
    PbxDevicePage,
    PbxUser,
    PbxUserPage,
)
from .pbx import (
    _CALL_RECORD_NOUN,
    _DEVICE_NOUN,
    _USER_NOUN,
    _call_document,
    _call_record_page,
    _device_page,
    _user_page,
)

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .async_client import AsyncRingivo

__all__ = ["AsyncPbx", "AsyncPbxCallRecords", "AsyncPbxDevices", "AsyncPbxUsers"]


class AsyncPbx:
    """The `client.pbx` namespace on `AsyncRingivo`."""

    def __init__(self, client: AsyncRingivo) -> None:
        self.users = AsyncPbxUsers(client)
        self.devices = AsyncPbxDevices(client)
        self.call_records = AsyncPbxCallRecords(client)


class AsyncPbxUsers:
    """The `client.pbx.users` namespace on `AsyncRingivo`."""

    def __init__(self, client: AsyncRingivo) -> None:
        self._client = client

    async def list(
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

        The awaited twin of `PbxUsers.list`, and the same arguments mean
        the same things: `user` is an EXACT extension rather than a `users`
        id, `search` is the one argument behind a directory search box, and
        `after`/`before` are mutually exclusive.

        Needs `pbx-users:read`.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
            "filter[customer]": customer,
            "filter[user]": user,
            "filter[search]": search,
        }
        response = await self._client.request("GET", "/v1/pbx/users", params=params)
        return _user_page(response.json())

    async def get(self, pbx_user_id: str) -> PbxUser:
        """Read one subscriber.

        The awaited twin of `PbxUsers.get`. A subscriber outside your
        customers' domains answers 404, not 403.

        Needs `pbx-users:read`.
        """
        response = await self._client.request(
            "GET",
            f"/v1/pbx/users/{_path_segment(pbx_user_id, noun=_USER_NOUN)}",
        )
        return PbxUser._from_resource(_data_object(response.json()))

    async def call(
        self,
        pbx_user_id: str,
        *,
        destination: str,
        caller_id: str | None = None,
        auto_answer: bool = False,
        device: str | None = None,
    ) -> PbxCall:
        """Ask this subscriber's phone to call somebody: click-to-dial.

        The awaited twin of `PbxUsers.call`, and it carries the same
        warnings: a 202 says the request was accepted, not that a phone
        rang; the id it hands back names the call on the PHONE SYSTEM rather
        than a call record, and `call_records.list(call_id=...)` finds the
        records it wrote once the call has ended; and THIS IS NOT SAFE TO
        RETRY BLINDLY — a call is undoable by nothing and the
        action carries no idempotency key. A 502 is the exception, and
        `errors[0].meta["vendor_status"]` is why.

        `caller_id` and `device` are left off the request when you do not
        pass one; `auto_answer` is sent on every request. The answer echoes
        what was SENT, so `caller_id` comes back as E.164 without the plus.

        Needs `pbx-calls:write`.
        """
        response = await self._client.request(
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


class AsyncPbxDevices:
    """The `client.pbx.devices` namespace on `AsyncRingivo`."""

    def __init__(self, client: AsyncRingivo) -> None:
        self._client = client

    async def list(
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

        The awaited twin of `PbxDevices.list`. `user` here is a `users`
        ID, unlike the same-named filter on `users.list()`, which is an
        extension.

        Needs `pbx-users:read` — the same scope as `users`.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
            "filter[customer]": customer,
            "filter[user]": user,
            "filter[registered]": registered,
        }
        response = await self._client.request("GET", "/v1/pbx/devices", params=params)
        return _device_page(response.json())

    async def get(self, pbx_device_id: str) -> PbxDevice:
        """Read one registration.

        The awaited twin of `PbxDevices.get`. A registration that has
        expired and been swept answers 404, because the row exists only
        while something is registered.

        Needs `pbx-users:read`.
        """
        response = await self._client.request(
            "GET",
            f"/v1/pbx/devices/{_path_segment(pbx_device_id, noun=_DEVICE_NOUN)}",
        )
        return PbxDevice._from_resource(_data_object(response.json()))


class AsyncPbxCallRecords:
    """The `client.pbx.call_records` namespace on `AsyncRingivo`."""

    def __init__(self, client: AsyncRingivo) -> None:
        self._client = client

    async def list(
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

        The awaited twin of `PbxCallRecords.list`, and the date range is
        the same load-bearing argument it is there: it decides which
        monthly tables are opened, no range means the current and previous
        month, and a range wider than 13 months is refused with a 400.

        Hidden records are left out unless `include_hidden=True`.

        `call_id` takes the `id` that `users.call()` returned, and finds
        that call's records once the call has ended: by default the visible
        dial-out record, and the hidden leg that rang the subscriber only
        with `include_hidden=True`. There is no filter on disposition.

        Needs `pbx-call-records:read`.
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
        response = await self._client.request("GET", "/v1/pbx/call-records", params=params)
        return _call_record_page(response.json())

    async def get(self, call_record_id: str) -> CallRecord:
        """Read one call.

        The awaited twin of `PbxCallRecords.get`. A hidden record IS served
        here — the list leaves it out and a direct read does not.

        Needs `pbx-call-records:read`.
        """
        response = await self._client.request(
            "GET",
            f"/v1/pbx/call-records/{_path_segment(call_record_id, noun=_CALL_RECORD_NOUN)}",
        )
        return CallRecord._from_resource(_data_object(response.json()))
