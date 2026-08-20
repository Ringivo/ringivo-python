from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.dialed_number_geography import DialedNumberGeography
    from ..models.number_lookup_components import NumberLookupComponents


T = TypeVar("T", bound="NumberLookup")


@_attrs_define
class NumberLookup:
    """
    Attributes:
        number (str): The number that was looked up, normalized to E.164.
        looked_up_at (datetime.datetime): When the components ran — so you can tell "we asked and learned nothing" from
            "we never
            asked".
        charged (bool): Whether this lookup was billed. True when any component answered; false only when every
            one of them failed.
        dialed_number (DialedNumberGeography): Where the number you asked about is nominally from, from our own copy of
            LERG. **Not the
            LRN's** rate center, which is a different fact and lives under `components.lrn`.
        components (NumberLookupComponents): The three paid components. Each reports its own outcome and they fail
            independently — a
            lookup with two answers and one failure is normal, and is billed in full.
    """

    number: str
    looked_up_at: datetime.datetime
    charged: bool
    dialed_number: DialedNumberGeography
    components: NumberLookupComponents
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        number = self.number

        looked_up_at = self.looked_up_at.isoformat()

        charged = self.charged

        dialed_number = self.dialed_number.to_dict()

        components = self.components.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "number": number,
                "lookedUpAt": looked_up_at,
                "charged": charged,
                "dialedNumber": dialed_number,
                "components": components,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.dialed_number_geography import DialedNumberGeography
        from ..models.number_lookup_components import NumberLookupComponents

        d = dict(src_dict)
        number = d.pop("number")

        looked_up_at = datetime.datetime.fromisoformat(d.pop("lookedUpAt"))

        charged = d.pop("charged")

        dialed_number = DialedNumberGeography.from_dict(d.pop("dialedNumber"))

        components = NumberLookupComponents.from_dict(d.pop("components"))

        number_lookup = cls(
            number=number,
            looked_up_at=looked_up_at,
            charged=charged,
            dialed_number=dialed_number,
            components=components,
        )

        number_lookup.additional_properties = d
        return number_lookup

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
