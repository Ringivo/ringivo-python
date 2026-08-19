from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.resource_meta_page import ResourceMetaPage


T = TypeVar("T", bound="ResourceMeta")


@_attrs_define
class ResourceMeta:
    """Metadata belonging to one resource object.

    Attributes:
        page (ResourceMetaPage | Unset): This row's own place in the collection that served it. Present on the members
            of a
            paginated collection, and absent everywhere else — a single-resource read and a
            side-loaded `included` row were never positions in a walk.
    """

    page: ResourceMetaPage | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        page: dict[str, Any] | Unset = UNSET
        if not isinstance(self.page, Unset):
            page = self.page.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if page is not UNSET:
            field_dict["page"] = page

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.resource_meta_page import ResourceMetaPage

        d = dict(src_dict)
        _page = d.pop("page", UNSET)
        page: ResourceMetaPage | Unset
        if isinstance(_page, Unset):
            page = UNSET
        else:
            page = ResourceMetaPage.from_dict(_page)

        resource_meta = cls(
            page=page,
        )

        resource_meta.additional_properties = d
        return resource_meta

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
