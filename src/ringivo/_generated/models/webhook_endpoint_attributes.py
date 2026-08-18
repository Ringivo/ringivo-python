from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.webhook_event_type import WebhookEventType
from ..models.webhook_scope_type import WebhookScopeType
from ..types import UNSET, Unset

T = TypeVar("T", bound="WebhookEndpointAttributes")


@_attrs_define
class WebhookEndpointAttributes:
    """
    Attributes:
        scope_type (WebhookScopeType | Unset): What an endpoint hears about. All three are matched as a containment
            order, so a
            reseller-wide endpoint and a per-account one both hear about the same fax.
        scope_id (None | Unset | UUID): The id of the tenant, customer or fax account this endpoint hears about.
        url (None | str | Unset):
        events (list[WebhookEventType] | None | Unset): Null or `[]` both mean "every event in scope".
        active (bool | None | Unset):
        secret (None | str | Unset): The signing secret, `whsec_`-prefixed. **Non-null only in the response to the
            create or
            the rotate that minted it** — every other read is `null`, because the platform holds no
            readable copy.
        secret_previous_expires_at (datetime.datetime | None | Unset): When the PREVIOUS secret stops signing. Null
            outside a rotation's grace window; the
            previous secret itself is never published.
        created_at (datetime.datetime | None | Unset):
        updated_at (datetime.datetime | None | Unset):
    """

    scope_type: WebhookScopeType | Unset = UNSET
    scope_id: None | Unset | UUID = UNSET
    url: None | str | Unset = UNSET
    events: list[WebhookEventType] | None | Unset = UNSET
    active: bool | None | Unset = UNSET
    secret: None | str | Unset = UNSET
    secret_previous_expires_at: datetime.datetime | None | Unset = UNSET
    created_at: datetime.datetime | None | Unset = UNSET
    updated_at: datetime.datetime | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        scope_type: str | Unset = UNSET
        if not isinstance(self.scope_type, Unset):
            scope_type = self.scope_type.value

        scope_id: None | str | Unset
        if isinstance(self.scope_id, Unset):
            scope_id = UNSET
        elif isinstance(self.scope_id, UUID):
            scope_id = str(self.scope_id)
        else:
            scope_id = self.scope_id

        url: None | str | Unset
        if isinstance(self.url, Unset):
            url = UNSET
        else:
            url = self.url

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

        active: bool | None | Unset
        if isinstance(self.active, Unset):
            active = UNSET
        else:
            active = self.active

        secret: None | str | Unset
        if isinstance(self.secret, Unset):
            secret = UNSET
        else:
            secret = self.secret

        secret_previous_expires_at: None | str | Unset
        if isinstance(self.secret_previous_expires_at, Unset):
            secret_previous_expires_at = UNSET
        elif isinstance(self.secret_previous_expires_at, datetime.datetime):
            secret_previous_expires_at = self.secret_previous_expires_at.isoformat()
        else:
            secret_previous_expires_at = self.secret_previous_expires_at

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        elif isinstance(self.created_at, datetime.datetime):
            created_at = self.created_at.isoformat()
        else:
            created_at = self.created_at

        updated_at: None | str | Unset
        if isinstance(self.updated_at, Unset):
            updated_at = UNSET
        elif isinstance(self.updated_at, datetime.datetime):
            updated_at = self.updated_at.isoformat()
        else:
            updated_at = self.updated_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if scope_type is not UNSET:
            field_dict["scopeType"] = scope_type
        if scope_id is not UNSET:
            field_dict["scopeId"] = scope_id
        if url is not UNSET:
            field_dict["url"] = url
        if events is not UNSET:
            field_dict["events"] = events
        if active is not UNSET:
            field_dict["active"] = active
        if secret is not UNSET:
            field_dict["secret"] = secret
        if secret_previous_expires_at is not UNSET:
            field_dict["secretPreviousExpiresAt"] = secret_previous_expires_at
        if created_at is not UNSET:
            field_dict["createdAt"] = created_at
        if updated_at is not UNSET:
            field_dict["updatedAt"] = updated_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        _scope_type = d.pop("scopeType", UNSET)
        scope_type: WebhookScopeType | Unset
        if isinstance(_scope_type, Unset):
            scope_type = UNSET
        else:
            scope_type = WebhookScopeType(_scope_type)

        def _parse_scope_id(data: object) -> None | Unset | UUID:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                scope_id_type_0 = UUID(data)

                return scope_id_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | Unset | UUID, data)

        scope_id = _parse_scope_id(d.pop("scopeId", UNSET))

        def _parse_url(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        url = _parse_url(d.pop("url", UNSET))

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

        def _parse_active(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        active = _parse_active(d.pop("active", UNSET))

        def _parse_secret(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        secret = _parse_secret(d.pop("secret", UNSET))

        def _parse_secret_previous_expires_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                secret_previous_expires_at_type_0 = datetime.datetime.fromisoformat(data)

                return secret_previous_expires_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        secret_previous_expires_at = _parse_secret_previous_expires_at(
            d.pop("secretPreviousExpiresAt", UNSET)
        )

        def _parse_created_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                created_at_type_0 = datetime.datetime.fromisoformat(data)

                return created_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        created_at = _parse_created_at(d.pop("createdAt", UNSET))

        def _parse_updated_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                updated_at_type_0 = datetime.datetime.fromisoformat(data)

                return updated_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        updated_at = _parse_updated_at(d.pop("updatedAt", UNSET))

        webhook_endpoint_attributes = cls(
            scope_type=scope_type,
            scope_id=scope_id,
            url=url,
            events=events,
            active=active,
            secret=secret,
            secret_previous_expires_at=secret_previous_expires_at,
            created_at=created_at,
            updated_at=updated_at,
        )

        webhook_endpoint_attributes.additional_properties = d
        return webhook_endpoint_attributes

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
