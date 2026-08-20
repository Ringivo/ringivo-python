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
    """Every member here is optional only under a stated condition. Send `client_id` and
    `client_secret` unless they ride an `Authorization: Basic` header, and send `tenant` unless
    your client holds exactly one active grant. The operation description carries both rules.

        Attributes:
            client_id (UUID | Unset): The client id you were issued. Omit it only when it rides an `Authorization: Basic`
                header instead; sending it in both places is a 422.
            client_secret (str | Unset): Its secret. In the body it travels over TLS and never in a URL; the alternative is
                the
                `Authorization: Basic` header, never a query parameter either way.
            tenant (UUID | Unset): The reseller you are acting for. Your client must hold an active grant for it, or the
                request is refused with a 403.

                **Optional when your client holds exactly one active grant**, whose tenant — and
                customer, if it names one — then become the token's. With more than one active grant
                and no `tenant`, the request is a 422 naming the ambiguity.

                Omitting the member is the only way to ask for that: unlike `customer`, this field must
                be a **string** whenever it is present, so `""` or `null` is a 422 rather than a
                request for automatic selection.
            customer (None | Unset | UUID): One customer inside that tenant, when a grant names one. It SELECTS a context
                somebody
                already granted and narrows nothing by itself. Omit it — or send null — for the
                tenant-wide token.
            scopes (list[str] | Unset): The scopes you are asking for. What you receive is the intersection with your grant
                and,
                on a customer-scoped token, with the customer-scopeable set. A scope outside that is
                dropped silently, so read `scopes` back off the response.

                Silently means *a scope that exists*. A scope NAME this platform does not publish is a
                422 listing the offenders — see the operation description.
            scope (None | str | Unset): The same request written as one space-delimited string (RFC 6749 section 3.3), for
                clients whose OAuth library writes that spelling. Send this or `scopes`; a request
                carrying both asks for the union. Null and empty both mean "no scopes", which is a
                valid — and useless — request.
    """

    client_id: UUID | Unset = UNSET
    client_secret: str | Unset = UNSET
    tenant: UUID | Unset = UNSET
    customer: None | Unset | UUID = UNSET
    scopes: list[str] | Unset = UNSET
    scope: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        client_id: str | Unset = UNSET
        if not isinstance(self.client_id, Unset):
            client_id = str(self.client_id)

        client_secret = self.client_secret

        tenant: str | Unset = UNSET
        if not isinstance(self.tenant, Unset):
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

        scope: None | str | Unset
        if isinstance(self.scope, Unset):
            scope = UNSET
        else:
            scope = self.scope

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if client_id is not UNSET:
            field_dict["client_id"] = client_id
        if client_secret is not UNSET:
            field_dict["client_secret"] = client_secret
        if tenant is not UNSET:
            field_dict["tenant"] = tenant
        if customer is not UNSET:
            field_dict["customer"] = customer
        if scopes is not UNSET:
            field_dict["scopes"] = scopes
        if scope is not UNSET:
            field_dict["scope"] = scope

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        _client_id = d.pop("client_id", UNSET)
        client_id: UUID | Unset
        if isinstance(_client_id, Unset):
            client_id = UNSET
        else:
            client_id = UUID(_client_id)

        client_secret = d.pop("client_secret", UNSET)

        _tenant = d.pop("tenant", UNSET)
        tenant: UUID | Unset
        if isinstance(_tenant, Unset):
            tenant = UNSET
        else:
            tenant = UUID(_tenant)

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

        def _parse_scope(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        scope = _parse_scope(d.pop("scope", UNSET))

        integration_token_request = cls(
            client_id=client_id,
            client_secret=client_secret,
            tenant=tenant,
            customer=customer,
            scopes=scopes,
            scope=scope,
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
