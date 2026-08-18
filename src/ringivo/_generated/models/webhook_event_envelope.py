from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.webhook_event_type import WebhookEventType

T = TypeVar("T", bound="WebhookEventEnvelope")


@_attrs_define
class WebhookEventEnvelope:
    """The envelope every outbound webhook body shares. `data` is added by the event schema that
    uses it — see `FaxEvent`.

    ## Verify the signature before you trust it

    Every delivery carries a `Ringivo-Signature` header:

    ```
    Ringivo-Signature: t=1755331200,v1=9f86d0…,v1=2c26b4…
    ```

    `t` is the Unix second the delivery was signed. Each `v1` is
    `HMAC-SHA256(secret, "<t>.<raw body>")` in lowercase hex. To verify: recompute the MAC over
    `"<t>.<raw body>"` with your `whsec_` secret, compare it to each `v1` in **constant time**,
    and reject anything whose `t` is more than **300 seconds** from your own clock. Both halves
    must pass — a good MAC with an old `t` is a replay, and a fresh `t` with no matching MAC is
    a forgery.

    **Sign the RAW BODY, never a re-encoding.** Parsing the JSON and re-encoding it before
    verifying WILL fail, and correctly so: key order, unicode escaping and number formatting are
    free choices no two encoders make identically. This is the commonest mistake with
    signatures of this shape.

    **A second `v1` appears only during a rotation's 24-hour grace window**, signed with the
    previous secret, newest first — so a receiver that checks only the first one validates
    against the secret we want it to hold.

    ## Delivery is at-least-once

    Dedupe on `event_id`: a retried delivery of the same event carries the same id, and two
    genuine transitions never share one. A failed delivery is retried after **10s, 1m, 5m, 30m,
    2h and 6h** — seven POSTs in all, the last about eight and three-quarter hours after the
    event — and then dead-lettered. Ask
    `GET /v1/webhook-deliveries?filter[status]=dead` for what you missed.

    Answer any 2XX to accept. Redirects are never followed. We wait ten seconds; if your handler
    needs longer, answer 202 and do the work afterwards.

        Attributes:
            event_id (UUID): The dedupe key.
            type_ (WebhookEventType): Every event name a subscriber may ask for.
            occurred_at (datetime.datetime): When the transition happened — captured at the event, not at delivery, so a
                retry does
                not claim the fax was delivered when we finally reached you.
    """

    event_id: UUID
    type_: WebhookEventType
    occurred_at: datetime.datetime
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        event_id = str(self.event_id)

        type_ = self.type_.value

        occurred_at = self.occurred_at.isoformat()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "event_id": event_id,
                "type": type_,
                "occurred_at": occurred_at,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        event_id = UUID(d.pop("event_id"))

        type_ = WebhookEventType(d.pop("type"))

        occurred_at = datetime.datetime.fromisoformat(d.pop("occurred_at"))

        webhook_event_envelope = cls(
            event_id=event_id,
            type_=type_,
            occurred_at=occurred_at,
        )

        webhook_event_envelope.additional_properties = d
        return webhook_event_envelope

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
