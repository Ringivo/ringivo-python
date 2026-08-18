from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.relationship_to_many import RelationshipToMany
    from ..models.relationship_to_one import RelationshipToOne


T = TypeVar("T", bound="FaxAccountRelationships")


@_attrs_define
class FaxAccountRelationships:
    """
    Attributes:
        customer (RelationshipToOne | Unset): A to-one relationship. `data` is present only when the relationship was
            resolved — a plain
            read that included nothing gives `links` alone.
        numbers (RelationshipToMany | Unset): A to-many relationship.
    """

    customer: RelationshipToOne | Unset = UNSET
    numbers: RelationshipToMany | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        customer: dict[str, Any] | Unset = UNSET
        if not isinstance(self.customer, Unset):
            customer = self.customer.to_dict()

        numbers: dict[str, Any] | Unset = UNSET
        if not isinstance(self.numbers, Unset):
            numbers = self.numbers.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if customer is not UNSET:
            field_dict["customer"] = customer
        if numbers is not UNSET:
            field_dict["numbers"] = numbers

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.relationship_to_many import RelationshipToMany
        from ..models.relationship_to_one import RelationshipToOne

        d = dict(src_dict)
        _customer = d.pop("customer", UNSET)
        customer: RelationshipToOne | Unset
        if isinstance(_customer, Unset):
            customer = UNSET
        else:
            customer = RelationshipToOne.from_dict(_customer)

        _numbers = d.pop("numbers", UNSET)
        numbers: RelationshipToMany | Unset
        if isinstance(_numbers, Unset):
            numbers = UNSET
        else:
            numbers = RelationshipToMany.from_dict(_numbers)

        fax_account_relationships = cls(
            customer=customer,
            numbers=numbers,
        )

        fax_account_relationships.additional_properties = d
        return fax_account_relationships

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
