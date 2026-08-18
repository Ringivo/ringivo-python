from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.webhook_delivery_status import WebhookDeliveryStatus
from ..models.webhook_event_type import WebhookEventType
from ..types import UNSET, Unset

T = TypeVar("T", bound="WebhookDeliveryAttributes")


@_attrs_define
class WebhookDeliveryAttributes:
    """
    Attributes:
        event_id (None | str | Unset): The dedupe key. A retried delivery of the same event carries the same id.
        event_type (WebhookEventType | Unset): Every event name a subscriber may ask for.
        payload_sha_256 (None | str | Unset): The digest of the exact bytes we signed. The body itself is never
            published here.
        status (WebhookDeliveryStatus | Unset): Derived, not stored. `pending` is still on the retry ladder; `dead` ran
            out of rungs and is
            what an outage costs you.
        attempt_no (int | None | Unset): How many POSTs have been made, not how many failed.
        status_code (int | None | Unset): What your server answered. Null when we never reached it.
        duration_ms (int | None | Unset):
        error (None | str | Unset): Why we could not reach you, when that is the reason.
        next_attempt_at (datetime.datetime | None | Unset):
        delivered_at (datetime.datetime | None | Unset):
        dead_at (datetime.datetime | None | Unset):
        created_at (datetime.datetime | None | Unset):
        updated_at (datetime.datetime | None | Unset):
    """

    event_id: None | str | Unset = UNSET
    event_type: WebhookEventType | Unset = UNSET
    payload_sha_256: None | str | Unset = UNSET
    status: WebhookDeliveryStatus | Unset = UNSET
    attempt_no: int | None | Unset = UNSET
    status_code: int | None | Unset = UNSET
    duration_ms: int | None | Unset = UNSET
    error: None | str | Unset = UNSET
    next_attempt_at: datetime.datetime | None | Unset = UNSET
    delivered_at: datetime.datetime | None | Unset = UNSET
    dead_at: datetime.datetime | None | Unset = UNSET
    created_at: datetime.datetime | None | Unset = UNSET
    updated_at: datetime.datetime | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        event_id: None | str | Unset
        if isinstance(self.event_id, Unset):
            event_id = UNSET
        else:
            event_id = self.event_id

        event_type: str | Unset = UNSET
        if not isinstance(self.event_type, Unset):
            event_type = self.event_type.value

        payload_sha_256: None | str | Unset
        if isinstance(self.payload_sha_256, Unset):
            payload_sha_256 = UNSET
        else:
            payload_sha_256 = self.payload_sha_256

        status: str | Unset = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.value

        attempt_no: int | None | Unset
        if isinstance(self.attempt_no, Unset):
            attempt_no = UNSET
        else:
            attempt_no = self.attempt_no

        status_code: int | None | Unset
        if isinstance(self.status_code, Unset):
            status_code = UNSET
        else:
            status_code = self.status_code

        duration_ms: int | None | Unset
        if isinstance(self.duration_ms, Unset):
            duration_ms = UNSET
        else:
            duration_ms = self.duration_ms

        error: None | str | Unset
        if isinstance(self.error, Unset):
            error = UNSET
        else:
            error = self.error

        next_attempt_at: None | str | Unset
        if isinstance(self.next_attempt_at, Unset):
            next_attempt_at = UNSET
        elif isinstance(self.next_attempt_at, datetime.datetime):
            next_attempt_at = self.next_attempt_at.isoformat()
        else:
            next_attempt_at = self.next_attempt_at

        delivered_at: None | str | Unset
        if isinstance(self.delivered_at, Unset):
            delivered_at = UNSET
        elif isinstance(self.delivered_at, datetime.datetime):
            delivered_at = self.delivered_at.isoformat()
        else:
            delivered_at = self.delivered_at

        dead_at: None | str | Unset
        if isinstance(self.dead_at, Unset):
            dead_at = UNSET
        elif isinstance(self.dead_at, datetime.datetime):
            dead_at = self.dead_at.isoformat()
        else:
            dead_at = self.dead_at

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        elif isinstance(self.created_at, datetime.datetime):
            created_at = self.created_at.isoformat()
        else:
            created_at = self.created_at

        updated_at: None | str | Unset
        if isinstance(self.updated_at, Unset):
            updated_at = UNSET
        elif isinstance(self.updated_at, datetime.datetime):
            updated_at = self.updated_at.isoformat()
        else:
            updated_at = self.updated_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if event_id is not UNSET:
            field_dict["eventId"] = event_id
        if event_type is not UNSET:
            field_dict["eventType"] = event_type
        if payload_sha_256 is not UNSET:
            field_dict["payloadSha256"] = payload_sha_256
        if status is not UNSET:
            field_dict["status"] = status
        if attempt_no is not UNSET:
            field_dict["attemptNo"] = attempt_no
        if status_code is not UNSET:
            field_dict["statusCode"] = status_code
        if duration_ms is not UNSET:
            field_dict["durationMs"] = duration_ms
        if error is not UNSET:
            field_dict["error"] = error
        if next_attempt_at is not UNSET:
            field_dict["nextAttemptAt"] = next_attempt_at
        if delivered_at is not UNSET:
            field_dict["deliveredAt"] = delivered_at
        if dead_at is not UNSET:
            field_dict["deadAt"] = dead_at
        if created_at is not UNSET:
            field_dict["createdAt"] = created_at
        if updated_at is not UNSET:
            field_dict["updatedAt"] = updated_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_event_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        event_id = _parse_event_id(d.pop("eventId", UNSET))

        _event_type = d.pop("eventType", UNSET)
        event_type: WebhookEventType | Unset
        if isinstance(_event_type, Unset):
            event_type = UNSET
        else:
            event_type = WebhookEventType(_event_type)

        def _parse_payload_sha_256(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        payload_sha_256 = _parse_payload_sha_256(d.pop("payloadSha256", UNSET))

        _status = d.pop("status", UNSET)
        status: WebhookDeliveryStatus | Unset
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = WebhookDeliveryStatus(_status)

        def _parse_attempt_no(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        attempt_no = _parse_attempt_no(d.pop("attemptNo", UNSET))

        def _parse_status_code(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        status_code = _parse_status_code(d.pop("statusCode", UNSET))

        def _parse_duration_ms(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        duration_ms = _parse_duration_ms(d.pop("durationMs", UNSET))

        def _parse_error(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        error = _parse_error(d.pop("error", UNSET))

        def _parse_next_attempt_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                next_attempt_at_type_0 = datetime.datetime.fromisoformat(data)

                return next_attempt_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        next_attempt_at = _parse_next_attempt_at(d.pop("nextAttemptAt", UNSET))

        def _parse_delivered_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                delivered_at_type_0 = datetime.datetime.fromisoformat(data)

                return delivered_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        delivered_at = _parse_delivered_at(d.pop("deliveredAt", UNSET))

        def _parse_dead_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                dead_at_type_0 = datetime.datetime.fromisoformat(data)

                return dead_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        dead_at = _parse_dead_at(d.pop("deadAt", UNSET))

        def _parse_created_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                created_at_type_0 = datetime.datetime.fromisoformat(data)

                return created_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        created_at = _parse_created_at(d.pop("createdAt", UNSET))

        def _parse_updated_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                updated_at_type_0 = datetime.datetime.fromisoformat(data)

                return updated_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        updated_at = _parse_updated_at(d.pop("updatedAt", UNSET))

        webhook_delivery_attributes = cls(
            event_id=event_id,
            event_type=event_type,
            payload_sha_256=payload_sha_256,
            status=status,
            attempt_no=attempt_no,
            status_code=status_code,
            duration_ms=duration_ms,
            error=error,
            next_attempt_at=next_attempt_at,
            delivered_at=delivered_at,
            dead_at=dead_at,
            created_at=created_at,
            updated_at=updated_at,
        )

        webhook_delivery_attributes.additional_properties = d
        return webhook_delivery_attributes

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
