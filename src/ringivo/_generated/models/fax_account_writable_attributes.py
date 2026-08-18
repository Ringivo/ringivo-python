from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.fax_account_status import FaxAccountStatus
from ..types import UNSET, Unset

T = TypeVar("T", bound="FaxAccountWritableAttributes")


@_attrs_define
class FaxAccountWritableAttributes:
    """
    Attributes:
        name (str | Unset):
        header_text (None | str | Unset):
        default_from_e164 (None | str | Unset):
        retention_days (int | Unset):
        compliance_retention (bool | Unset):
        max_attempts (int | Unset):
        status (FaxAccountStatus | Unset): A suspended account may receive faxes but not send them.
    """

    name: str | Unset = UNSET
    header_text: None | str | Unset = UNSET
    default_from_e164: None | str | Unset = UNSET
    retention_days: int | Unset = UNSET
    compliance_retention: bool | Unset = UNSET
    max_attempts: int | Unset = UNSET
    status: FaxAccountStatus | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        header_text: None | str | Unset
        if isinstance(self.header_text, Unset):
            header_text = UNSET
        else:
            header_text = self.header_text

        default_from_e164: None | str | Unset
        if isinstance(self.default_from_e164, Unset):
            default_from_e164 = UNSET
        else:
            default_from_e164 = self.default_from_e164

        retention_days = self.retention_days

        compliance_retention = self.compliance_retention

        max_attempts = self.max_attempts

        status: str | Unset = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if name is not UNSET:
            field_dict["name"] = name
        if header_text is not UNSET:
            field_dict["headerText"] = header_text
        if default_from_e164 is not UNSET:
            field_dict["defaultFromE164"] = default_from_e164
        if retention_days is not UNSET:
            field_dict["retentionDays"] = retention_days
        if compliance_retention is not UNSET:
            field_dict["complianceRetention"] = compliance_retention
        if max_attempts is not UNSET:
            field_dict["maxAttempts"] = max_attempts
        if status is not UNSET:
            field_dict["status"] = status

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name", UNSET)

        def _parse_header_text(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        header_text = _parse_header_text(d.pop("headerText", UNSET))

        def _parse_default_from_e164(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        default_from_e164 = _parse_default_from_e164(d.pop("defaultFromE164", UNSET))

        retention_days = d.pop("retentionDays", UNSET)

        compliance_retention = d.pop("complianceRetention", UNSET)

        max_attempts = d.pop("maxAttempts", UNSET)

        _status = d.pop("status", UNSET)
        status: FaxAccountStatus | Unset
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = FaxAccountStatus(_status)

        fax_account_writable_attributes = cls(
            name=name,
            header_text=header_text,
            default_from_e164=default_from_e164,
            retention_days=retention_days,
            compliance_retention=compliance_retention,
            max_attempts=max_attempts,
            status=status,
        )

        fax_account_writable_attributes.additional_properties = d
        return fax_account_writable_attributes

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
