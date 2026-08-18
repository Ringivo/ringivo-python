from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="CollectionLinks")


@_attrs_define
class CollectionLinks:
    """Pagination links. `next` is the one to follow on a cursor-paginated collection; it is absent
    or null on the last page.

        Attributes:
            self_ (None | str | Unset):
            first (None | str | Unset):
            last (None | str | Unset):
            prev (None | str | Unset):
            next_ (None | str | Unset):
    """

    self_: None | str | Unset = UNSET
    first: None | str | Unset = UNSET
    last: None | str | Unset = UNSET
    prev: None | str | Unset = UNSET
    next_: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        self_: None | str | Unset
        if isinstance(self.self_, Unset):
            self_ = UNSET
        else:
            self_ = self.self_

        first: None | str | Unset
        if isinstance(self.first, Unset):
            first = UNSET
        else:
            first = self.first

        last: None | str | Unset
        if isinstance(self.last, Unset):
            last = UNSET
        else:
            last = self.last

        prev: None | str | Unset
        if isinstance(self.prev, Unset):
            prev = UNSET
        else:
            prev = self.prev

        next_: None | str | Unset
        if isinstance(self.next_, Unset):
            next_ = UNSET
        else:
            next_ = self.next_

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if self_ is not UNSET:
            field_dict["self"] = self_
        if first is not UNSET:
            field_dict["first"] = first
        if last is not UNSET:
            field_dict["last"] = last
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

        def _parse_first(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        first = _parse_first(d.pop("first", UNSET))

        def _parse_last(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        last = _parse_last(d.pop("last", UNSET))

        def _parse_prev(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        prev = _parse_prev(d.pop("prev", UNSET))

        def _parse_next_(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        next_ = _parse_next_(d.pop("next", UNSET))

        collection_links = cls(
            self_=self_,
            first=first,
            last=last,
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
