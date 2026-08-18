from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.resource_identifier import ResourceIdentifier
    from ..models.resource_links import ResourceLinks


T = TypeVar("T", bound="RelationshipToOne")


@_attrs_define
class RelationshipToOne:
    """A to-one relationship. `data` is present only when the relationship was resolved — a plain
    read that included nothing gives `links` alone.

        Attributes:
            links (ResourceLinks | Unset): Links belonging to one resource object.
            data (None | ResourceIdentifier | Unset):
    """

    links: ResourceLinks | Unset = UNSET
    data: None | ResourceIdentifier | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.resource_identifier import ResourceIdentifier

        links: dict[str, Any] | Unset = UNSET
        if not isinstance(self.links, Unset):
            links = self.links.to_dict()

        data: dict[str, Any] | None | Unset
        if isinstance(self.data, Unset):
            data = UNSET
        elif isinstance(self.data, ResourceIdentifier):
            data = self.data.to_dict()
        else:
            data = self.data

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

        def _parse_data(data: object) -> None | ResourceIdentifier | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                data_type_0 = ResourceIdentifier.from_dict(data)

                return data_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | ResourceIdentifier | Unset, data)

        data = _parse_data(d.pop("data", UNSET))

        relationship_to_one = cls(
            links=links,
            data=data,
        )

        relationship_to_one.additional_properties = d
        return relationship_to_one

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
