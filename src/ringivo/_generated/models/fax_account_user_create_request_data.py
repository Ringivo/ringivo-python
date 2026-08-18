from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.fax_account_user_create_request_data_type import FaxAccountUserCreateRequestDataType

if TYPE_CHECKING:
    from ..models.fax_account_user_create_request_data_relationships import (
        FaxAccountUserCreateRequestDataRelationships,
    )


T = TypeVar("T", bound="FaxAccountUserCreateRequestData")


@_attrs_define
class FaxAccountUserCreateRequestData:
    """
    Attributes:
        type_ (FaxAccountUserCreateRequestDataType):
        relationships (FaxAccountUserCreateRequestDataRelationships):
    """

    type_: FaxAccountUserCreateRequestDataType
    relationships: FaxAccountUserCreateRequestDataRelationships
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        relationships = self.relationships.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "relationships": relationships,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.fax_account_user_create_request_data_relationships import (
            FaxAccountUserCreateRequestDataRelationships,
        )

        d = dict(src_dict)
        type_ = FaxAccountUserCreateRequestDataType(d.pop("type"))

        relationships = FaxAccountUserCreateRequestDataRelationships.from_dict(
            d.pop("relationships")
        )

        fax_account_user_create_request_data = cls(
            type_=type_,
            relationships=relationships,
        )

        fax_account_user_create_request_data.additional_properties = d
        return fax_account_user_create_request_data

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
