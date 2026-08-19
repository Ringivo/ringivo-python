from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="IntegrationTokenResponse")


@_attrs_define
class IntegrationTokenResponse:
    """
    Attributes:
        access_token (str): The bearer token. Send it as `Authorization: Bearer <token>`.
        token_type (str):
        expires_in (int): Seconds until the token expires — 900, a fresh 15 minutes.
        scopes (list[str]): The scopes the token actually carries, after the intersection. This is the authoritative
            answer and it may be shorter than what you asked for.
    """

    access_token: str
    token_type: str
    expires_in: int
    scopes: list[str]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        access_token = self.access_token

        token_type = self.token_type

        expires_in = self.expires_in

        scopes = self.scopes

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "access_token": access_token,
                "token_type": token_type,
                "expires_in": expires_in,
                "scopes": scopes,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        access_token = d.pop("access_token")

        token_type = d.pop("token_type")

        expires_in = d.pop("expires_in")

        scopes = cast(list[str], d.pop("scopes"))

        integration_token_response = cls(
            access_token=access_token,
            token_type=token_type,
            expires_in=expires_in,
            scopes=scopes,
        )

        integration_token_response.additional_properties = d
        return integration_token_response

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
