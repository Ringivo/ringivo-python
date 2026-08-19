from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="IntegrationTokenRequest")


@_attrs_define
class IntegrationTokenRequest:
    """
    Attributes:
        client_id (UUID): The client id you were issued.
        client_secret (str): Its secret. It travels in the body over TLS, never in a URL.
        tenant (UUID): The reseller you are acting for. Your client must hold an active grant for it, or the
            request is refused with a 403.
        customer (None | Unset | UUID): One customer inside that tenant, when a grant names one. It SELECTS a context
            somebody
            already granted and narrows nothing by itself. Omit it — or send null — for the
            tenant-wide token.
        scopes (list[str] | Unset): The scopes you are asking for. What you receive is the intersection with your grant
            and,
            on a customer-scoped token, with the customer-scopeable set. Anything outside it is
            dropped silently, so read `scopes` back off the response.
    """

    client_id: UUID
    client_secret: str
    tenant: UUID
    customer: None | Unset | UUID = UNSET
    scopes: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        client_id = str(self.client_id)

        client_secret = self.client_secret

        tenant = str(self.tenant)

        customer: None | str | Unset
        if isinstance(self.customer, Unset):
            customer = UNSET
        elif isinstance(self.customer, UUID):
            customer = str(self.customer)
        else:
            customer = self.customer

        scopes: list[str] | Unset = UNSET
        if not isinstance(self.scopes, Unset):
            scopes = self.scopes

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "tenant": tenant,
            }
        )
        if customer is not UNSET:
            field_dict["customer"] = customer
        if scopes is not UNSET:
            field_dict["scopes"] = scopes

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        client_id = UUID(d.pop("client_id"))

        client_secret = d.pop("client_secret")

        tenant = UUID(d.pop("tenant"))

        def _parse_customer(data: object) -> None | Unset | UUID:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                customer_type_0 = UUID(data)

                return customer_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | Unset | UUID, data)

        customer = _parse_customer(d.pop("customer", UNSET))

        scopes = cast(list[str], d.pop("scopes", UNSET))

        integration_token_request = cls(
            client_id=client_id,
            client_secret=client_secret,
            tenant=tenant,
            customer=customer,
            scopes=scopes,
        )

        integration_token_request.additional_properties = d
        return integration_token_request

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
