from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="MessagingFacts")


@_attrs_define
class MessagingFacts:
    """Whether the number can carry text messages, and who carries them.

    Attributes:
        enabled (bool): Whether the number is enabled for messaging. **`false` means it cannot receive messages**
            — it never means "we do not know", which arrives as `status: no_data` with this whole
            object null.
        provider (None | str): The messaging carrier's name.
        country (None | str):
        country_code (None | str):
    """

    enabled: bool
    provider: None | str
    country: None | str
    country_code: None | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        enabled = self.enabled

        provider: None | str
        provider = self.provider

        country: None | str
        country = self.country

        country_code: None | str
        country_code = self.country_code

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "enabled": enabled,
                "provider": provider,
                "country": country,
                "countryCode": country_code,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        enabled = d.pop("enabled")

        def _parse_provider(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        provider = _parse_provider(d.pop("provider"))

        def _parse_country(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        country = _parse_country(d.pop("country"))

        def _parse_country_code(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        country_code = _parse_country_code(d.pop("countryCode"))

        messaging_facts = cls(
            enabled=enabled,
            provider=provider,
            country=country,
            country_code=country_code,
        )

        messaging_facts.additional_properties = d
        return messaging_facts

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
