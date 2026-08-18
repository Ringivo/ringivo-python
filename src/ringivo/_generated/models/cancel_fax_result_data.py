from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.fax_status import FaxStatus
from ..types import UNSET, Unset

T = TypeVar("T", bound="CancelFaxResultData")


@_attrs_define
class CancelFaxResultData:
    """
    Attributes:
        id (UUID | Unset):
        status (FaxStatus | Unset): `queued`, `converting`, `sending`, `delivered`, `partial` and `cancelled` belong to
            an
            outbound fax; `received` to an inbound one; `failed` to both.
    """

    id: UUID | Unset = UNSET
    status: FaxStatus | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id: str | Unset = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        status: str | Unset = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if status is not UNSET:
            field_dict["status"] = status

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

        cancel_fax_result_data = cls(
            id=id,
            status=status,
        )

        cancel_fax_result_data.additional_properties = d
        return cancel_fax_result_data

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
