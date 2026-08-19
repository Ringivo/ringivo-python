from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PageMeta")


@_attrs_define
class PageMeta:
    """Where this page sits in the collection it came from.

    Attributes:
        size (int): The number of rows a full page holds for this request.
        next_cursor (None | str): Send this back as `page[after]` for the page that follows. `null` on the final page —
            the end-of-feed signal.
        total (int | Unset): The exact number of rows the collection holds under the filters applied, repeated on
            every page of the walk. Present on SOME collections only, so read it as optional: of the
            collections documented here `fax-accounts`, `fax-account-users` and `webhook-endpoints`
            publish it, and `faxes` and `webhook-deliveries` never do. Counting a table that only
            grows costs more with every row, which is the price a cursor walk exists to not pay.
    """

    size: int
    next_cursor: None | str
    total: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        size = self.size

        next_cursor: None | str
        next_cursor = self.next_cursor

        total = self.total

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "size": size,
                "nextCursor": next_cursor,
            }
        )
        if total is not UNSET:
            field_dict["total"] = total

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        size = d.pop("size")

        def _parse_next_cursor(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        next_cursor = _parse_next_cursor(d.pop("nextCursor"))

        total = d.pop("total", UNSET)

        page_meta = cls(
            size=size,
            next_cursor=next_cursor,
            total=total,
        )

        page_meta.additional_properties = d
        return page_meta

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
