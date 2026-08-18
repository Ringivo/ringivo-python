from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.fax_direction import FaxDirection
from ..models.fax_status import FaxStatus
from ..types import UNSET, Unset

T = TypeVar("T", bound="SendFaxAcceptedData")


@_attrs_define
class SendFaxAcceptedData:
    """
    Attributes:
        id (UUID | Unset):
        status (FaxStatus | Unset): `queued`, `converting`, `sending`, `delivered`, `partial` and `cancelled` belong to
            an
            outbound fax; `received` to an inbound one; `failed` to both.
        direction (FaxDirection | Unset):
        from_ (None | str | Unset):
        to (None | str | Unset):
        client_reference (None | str | Unset):
        created_at (datetime.datetime | None | Unset):
    """

    id: UUID | Unset = UNSET
    status: FaxStatus | Unset = UNSET
    direction: FaxDirection | Unset = UNSET
    from_: None | str | Unset = UNSET
    to: None | str | Unset = UNSET
    client_reference: None | str | Unset = UNSET
    created_at: datetime.datetime | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id: str | Unset = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        status: str | Unset = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.value

        direction: str | Unset = UNSET
        if not isinstance(self.direction, Unset):
            direction = self.direction.value

        from_: None | str | Unset
        if isinstance(self.from_, Unset):
            from_ = UNSET
        else:
            from_ = self.from_

        to: None | str | Unset
        if isinstance(self.to, Unset):
            to = UNSET
        else:
            to = self.to

        client_reference: None | str | Unset
        if isinstance(self.client_reference, Unset):
            client_reference = UNSET
        else:
            client_reference = self.client_reference

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        elif isinstance(self.created_at, datetime.datetime):
            created_at = self.created_at.isoformat()
        else:
            created_at = self.created_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if status is not UNSET:
            field_dict["status"] = status
        if direction is not UNSET:
            field_dict["direction"] = direction
        if from_ is not UNSET:
            field_dict["from"] = from_
        if to is not UNSET:
            field_dict["to"] = to
        if client_reference is not UNSET:
            field_dict["client_reference"] = client_reference
        if created_at is not UNSET:
            field_dict["created_at"] = created_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        _id = d.pop("id", UNSET)
        id: UUID | Unset
        if isinstance(_id, Unset):
            id = UNSET
        else:
            id = UUID(_id)

        _status = d.pop("status", UNSET)
        status: FaxStatus | Unset
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = FaxStatus(_status)

        _direction = d.pop("direction", UNSET)
        direction: FaxDirection | Unset
        if isinstance(_direction, Unset):
            direction = UNSET
        else:
            direction = FaxDirection(_direction)

        def _parse_from_(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        from_ = _parse_from_(d.pop("from", UNSET))

        def _parse_to(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        to = _parse_to(d.pop("to", UNSET))

        def _parse_client_reference(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        client_reference = _parse_client_reference(d.pop("client_reference", UNSET))

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

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        send_fax_accepted_data = cls(
            id=id,
            status=status,
            direction=direction,
            from_=from_,
            to=to,
            client_reference=client_reference,
            created_at=created_at,
        )

        send_fax_accepted_data.additional_properties = d
        return send_fax_accepted_data

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
