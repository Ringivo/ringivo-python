from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.fax_account_user_resource_type import FaxAccountUserResourceType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.fax_account_user_attributes import FaxAccountUserAttributes
    from ..models.fax_account_user_resource_relationships import FaxAccountUserResourceRelationships
    from ..models.resource_links import ResourceLinks
    from ..models.resource_meta import ResourceMeta


T = TypeVar("T", bound="FaxAccountUserResource")


@_attrs_define
class FaxAccountUserResource:
    """
    Attributes:
        type_ (FaxAccountUserResourceType):
        id (UUID):
        attributes (FaxAccountUserAttributes | Unset):
        relationships (FaxAccountUserResourceRelationships | Unset):
        links (ResourceLinks | Unset): Links belonging to one resource object.
        meta (ResourceMeta | Unset): Metadata belonging to one resource object.
    """

    type_: FaxAccountUserResourceType
    id: UUID
    attributes: FaxAccountUserAttributes | Unset = UNSET
    relationships: FaxAccountUserResourceRelationships | Unset = UNSET
    links: ResourceLinks | Unset = UNSET
    meta: ResourceMeta | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        id = str(self.id)

        attributes: dict[str, Any] | Unset = UNSET
        if not isinstance(self.attributes, Unset):
            attributes = self.attributes.to_dict()

        relationships: dict[str, Any] | Unset = UNSET
        if not isinstance(self.relationships, Unset):
            relationships = self.relationships.to_dict()

        links: dict[str, Any] | Unset = UNSET
        if not isinstance(self.links, Unset):
            links = self.links.to_dict()

        meta: dict[str, Any] | Unset = UNSET
        if not isinstance(self.meta, Unset):
            meta = self.meta.to_dict()

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
        if relationships is not UNSET:
            field_dict["relationships"] = relationships
        if links is not UNSET:
            field_dict["links"] = links
        if meta is not UNSET:
            field_dict["meta"] = meta

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.fax_account_user_attributes import FaxAccountUserAttributes
        from ..models.fax_account_user_resource_relationships import (
            FaxAccountUserResourceRelationships,
        )
        from ..models.resource_links import ResourceLinks
        from ..models.resource_meta import ResourceMeta

        d = dict(src_dict)
        type_ = FaxAccountUserResourceType(d.pop("type"))

        id = UUID(d.pop("id"))

        _attributes = d.pop("attributes", UNSET)
        attributes: FaxAccountUserAttributes | Unset
        if isinstance(_attributes, Unset):
            attributes = UNSET
        else:
            attributes = FaxAccountUserAttributes.from_dict(_attributes)

        _relationships = d.pop("relationships", UNSET)
        relationships: FaxAccountUserResourceRelationships | Unset
        if isinstance(_relationships, Unset):
            relationships = UNSET
        else:
            relationships = FaxAccountUserResourceRelationships.from_dict(_relationships)

        _links = d.pop("links", UNSET)
        links: ResourceLinks | Unset
        if isinstance(_links, Unset):
            links = UNSET
        else:
            links = ResourceLinks.from_dict(_links)

        _meta = d.pop("meta", UNSET)
        meta: ResourceMeta | Unset
        if isinstance(_meta, Unset):
            meta = UNSET
        else:
            meta = ResourceMeta.from_dict(_meta)

        fax_account_user_resource = cls(
            type_=type_,
            id=id,
            attributes=attributes,
            relationships=relationships,
            links=links,
            meta=meta,
        )

        fax_account_user_resource.additional_properties = d
        return fax_account_user_resource

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
