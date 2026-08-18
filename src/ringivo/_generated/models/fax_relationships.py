from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.relationship_to_many import RelationshipToMany
    from ..models.relationship_to_one import RelationshipToOne


T = TypeVar("T", bound="FaxRelationships")


@_attrs_define
class FaxRelationships:
    """
    Attributes:
        fax_account (RelationshipToOne | Unset): A to-one relationship. `data` is present only when the relationship was
            resolved — a plain
            read that included nothing gives `links` alone.
        attempts (RelationshipToMany | Unset): A to-many relationship.
    """

    fax_account: RelationshipToOne | Unset = UNSET
    attempts: RelationshipToMany | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        fax_account: dict[str, Any] | Unset = UNSET
        if not isinstance(self.fax_account, Unset):
            fax_account = self.fax_account.to_dict()

        attempts: dict[str, Any] | Unset = UNSET
        if not isinstance(self.attempts, Unset):
            attempts = self.attempts.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if fax_account is not UNSET:
            field_dict["faxAccount"] = fax_account
        if attempts is not UNSET:
            field_dict["attempts"] = attempts

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.relationship_to_many import RelationshipToMany
        from ..models.relationship_to_one import RelationshipToOne

        d = dict(src_dict)
        _fax_account = d.pop("faxAccount", UNSET)
        fax_account: RelationshipToOne | Unset
        if isinstance(_fax_account, Unset):
            fax_account = UNSET
        else:
            fax_account = RelationshipToOne.from_dict(_fax_account)

        _attempts = d.pop("attempts", UNSET)
        attempts: RelationshipToMany | Unset
        if isinstance(_attempts, Unset):
            attempts = UNSET
        else:
            attempts = RelationshipToMany.from_dict(_attempts)

        fax_relationships = cls(
            fax_account=fax_account,
            attempts=attempts,
        )

        fax_relationships.additional_properties = d
        return fax_relationships

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
