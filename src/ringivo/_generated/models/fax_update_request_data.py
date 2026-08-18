from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.fax_update_request_data_type import FaxUpdateRequestDataType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.fax_update_request_data_attributes import FaxUpdateRequestDataAttributes


T = TypeVar("T", bound="FaxUpdateRequestData")


@_attrs_define
class FaxUpdateRequestData:
    """
    Attributes:
        type_ (FaxUpdateRequestDataType):
        id (UUID):
        attributes (FaxUpdateRequestDataAttributes | Unset): Only `read`, `archived` and `tags` may CHANGE. Any other
            attribute may be echoed back
            with its current value, and is a 422 with a different one.
    """

    type_: FaxUpdateRequestDataType
    id: UUID
    attributes: FaxUpdateRequestDataAttributes | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        id = str(self.id)

        attributes: dict[str, Any] | Unset = UNSET
        if not isinstance(self.attributes, Unset):
            attributes = self.attributes.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "id": id,
            }
        )
        if attributes is not UNSET:
            field_dict["attributes"] = attributes

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.fax_update_request_data_attributes import FaxUpdateRequestDataAttributes

        d = dict(src_dict)
        type_ = FaxUpdateRequestDataType(d.pop("type"))

        id = UUID(d.pop("id"))

        _attributes = d.pop("attributes", UNSET)
        attributes: FaxUpdateRequestDataAttributes | Unset
        if isinstance(_attributes, Unset):
            attributes = UNSET
        else:
            attributes = FaxUpdateRequestDataAttributes.from_dict(_attributes)

        fax_update_request_data = cls(
            type_=type_,
            id=id,
            attributes=attributes,
        )

        fax_update_request_data.additional_properties = d
        return fax_update_request_data

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
