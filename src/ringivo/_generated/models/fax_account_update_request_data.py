from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.fax_account_update_request_data_type import FaxAccountUpdateRequestDataType

if TYPE_CHECKING:
    from ..models.fax_account_update_request_data_attributes import (
        FaxAccountUpdateRequestDataAttributes,
    )


T = TypeVar("T", bound="FaxAccountUpdateRequestData")


@_attrs_define
class FaxAccountUpdateRequestData:
    """
    Attributes:
        type_ (FaxAccountUpdateRequestDataType):
        id (UUID):
        attributes (FaxAccountUpdateRequestDataAttributes):
    """

    type_: FaxAccountUpdateRequestDataType
    id: UUID
    attributes: FaxAccountUpdateRequestDataAttributes
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        id = str(self.id)

        attributes = self.attributes.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "id": id,
                "attributes": attributes,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.fax_account_update_request_data_attributes import (
            FaxAccountUpdateRequestDataAttributes,
        )

        d = dict(src_dict)
        type_ = FaxAccountUpdateRequestDataType(d.pop("type"))

        id = UUID(d.pop("id"))

        attributes = FaxAccountUpdateRequestDataAttributes.from_dict(d.pop("attributes"))

        fax_account_update_request_data = cls(
            type_=type_,
            id=id,
            attributes=attributes,
        )

        fax_account_update_request_data.additional_properties = d
        return fax_account_update_request_data

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
