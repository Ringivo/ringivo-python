from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.webhook_endpoint_update_request_data_type import WebhookEndpointUpdateRequestDataType

if TYPE_CHECKING:
    from ..models.webhook_endpoint_update_request_data_attributes import (
        WebhookEndpointUpdateRequestDataAttributes,
    )


T = TypeVar("T", bound="WebhookEndpointUpdateRequestData")


@_attrs_define
class WebhookEndpointUpdateRequestData:
    """
    Attributes:
        type_ (WebhookEndpointUpdateRequestDataType):
        id (UUID):
        attributes (WebhookEndpointUpdateRequestDataAttributes): `scopeType` and `scopeId` may be echoed back unchanged;
            a different value is a 422.
    """

    type_: WebhookEndpointUpdateRequestDataType
    id: UUID
    attributes: WebhookEndpointUpdateRequestDataAttributes
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        id = str(self.id)

        attributes = self.attributes.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "id": id,
                "attributes": attributes,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.webhook_endpoint_update_request_data_attributes import (
            WebhookEndpointUpdateRequestDataAttributes,
        )

        d = dict(src_dict)
        type_ = WebhookEndpointUpdateRequestDataType(d.pop("type"))

        id = UUID(d.pop("id"))

        attributes = WebhookEndpointUpdateRequestDataAttributes.from_dict(d.pop("attributes"))

        webhook_endpoint_update_request_data = cls(
            type_=type_,
            id=id,
            attributes=attributes,
        )

        webhook_endpoint_update_request_data.additional_properties = d
        return webhook_endpoint_update_request_data

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
