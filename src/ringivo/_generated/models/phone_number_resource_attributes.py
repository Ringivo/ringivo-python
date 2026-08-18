from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.phone_number_resource_attributes_status_type_1 import (
    PhoneNumberResourceAttributesStatusType1,
)
from ..models.phone_number_resource_attributes_status_type_2_type_1 import (
    PhoneNumberResourceAttributesStatusType2Type1,
)
from ..models.phone_number_resource_attributes_status_type_3_type_1 import (
    PhoneNumberResourceAttributesStatusType3Type1,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="PhoneNumberResourceAttributes")


@_attrs_define
class PhoneNumberResourceAttributes:
    """
    Attributes:
        e164 (None | str | Unset):
        status (None | PhoneNumberResourceAttributesStatusType1 | PhoneNumberResourceAttributesStatusType2Type1 |
            PhoneNumberResourceAttributesStatusType3Type1 | Unset):
        country (None | str | Unset):
        activated_at (datetime.datetime | None | Unset):
        created_at (datetime.datetime | None | Unset):
    """

    e164: None | str | Unset = UNSET
    status: (
        None
        | PhoneNumberResourceAttributesStatusType1
        | PhoneNumberResourceAttributesStatusType2Type1
        | PhoneNumberResourceAttributesStatusType3Type1
        | Unset
    ) = UNSET
    country: None | str | Unset = UNSET
    activated_at: datetime.datetime | None | Unset = UNSET
    created_at: datetime.datetime | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        e164: None | str | Unset
        if isinstance(self.e164, Unset):
            e164 = UNSET
        else:
            e164 = self.e164

        status: None | str | Unset
        if isinstance(self.status, Unset):
            status = UNSET
        elif isinstance(self.status, PhoneNumberResourceAttributesStatusType1):
            status = self.status.value
        elif isinstance(self.status, PhoneNumberResourceAttributesStatusType2Type1):
            status = self.status.value
        elif isinstance(self.status, PhoneNumberResourceAttributesStatusType3Type1):
            status = self.status.value
        else:
            status = self.status

        country: None | str | Unset
        if isinstance(self.country, Unset):
            country = UNSET
        else:
            country = self.country

        activated_at: None | str | Unset
        if isinstance(self.activated_at, Unset):
            activated_at = UNSET
        elif isinstance(self.activated_at, datetime.datetime):
            activated_at = self.activated_at.isoformat()
        else:
            activated_at = self.activated_at

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        elif isinstance(self.created_at, datetime.datetime):
            created_at = self.created_at.isoformat()
        else:
            created_at = self.created_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if e164 is not UNSET:
            field_dict["e164"] = e164
        if status is not UNSET:
            field_dict["status"] = status
        if country is not UNSET:
            field_dict["country"] = country
        if activated_at is not UNSET:
            field_dict["activatedAt"] = activated_at
        if created_at is not UNSET:
            field_dict["createdAt"] = created_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_e164(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        e164 = _parse_e164(d.pop("e164", UNSET))

        def _parse_status(
            data: object,
        ) -> (
            None
            | PhoneNumberResourceAttributesStatusType1
            | PhoneNumberResourceAttributesStatusType2Type1
            | PhoneNumberResourceAttributesStatusType3Type1
            | Unset
        ):
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                status_type_1 = PhoneNumberResourceAttributesStatusType1(data)

                return status_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, str):
                    raise TypeError()
                status_type_2_type_1 = PhoneNumberResourceAttributesStatusType2Type1(data)

                return status_type_2_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, str):
                    raise TypeError()
                status_type_3_type_1 = PhoneNumberResourceAttributesStatusType3Type1(data)

                return status_type_3_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(
                None
                | PhoneNumberResourceAttributesStatusType1
                | PhoneNumberResourceAttributesStatusType2Type1
                | PhoneNumberResourceAttributesStatusType3Type1
                | Unset,
                data,
            )

        status = _parse_status(d.pop("status", UNSET))

        def _parse_country(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        country = _parse_country(d.pop("country", UNSET))

        def _parse_activated_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                activated_at_type_0 = datetime.datetime.fromisoformat(data)

                return activated_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        activated_at = _parse_activated_at(d.pop("activatedAt", UNSET))

        def _parse_created_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                created_at_type_0 = datetime.datetime.fromisoformat(data)

                return created_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        created_at = _parse_created_at(d.pop("createdAt", UNSET))

        phone_number_resource_attributes = cls(
            e164=e164,
            status=status,
            country=country,
            activated_at=activated_at,
            created_at=created_at,
        )

        phone_number_resource_attributes.additional_properties = d
        return phone_number_resource_attributes

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
