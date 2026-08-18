from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="MediaLink")


@_attrs_define
class MediaLink:
    """A capability that expires, plus the facts about what is behind it. Not a JSON:API resource:
    there is no stored member this URI could be a collection of.

        Attributes:
            url (str): A time-limited download URL on your own API host. Fetch it with a plain `GET` and no
                `Authorization` header — the signature it carries is the authorization. Opaque: the
                signature covers the whole address, so any edit invalidates it. Short-lived — do not
                cache it past `expires_at` or share it.
            expires_at (datetime.datetime):
            byte_size (int):
            sha256 (str): The digest of the bytes behind `url`, so you can verify what you downloaded.
    """

    url: str
    expires_at: datetime.datetime
    byte_size: int
    sha256: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        url = self.url

        expires_at = self.expires_at.isoformat()

        byte_size = self.byte_size

        sha256 = self.sha256

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "url": url,
                "expires_at": expires_at,
                "byte_size": byte_size,
                "sha256": sha256,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        url = d.pop("url")

        expires_at = datetime.datetime.fromisoformat(d.pop("expires_at"))

        byte_size = d.pop("byte_size")

        sha256 = d.pop("sha256")

        media_link = cls(
            url=url,
            expires_at=expires_at,
            byte_size=byte_size,
            sha256=sha256,
        )

        media_link.additional_properties = d
        return media_link

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
