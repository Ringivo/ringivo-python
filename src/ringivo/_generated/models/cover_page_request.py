from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="CoverPageRequest")


@_attrs_define
class CoverPageRequest:
    """The four fields of the built-in cover page. A cover page IS a page — it is counted in
    `pages_total` and it bills.

    Shared by both send bodies on purpose: the ceiling on each field is one validation rule in
    the application, so two copies here would be two places for it to drift.

        Attributes:
            to_name (str | Unset):
            from_name (str | Unset):
            subject (str | Unset):
            message (str | Unset):
    """

    to_name: str | Unset = UNSET
    from_name: str | Unset = UNSET
    subject: str | Unset = UNSET
    message: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        to_name = self.to_name

        from_name = self.from_name

        subject = self.subject

        message = self.message

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if to_name is not UNSET:
            field_dict["to_name"] = to_name
        if from_name is not UNSET:
            field_dict["from_name"] = from_name
        if subject is not UNSET:
            field_dict["subject"] = subject
        if message is not UNSET:
            field_dict["message"] = message

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        to_name = d.pop("to_name", UNSET)

        from_name = d.pop("from_name", UNSET)

        subject = d.pop("subject", UNSET)

        message = d.pop("message", UNSET)

        cover_page_request = cls(
            to_name=to_name,
            from_name=from_name,
            subject=subject,
            message=message,
        )

        cover_page_request.additional_properties = d
        return cover_page_request

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
