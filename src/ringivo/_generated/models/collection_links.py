from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="CollectionLinks")


@_attrs_define
class CollectionLinks:
    """Pagination links. `first` is always present, `prev` whenever a previous page exists, and
    `next` on every page but the last — on the final page `next` is ABSENT from the document
    altogether. Branch on `meta.page.nextCursor` instead: it is `null` at the end and present on
    every page, so one member answers "is there more?" everywhere. There is no `last` link.

    A link that does not apply is ABSENT rather than null — the encoder cannot carry a null
    href — so these three are plain strings whenever they appear at all.

        Attributes:
            self_ (None | str | Unset):
            first (str | Unset):
            prev (str | Unset):
            next_ (str | Unset):
    """

    self_: None | str | Unset = UNSET
    first: str | Unset = UNSET
    prev: str | Unset = UNSET
    next_: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        self_: None | str | Unset
        if isinstance(self.self_, Unset):
            self_ = UNSET
        else:
            self_ = self.self_

        first = self.first

        prev = self.prev

        next_ = self.next_

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if self_ is not UNSET:
            field_dict["self"] = self_
        if first is not UNSET:
            field_dict["first"] = first
        if prev is not UNSET:
            field_dict["prev"] = prev
        if next_ is not UNSET:
            field_dict["next"] = next_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_self_(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        self_ = _parse_self_(d.pop("self", UNSET))

        first = d.pop("first", UNSET)

        prev = d.pop("prev", UNSET)

        next_ = d.pop("next", UNSET)

        collection_links = cls(
            self_=self_,
            first=first,
            prev=prev,
            next_=next_,
        )

        collection_links.additional_properties = d
        return collection_links

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
