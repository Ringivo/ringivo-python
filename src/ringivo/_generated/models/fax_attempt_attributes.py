from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.fax_attempt_attributes_transport_profile_type_0 import (
        FaxAttemptAttributesTransportProfileType0,
    )


T = TypeVar("T", bound="FaxAttemptAttributes")


@_attrs_define
class FaxAttemptAttributes:
    """One call placed for one fax. Two independent sources fill it: a busy or unanswered call
    produces no fax-protocol event, so `hangupCause` is the only classifier there — and the
    reverse happens too. Both sides are nullable because both are nullable in fact.

        Attributes:
            attempt_no (int | None | Unset):
            transport_profile (FaxAttemptAttributesTransportProfileType0 | None | Unset): The ladder rung this call used,
                whole — the transport plus whether ECM and V.17 were on.
                Null on an inbound call: nobody negotiated a rung for one.
            started_at (datetime.datetime | None | Unset):
            answered_at (datetime.datetime | None | Unset):
            ended_at (datetime.datetime | None | Unset):
            billable_ms (int | None | Unset):
            hangup_cause (None | str | Unset):
            sip_status (int | None | Unset):
            fax_success (bool | None | Unset):
            fax_result_code (int | None | Unset):
            fax_result_text (None | str | Unset):
            pages_transferred (int | None | Unset):
            pages_total (int | None | Unset):
            transfer_rate (int | None | Unset):
            ecm_used (bool | None | Unset):
            t_38_used (bool | None | Unset):
            image_resolution (None | str | Unset):
            bad_rows (int | None | Unset):
            remote_station_id (None | str | Unset):
    """

    attempt_no: int | None | Unset = UNSET
    transport_profile: FaxAttemptAttributesTransportProfileType0 | None | Unset = UNSET
    started_at: datetime.datetime | None | Unset = UNSET
    answered_at: datetime.datetime | None | Unset = UNSET
    ended_at: datetime.datetime | None | Unset = UNSET
    billable_ms: int | None | Unset = UNSET
    hangup_cause: None | str | Unset = UNSET
    sip_status: int | None | Unset = UNSET
    fax_success: bool | None | Unset = UNSET
    fax_result_code: int | None | Unset = UNSET
    fax_result_text: None | str | Unset = UNSET
    pages_transferred: int | None | Unset = UNSET
    pages_total: int | None | Unset = UNSET
    transfer_rate: int | None | Unset = UNSET
    ecm_used: bool | None | Unset = UNSET
    t_38_used: bool | None | Unset = UNSET
    image_resolution: None | str | Unset = UNSET
    bad_rows: int | None | Unset = UNSET
    remote_station_id: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.fax_attempt_attributes_transport_profile_type_0 import (
            FaxAttemptAttributesTransportProfileType0,
        )

        attempt_no: int | None | Unset
        if isinstance(self.attempt_no, Unset):
            attempt_no = UNSET
        else:
            attempt_no = self.attempt_no

        transport_profile: dict[str, Any] | None | Unset
        if isinstance(self.transport_profile, Unset):
            transport_profile = UNSET
        elif isinstance(self.transport_profile, FaxAttemptAttributesTransportProfileType0):
            transport_profile = self.transport_profile.to_dict()
        else:
            transport_profile = self.transport_profile

        started_at: None | str | Unset
        if isinstance(self.started_at, Unset):
            started_at = UNSET
        elif isinstance(self.started_at, datetime.datetime):
            started_at = self.started_at.isoformat()
        else:
            started_at = self.started_at

        answered_at: None | str | Unset
        if isinstance(self.answered_at, Unset):
            answered_at = UNSET
        elif isinstance(self.answered_at, datetime.datetime):
            answered_at = self.answered_at.isoformat()
        else:
            answered_at = self.answered_at

        ended_at: None | str | Unset
        if isinstance(self.ended_at, Unset):
            ended_at = UNSET
        elif isinstance(self.ended_at, datetime.datetime):
            ended_at = self.ended_at.isoformat()
        else:
            ended_at = self.ended_at

        billable_ms: int | None | Unset
        if isinstance(self.billable_ms, Unset):
            billable_ms = UNSET
        else:
            billable_ms = self.billable_ms

        hangup_cause: None | str | Unset
        if isinstance(self.hangup_cause, Unset):
            hangup_cause = UNSET
        else:
            hangup_cause = self.hangup_cause

        sip_status: int | None | Unset
        if isinstance(self.sip_status, Unset):
            sip_status = UNSET
        else:
            sip_status = self.sip_status

        fax_success: bool | None | Unset
        if isinstance(self.fax_success, Unset):
            fax_success = UNSET
        else:
            fax_success = self.fax_success

        fax_result_code: int | None | Unset
        if isinstance(self.fax_result_code, Unset):
            fax_result_code = UNSET
        else:
            fax_result_code = self.fax_result_code

        fax_result_text: None | str | Unset
        if isinstance(self.fax_result_text, Unset):
            fax_result_text = UNSET
        else:
            fax_result_text = self.fax_result_text

        pages_transferred: int | None | Unset
        if isinstance(self.pages_transferred, Unset):
            pages_transferred = UNSET
        else:
            pages_transferred = self.pages_transferred

        pages_total: int | None | Unset
        if isinstance(self.pages_total, Unset):
            pages_total = UNSET
        else:
            pages_total = self.pages_total

        transfer_rate: int | None | Unset
        if isinstance(self.transfer_rate, Unset):
            transfer_rate = UNSET
        else:
            transfer_rate = self.transfer_rate

        ecm_used: bool | None | Unset
        if isinstance(self.ecm_used, Unset):
            ecm_used = UNSET
        else:
            ecm_used = self.ecm_used

        t_38_used: bool | None | Unset
        if isinstance(self.t_38_used, Unset):
            t_38_used = UNSET
        else:
            t_38_used = self.t_38_used

        image_resolution: None | str | Unset
        if isinstance(self.image_resolution, Unset):
            image_resolution = UNSET
        else:
            image_resolution = self.image_resolution

        bad_rows: int | None | Unset
        if isinstance(self.bad_rows, Unset):
            bad_rows = UNSET
        else:
            bad_rows = self.bad_rows

        remote_station_id: None | str | Unset
        if isinstance(self.remote_station_id, Unset):
            remote_station_id = UNSET
        else:
            remote_station_id = self.remote_station_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if attempt_no is not UNSET:
            field_dict["attemptNo"] = attempt_no
        if transport_profile is not UNSET:
            field_dict["transportProfile"] = transport_profile
        if started_at is not UNSET:
            field_dict["startedAt"] = started_at
        if answered_at is not UNSET:
            field_dict["answeredAt"] = answered_at
        if ended_at is not UNSET:
            field_dict["endedAt"] = ended_at
        if billable_ms is not UNSET:
            field_dict["billableMs"] = billable_ms
        if hangup_cause is not UNSET:
            field_dict["hangupCause"] = hangup_cause
        if sip_status is not UNSET:
            field_dict["sipStatus"] = sip_status
        if fax_success is not UNSET:
            field_dict["faxSuccess"] = fax_success
        if fax_result_code is not UNSET:
            field_dict["faxResultCode"] = fax_result_code
        if fax_result_text is not UNSET:
            field_dict["faxResultText"] = fax_result_text
        if pages_transferred is not UNSET:
            field_dict["pagesTransferred"] = pages_transferred
        if pages_total is not UNSET:
            field_dict["pagesTotal"] = pages_total
        if transfer_rate is not UNSET:
            field_dict["transferRate"] = transfer_rate
        if ecm_used is not UNSET:
            field_dict["ecmUsed"] = ecm_used
        if t_38_used is not UNSET:
            field_dict["t38Used"] = t_38_used
        if image_resolution is not UNSET:
            field_dict["imageResolution"] = image_resolution
        if bad_rows is not UNSET:
            field_dict["badRows"] = bad_rows
        if remote_station_id is not UNSET:
            field_dict["remoteStationId"] = remote_station_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.fax_attempt_attributes_transport_profile_type_0 import (
            FaxAttemptAttributesTransportProfileType0,
        )

        d = dict(src_dict)

        def _parse_attempt_no(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        attempt_no = _parse_attempt_no(d.pop("attemptNo", UNSET))

        def _parse_transport_profile(
            data: object,
        ) -> FaxAttemptAttributesTransportProfileType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                transport_profile_type_0 = FaxAttemptAttributesTransportProfileType0.from_dict(data)

                return transport_profile_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(FaxAttemptAttributesTransportProfileType0 | None | Unset, data)

        transport_profile = _parse_transport_profile(d.pop("transportProfile", UNSET))

        def _parse_started_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                started_at_type_0 = datetime.datetime.fromisoformat(data)

                return started_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        started_at = _parse_started_at(d.pop("startedAt", UNSET))

        def _parse_answered_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                answered_at_type_0 = datetime.datetime.fromisoformat(data)

                return answered_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        answered_at = _parse_answered_at(d.pop("answeredAt", UNSET))

        def _parse_ended_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                ended_at_type_0 = datetime.datetime.fromisoformat(data)

                return ended_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        ended_at = _parse_ended_at(d.pop("endedAt", UNSET))

        def _parse_billable_ms(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        billable_ms = _parse_billable_ms(d.pop("billableMs", UNSET))

        def _parse_hangup_cause(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        hangup_cause = _parse_hangup_cause(d.pop("hangupCause", UNSET))

        def _parse_sip_status(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        sip_status = _parse_sip_status(d.pop("sipStatus", UNSET))

        def _parse_fax_success(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        fax_success = _parse_fax_success(d.pop("faxSuccess", UNSET))

        def _parse_fax_result_code(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        fax_result_code = _parse_fax_result_code(d.pop("faxResultCode", UNSET))

        def _parse_fax_result_text(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        fax_result_text = _parse_fax_result_text(d.pop("faxResultText", UNSET))

        def _parse_pages_transferred(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        pages_transferred = _parse_pages_transferred(d.pop("pagesTransferred", UNSET))

        def _parse_pages_total(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        pages_total = _parse_pages_total(d.pop("pagesTotal", UNSET))

        def _parse_transfer_rate(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        transfer_rate = _parse_transfer_rate(d.pop("transferRate", UNSET))

        def _parse_ecm_used(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        ecm_used = _parse_ecm_used(d.pop("ecmUsed", UNSET))

        def _parse_t_38_used(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        t_38_used = _parse_t_38_used(d.pop("t38Used", UNSET))

        def _parse_image_resolution(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        image_resolution = _parse_image_resolution(d.pop("imageResolution", UNSET))

        def _parse_bad_rows(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        bad_rows = _parse_bad_rows(d.pop("badRows", UNSET))

        def _parse_remote_station_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        remote_station_id = _parse_remote_station_id(d.pop("remoteStationId", UNSET))

        fax_attempt_attributes = cls(
            attempt_no=attempt_no,
            transport_profile=transport_profile,
            started_at=started_at,
            answered_at=answered_at,
            ended_at=ended_at,
            billable_ms=billable_ms,
            hangup_cause=hangup_cause,
            sip_status=sip_status,
            fax_success=fax_success,
            fax_result_code=fax_result_code,
            fax_result_text=fax_result_text,
            pages_transferred=pages_transferred,
            pages_total=pages_total,
            transfer_rate=transfer_rate,
            ecm_used=ecm_used,
            t_38_used=t_38_used,
            image_resolution=image_resolution,
            bad_rows=bad_rows,
            remote_station_id=remote_station_id,
        )

        fax_attempt_attributes.additional_properties = d
        return fax_attempt_attributes

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
