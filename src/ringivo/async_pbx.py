"""Your customers' phone systems, and one call placed into them — awaited.

The SIBLING of pbx.py, method for method: each body here is its twin's
body with an `await` on the line that goes to the network. The three page
readers, the request builder, the nouns and faxes.py's path escaper are
imported rather than copied, for the reason async_fax_accounts.py gives
about its own imports — they are pure functions of their arguments, they
touch no client, and one of them is a security control.

Read pbx.py for the whys: why one namespace holds three collections, why
every `/v1/pbx/` read is scoped and an unreachable credential is a 400
rather than an empty page, why `devices` shares the `subscribers` scope, why two
of the three resources publish their timestamps as text, and why the date
range on `call_records` decides which months are read at all.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from .fax_accounts import _JSONAPI
from .faxes import _data_object, _path_segment
from .models import (
    CallRecord,
    CallRecordPage,
    PbxCall,
    PbxDevice,
    PbxDevicePage,
    PbxSubscriber,
    PbxSubscriberPage,
    Recording,
    Transcript,
)
from .pbx import (
    _CALL_RECORD_NOUN,
    _DEVICE_NOUN,
    _SUBSCRIBER_NOUN,
    _call_document,
    _call_record_page,
    _device_page,
    _fields_param,
    _recordings,
    _transcripts,
    _kind_param,
    _subscriber_page,
)

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .async_client import AsyncRingivo

__all__ = ["AsyncPbx", "AsyncPbxCallRecords", "AsyncPbxDevices", "AsyncPbxSubscribers"]


class AsyncPbx:
    """The `client.pbx` namespace on `AsyncRingivo`."""

    def __init__(self, client: AsyncRingivo) -> None:
        self.subscribers = AsyncPbxSubscribers(client)
        self.devices = AsyncPbxDevices(client)
        self.call_records = AsyncPbxCallRecords(client)


class AsyncPbxSubscribers:
    """The `client.pbx.subscribers` namespace on `AsyncRingivo`."""

    def __init__(self, client: AsyncRingivo) -> None:
        self._client = client

    async def list(
        self,
        *,
        customer: str | None = None,
        user: str | None = None,
        search: str | None = None,
        kind: str | Sequence[str] | None = None,
        has_devices: bool | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> PbxSubscriberPage:
        """One page of subscribers — people and machines — extension first.

        The awaited twin of `PbxSubscribers.list`, and the same arguments
        mean the same things: `user` is an EXACT extension rather than a
        `subscribers` id, `search` is the one argument behind a directory
        search box, `kind` is one word, a comma list or a list of words,
        `has_devices` narrows to subscribers with (or without) a device, and
        `after`/`before` are mutually exclusive. A click-to-call picker
        passes `kind="user", has_devices=True`.

        Needs `pbx-users:read`.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
            "filter[customer]": customer,
            "filter[user]": user,
            "filter[search]": search,
            "filter[kind]": _kind_param(kind),
            "filter[hasDevices]": has_devices,
        }
        response = await self._client.request("GET", "/v1/pbx/subscribers", params=params)
        return _subscriber_page(response.json())

    async def get(self, subscriber_id: str) -> PbxSubscriber:
        """Read one subscriber.

        The awaited twin of `PbxSubscribers.get`. A subscriber outside your
        customers' domains answers 404, not 403.

        Needs `pbx-users:read`.
        """
        response = await self._client.request(
            "GET",
            f"/v1/pbx/subscribers/{_path_segment(subscriber_id, noun=_SUBSCRIBER_NOUN)}",
        )
        return PbxSubscriber._from_resource(_data_object(response.json()))

    async def call(
        self,
        subscriber_id: str,
        *,
        destination: str,
        caller_id: str | None = None,
        auto_answer: bool = False,
        device: str | None = None,
    ) -> PbxCall:
        """Ask this subscriber's phone to call somebody: click-to-dial.

        The awaited twin of `PbxSubscribers.call`, and it carries the same
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
            f"/v1/pbx/subscribers/{_path_segment(subscriber_id, noun=_SUBSCRIBER_NOUN)}/calls",
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

        The awaited twin of `PbxDevices.list`. `user` here is a
        `subscribers` ID, unlike the same-named filter on
        `subscribers.list()`, which is an extension.

        Needs `pbx-users:read` — the same scope as `subscribers`.
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
        fields: Sequence[str] | None = None,
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

        `direction` is `inbound`, `outbound` or `internal`, passed through
        rather than validated locally. There is no filter on disposition.

        `fields` asks for the EXTENDED tier — the phone system's own raw
        values — as a list of the API's own camelCase names, e.g.
        `["direction", "startedAt", "origCallId"]`. It is a sparse fieldset, so
        it NARROWS: name every field you want, standard ones included, or
        leave it off for the standard tier alone.

        call_id: The records of ONE click-to-dial call. Pass the `id`
            that `subscribers.call()` returned. The call record appears once
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

        Needs `pbx-call-records:read`.
        """
        params: dict[str, Any] = {
            "page[after]": after,
            "page[before]": before,
            "page[size]": page_size,
            "filter[customer]": customer,
            "filter[startedAfter]": started_after,
            "filter[startedBefore]": started_before,
            "filter[direction]": direction,
            "fields[call-records]": _fields_param(fields),
            "filter[user]": user,
            "filter[callId]": call_id,
            "filter[includeHidden]": include_hidden,
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

    async def recordings(self, call_record_id: str) -> tuple[Recording, ...]:
        """Every capture of one call, each with a freshly minted content link.

        The awaited twin of `PbxCallRecords.recordings`. NOT PAGINATED —
        this is the captures of one call, bounded by its two legs, so there
        is no cursor and nothing beyond this tuple to walk.

        Each `Recording.content_url` is short-lived; call this again for a
        fresh one rather than caching one past its `expires_at`.

        Needs `pbx-call-records:read`, the same scope `get()` needs.
        """
        response = await self._client.request(
            "GET",
            f"/v1/pbx/call-records/{_path_segment(call_record_id, noun=_CALL_RECORD_NOUN)}/recordings",
        )
        return _recordings(response.json())

    async def transcripts(self, call_record_id: str) -> tuple[Transcript, ...]:
        """One item per capture of the call, with the state of its transcript.

        The awaited twin of `PbxCallRecords.transcripts`. ONE ITEM PER
        RECORDING, not one per transcript that exists — a capture with no
        words yet still appears, as `status="pending"` with every other
        field None. NOT PAGINATED, for the reason `recordings()` is not.

        This is the collection read only: it never tells a permanent
        failure apart from a wait, and it carries no speaker turns. Both
        need the single-transcript endpoint, which this client does not
        yet wrap.

        Needs BOTH `pbx-call-records:read` AND `pbx-transcripts:read`,
        asked in that order — the words of a call are a separate grant
        from the call log itself.
        """
        response = await self._client.request(
            "GET",
            f"/v1/pbx/call-records/{_path_segment(call_record_id, noun=_CALL_RECORD_NOUN)}/transcripts",
        )
        return _transcripts(response.json())
