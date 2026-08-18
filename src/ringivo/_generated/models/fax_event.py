from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.webhook_event_type import WebhookEventType

if TYPE_CHECKING:
    from ..models.fax_event_data import FaxEventData


T = TypeVar("T", bound="FaxEvent")


@_attrs_define
class FaxEvent:
    """
    Attributes:
        event_id (UUID): The dedupe key.
        type_ (WebhookEventType): Every event name a subscriber may ask for.
        occurred_at (datetime.datetime): When the transition happened — captured at the event, not at delivery, so a
            retry does
            not claim the fax was delivered when we finally reached you.
        data (FaxEventData): A SNAPSHOT of the fax, frozen when the transition happened — not a fresh read. A retry six
            hours later carries the same values, so a `fax.sending` event never says `delivered`.

            **No document content, no object keys and no URLs.** A webhook body travels to a third party
            over the public internet and is stored in their logs. Fetch the pages with your own
            credential at `GET /v1/faxes/{fax}/media`, which is also what records who looked.
    """

    event_id: UUID
    type_: WebhookEventType
    occurred_at: datetime.datetime
    data: FaxEventData
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        event_id = str(self.event_id)

        type_ = self.type_.value

        occurred_at = self.occurred_at.isoformat()

        data = self.data.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "event_id": event_id,
                "type": type_,
                "occurred_at": occurred_at,
                "data": data,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.fax_event_data import FaxEventData

        d = dict(src_dict)
        event_id = UUID(d.pop("event_id"))

        type_ = WebhookEventType(d.pop("type"))

        occurred_at = datetime.datetime.fromisoformat(d.pop("occurred_at"))

        data = FaxEventData.from_dict(d.pop("data"))

        fax_event = cls(
            event_id=event_id,
            type_=type_,
            occurred_at=occurred_at,
            data=data,
        )

        fax_event.additional_properties = d
        return fax_event

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
