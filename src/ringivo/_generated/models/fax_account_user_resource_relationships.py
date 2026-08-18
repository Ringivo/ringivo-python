from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.relationship_to_one import RelationshipToOne


T = TypeVar("T", bound="FaxAccountUserResourceRelationships")


@_attrs_define
class FaxAccountUserResourceRelationships:
    """
    Attributes:
        fax_account (RelationshipToOne | Unset): A to-one relationship. `data` is present only when the relationship was
            resolved — a plain
            read that included nothing gives `links` alone.
        user (RelationshipToOne | Unset): A to-one relationship. `data` is present only when the relationship was
            resolved — a plain
            read that included nothing gives `links` alone.
    """

    fax_account: RelationshipToOne | Unset = UNSET
    user: RelationshipToOne | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        fax_account: dict[str, Any] | Unset = UNSET
        if not isinstance(self.fax_account, Unset):
            fax_account = self.fax_account.to_dict()

        user: dict[str, Any] | Unset = UNSET
        if not isinstance(self.user, Unset):
            user = self.user.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if fax_account is not UNSET:
            field_dict["faxAccount"] = fax_account
        if user is not UNSET:
            field_dict["user"] = user

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.relationship_to_one import RelationshipToOne

        d = dict(src_dict)
        _fax_account = d.pop("faxAccount", UNSET)
        fax_account: RelationshipToOne | Unset
        if isinstance(_fax_account, Unset):
            fax_account = UNSET
        else:
            fax_account = RelationshipToOne.from_dict(_fax_account)

        _user = d.pop("user", UNSET)
        user: RelationshipToOne | Unset
        if isinstance(_user, Unset):
            user = UNSET
        else:
            user = RelationshipToOne.from_dict(_user)

        fax_account_user_resource_relationships = cls(
            fax_account=fax_account,
            user=user,
        )

        fax_account_user_resource_relationships.additional_properties = d
        return fax_account_user_resource_relationships

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
