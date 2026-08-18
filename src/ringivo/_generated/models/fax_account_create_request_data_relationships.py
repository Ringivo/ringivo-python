from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.fax_account_create_request_data_relationships_customer import (
        FaxAccountCreateRequestDataRelationshipsCustomer,
    )


T = TypeVar("T", bound="FaxAccountCreateRequestDataRelationships")


@_attrs_define
class FaxAccountCreateRequestDataRelationships:
    """
    Attributes:
        customer (FaxAccountCreateRequestDataRelationshipsCustomer):
    """

    customer: FaxAccountCreateRequestDataRelationshipsCustomer
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        customer = self.customer.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "customer": customer,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.fax_account_create_request_data_relationships_customer import (
            FaxAccountCreateRequestDataRelationshipsCustomer,
        )

        d = dict(src_dict)
        customer = FaxAccountCreateRequestDataRelationshipsCustomer.from_dict(d.pop("customer"))

        fax_account_create_request_data_relationships = cls(
            customer=customer,
        )

        fax_account_create_request_data_relationships.additional_properties = d
        return fax_account_create_request_data_relationships

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
