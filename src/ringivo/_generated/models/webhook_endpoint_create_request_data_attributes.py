from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.webhook_event_type import WebhookEventType
from ..models.webhook_scope_type import WebhookScopeType
from ..types import UNSET, Unset

T = TypeVar("T", bound="WebhookEndpointCreateRequestDataAttributes")


@_attrs_define
class WebhookEndpointCreateRequestDataAttributes:
    """
    Attributes:
        url (str): `https` only, on a public host.
        scope_type (WebhookScopeType): What an endpoint hears about. All three are matched as a containment order, so a
            reseller-wide endpoint and a per-account one both hear about the same fax.
        scope_id (UUID):
        events (list[WebhookEventType] | None | Unset):
        active (bool | Unset):
    """

    url: str
    scope_type: WebhookScopeType
    scope_id: UUID
    events: list[WebhookEventType] | None | Unset = UNSET
    active: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        url = self.url

        scope_type = self.scope_type.value

        scope_id = str(self.scope_id)

        events: list[str] | None | Unset
        if isinstance(self.events, Unset):
            events = UNSET
        elif isinstance(self.events, list):
            events = []
            for events_type_0_item_data in self.events:
                events_type_0_item = events_type_0_item_data.value
                events.append(events_type_0_item)

        else:
            events = self.events

        active = self.active

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "url": url,
                "scopeType": scope_type,
                "scopeId": scope_id,
            }
        )
        if events is not UNSET:
            field_dict["events"] = events
        if active is not UNSET:
            field_dict["active"] = active

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        url = d.pop("url")

        scope_type = WebhookScopeType(d.pop("scopeType"))

        scope_id = UUID(d.pop("scopeId"))

        def _parse_events(data: object) -> list[WebhookEventType] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                events_type_0 = []
                _events_type_0 = data
                for events_type_0_item_data in _events_type_0:
                    events_type_0_item = WebhookEventType(events_type_0_item_data)

                    events_type_0.append(events_type_0_item)

                return events_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[WebhookEventType] | None | Unset, data)

        events = _parse_events(d.pop("events", UNSET))

        active = d.pop("active", UNSET)

        webhook_endpoint_create_request_data_attributes = cls(
            url=url,
            scope_type=scope_type,
            scope_id=scope_id,
            events=events,
            active=active,
        )

        webhook_endpoint_create_request_data_attributes.additional_properties = d
        return webhook_endpoint_create_request_data_attributes

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
