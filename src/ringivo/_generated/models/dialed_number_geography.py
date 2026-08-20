from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="DialedNumberGeography")


@_attrs_define
class DialedNumberGeography:
    """Where the number you asked about is nominally from, from our own copy of LERG. **Not the
    LRN's** rate center, which is a different fact and lives under `components.lrn`.

        Attributes:
            rate_center (None | str): Null for a toll-free number, which has no rate center. Absent, not missing.
            state (None | str): Two-letter state or province code. Null for a toll-free number.
    """

    rate_center: None | str
    state: None | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        rate_center: None | str
        rate_center = self.rate_center

        state: None | str
        state = self.state

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "rateCenter": rate_center,
                "state": state,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_rate_center(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        rate_center = _parse_rate_center(d.pop("rateCenter"))

        def _parse_state(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        state = _parse_state(d.pop("state"))

        dialed_number_geography = cls(
            rate_center=rate_center,
            state=state,
        )

        dialed_number_geography.additional_properties = d
        return dialed_number_geography

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
