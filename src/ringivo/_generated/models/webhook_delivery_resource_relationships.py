from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.relationship_to_one import RelationshipToOne


T = TypeVar("T", bound="WebhookDeliveryResourceRelationships")


@_attrs_define
class WebhookDeliveryResourceRelationships:
    """
    Attributes:
        endpoint (RelationshipToOne | Unset): A to-one relationship. `data` is present only when the relationship was
            resolved — a plain
            read that included nothing gives `links` alone.
    """

    endpoint: RelationshipToOne | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        endpoint: dict[str, Any] | Unset = UNSET
        if not isinstance(self.endpoint, Unset):
            endpoint = self.endpoint.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if endpoint is not UNSET:
            field_dict["endpoint"] = endpoint

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.relationship_to_one import RelationshipToOne

        d = dict(src_dict)
        _endpoint = d.pop("endpoint", UNSET)
        endpoint: RelationshipToOne | Unset
        if isinstance(_endpoint, Unset):
            endpoint = UNSET
        else:
            endpoint = RelationshipToOne.from_dict(_endpoint)

        webhook_delivery_resource_relationships = cls(
            endpoint=endpoint,
        )

        webhook_delivery_resource_relationships.additional_properties = d
        return webhook_delivery_resource_relationships

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
