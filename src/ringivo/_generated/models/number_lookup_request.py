from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

T = TypeVar("T", bound="NumberLookupRequest")


@_attrs_define
class NumberLookupRequest:
    """
    Attributes:
        number (str): The number to look up. 10 digits, or 11 beginning with `1`; punctuation and spaces are
            ignored, so `(650) 253-0000` and `+16502530000` are the same request.
    """

    number: str

    def to_dict(self) -> dict[str, Any]:
        number = self.number

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "number": number,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        number = d.pop("number")

        number_lookup_request = cls(
            number=number,
        )

        return number_lookup_request
