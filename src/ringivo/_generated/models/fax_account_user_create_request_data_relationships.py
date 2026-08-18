from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.fax_account_user_create_request_data_relationships_fax_account import (
        FaxAccountUserCreateRequestDataRelationshipsFaxAccount,
    )
    from ..models.fax_account_user_create_request_data_relationships_user import (
        FaxAccountUserCreateRequestDataRelationshipsUser,
    )


T = TypeVar("T", bound="FaxAccountUserCreateRequestDataRelationships")


@_attrs_define
class FaxAccountUserCreateRequestDataRelationships:
    """
    Attributes:
        fax_account (FaxAccountUserCreateRequestDataRelationshipsFaxAccount):
        user (FaxAccountUserCreateRequestDataRelationshipsUser):
    """

    fax_account: FaxAccountUserCreateRequestDataRelationshipsFaxAccount
    user: FaxAccountUserCreateRequestDataRelationshipsUser
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        fax_account = self.fax_account.to_dict()

        user = self.user.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "faxAccount": fax_account,
                "user": user,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.fax_account_user_create_request_data_relationships_fax_account import (
            FaxAccountUserCreateRequestDataRelationshipsFaxAccount,
        )
        from ..models.fax_account_user_create_request_data_relationships_user import (
            FaxAccountUserCreateRequestDataRelationshipsUser,
        )

        d = dict(src_dict)
        fax_account = FaxAccountUserCreateRequestDataRelationshipsFaxAccount.from_dict(
            d.pop("faxAccount")
        )

        user = FaxAccountUserCreateRequestDataRelationshipsUser.from_dict(d.pop("user"))

        fax_account_user_create_request_data_relationships = cls(
            fax_account=fax_account,
            user=user,
        )

        fax_account_user_create_request_data_relationships.additional_properties = d
        return fax_account_user_create_request_data_relationships

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
