from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.resource_identifier import ResourceIdentifier
    from ..models.resource_links import ResourceLinks


T = TypeVar("T", bound="RelationshipToMany")


@_attrs_define
class RelationshipToMany:
    """A to-many relationship.

    Attributes:
        links (ResourceLinks | Unset): Links belonging to one resource object.
        data (list[ResourceIdentifier] | Unset):
    """

    links: ResourceLinks | Unset = UNSET
    data: list[ResourceIdentifier] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        links: dict[str, Any] | Unset = UNSET
        if not isinstance(self.links, Unset):
            links = self.links.to_dict()

        data: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.data, Unset):
            data = []
            for data_item_data in self.data:
                data_item = data_item_data.to_dict()
                data.append(data_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if links is not UNSET:
            field_dict["links"] = links
        if data is not UNSET:
            field_dict["data"] = data

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.resource_identifier import ResourceIdentifier
        from ..models.resource_links import ResourceLinks

        d = dict(src_dict)
        _links = d.pop("links", UNSET)
        links: ResourceLinks | Unset
        if isinstance(_links, Unset):
            links = UNSET
        else:
            links = ResourceLinks.from_dict(_links)

        _data = d.pop("data", UNSET)
        data: list[ResourceIdentifier] | Unset = UNSET
        if _data is not UNSET:
            data = []
            for data_item_data in _data:
                data_item = ResourceIdentifier.from_dict(data_item_data)

                data.append(data_item)

        relationship_to_many = cls(
            links=links,
            data=data,
        )

        relationship_to_many.additional_properties = d
        return relationship_to_many

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
