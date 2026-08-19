from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ResourceMetaPage")


@_attrs_define
class ResourceMetaPage:
    """This row's own place in the collection that served it. Present on the members of a
    paginated collection, and absent everywhere else — a single-resource read and a
    side-loaded `included` row were never positions in a walk.

        Attributes:
            cursor (str | Unset): An opaque cursor for THIS row. Send it as `page[after]` for the rows after it or as
                `page[before]` for the rows before it, under the same `filter` and `sort`.
    """

    cursor: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        cursor = self.cursor

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if cursor is not UNSET:
            field_dict["cursor"] = cursor

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        cursor = d.pop("cursor", UNSET)

        resource_meta_page = cls(
            cursor=cursor,
        )

        resource_meta_page.additional_properties = d
        return resource_meta_page

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
