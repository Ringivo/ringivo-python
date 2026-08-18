from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.relationship_to_one import RelationshipToOne


T = TypeVar("T", bound="PhoneNumberResourceRelationships")


@_attrs_define
class PhoneNumberResourceRelationships:
    """
    Attributes:
        customer (RelationshipToOne | Unset): A to-one relationship. `data` is present only when the relationship was
            resolved — a plain
            read that included nothing gives `links` alone.
        routing_target (RelationshipToOne | Unset): A to-one relationship. `data` is present only when the relationship
            was resolved — a plain
            read that included nothing gives `links` alone.
        pbx_number (RelationshipToOne | Unset): A to-one relationship. `data` is present only when the relationship was
            resolved — a plain
            read that included nothing gives `links` alone.
    """

    customer: RelationshipToOne | Unset = UNSET
    routing_target: RelationshipToOne | Unset = UNSET
    pbx_number: RelationshipToOne | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        customer: dict[str, Any] | Unset = UNSET
        if not isinstance(self.customer, Unset):
            customer = self.customer.to_dict()

        routing_target: dict[str, Any] | Unset = UNSET
        if not isinstance(self.routing_target, Unset):
            routing_target = self.routing_target.to_dict()

        pbx_number: dict[str, Any] | Unset = UNSET
        if not isinstance(self.pbx_number, Unset):
            pbx_number = self.pbx_number.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if customer is not UNSET:
            field_dict["customer"] = customer
        if routing_target is not UNSET:
            field_dict["routingTarget"] = routing_target
        if pbx_number is not UNSET:
            field_dict["pbxNumber"] = pbx_number

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.relationship_to_one import RelationshipToOne

        d = dict(src_dict)
        _customer = d.pop("customer", UNSET)
        customer: RelationshipToOne | Unset
        if isinstance(_customer, Unset):
            customer = UNSET
        else:
            customer = RelationshipToOne.from_dict(_customer)

        _routing_target = d.pop("routingTarget", UNSET)
        routing_target: RelationshipToOne | Unset
        if isinstance(_routing_target, Unset):
            routing_target = UNSET
        else:
            routing_target = RelationshipToOne.from_dict(_routing_target)

        _pbx_number = d.pop("pbxNumber", UNSET)
        pbx_number: RelationshipToOne | Unset
        if isinstance(_pbx_number, Unset):
            pbx_number = UNSET
        else:
            pbx_number = RelationshipToOne.from_dict(_pbx_number)

        phone_number_resource_relationships = cls(
            customer=customer,
            routing_target=routing_target,
            pbx_number=pbx_number,
        )

        phone_number_resource_relationships.additional_properties = d
        return phone_number_resource_relationships

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
