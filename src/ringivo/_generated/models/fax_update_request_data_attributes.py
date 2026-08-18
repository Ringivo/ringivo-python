from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.tags_type_0 import TagsType0


T = TypeVar("T", bound="FaxUpdateRequestDataAttributes")


@_attrs_define
class FaxUpdateRequestDataAttributes:
    """Only `read`, `archived` and `tags` may CHANGE. Any other attribute may be echoed back
    with its current value, and is a 422 with a different one.

        Attributes:
            read (bool | Unset):
            archived (bool | Unset):
            tags (None | TagsType0 | Unset): A flat map of short labels you own — the only filing system there is. Replaced
                wholesale on
                a write, never merged.
    """

    read: bool | Unset = UNSET
    archived: bool | Unset = UNSET
    tags: None | TagsType0 | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.tags_type_0 import TagsType0

        read = self.read

        archived = self.archived

        tags: dict[str, Any] | None | Unset
        if isinstance(self.tags, Unset):
            tags = UNSET
        elif isinstance(self.tags, TagsType0):
            tags = self.tags.to_dict()
        else:
            tags = self.tags

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if read is not UNSET:
            field_dict["read"] = read
        if archived is not UNSET:
            field_dict["archived"] = archived
        if tags is not UNSET:
            field_dict["tags"] = tags

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.tags_type_0 import TagsType0

        d = dict(src_dict)
        read = d.pop("read", UNSET)

        archived = d.pop("archived", UNSET)

        def _parse_tags(data: object) -> None | TagsType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_tags_type_0 = TagsType0.from_dict(data)

                return componentsschemas_tags_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | TagsType0 | Unset, data)

        tags = _parse_tags(d.pop("tags", UNSET))

        fax_update_request_data_attributes = cls(
            read=read,
            archived=archived,
            tags=tags,
        )

        fax_update_request_data_attributes.additional_properties = d
        return fax_update_request_data_attributes

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
