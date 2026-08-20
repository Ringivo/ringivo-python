from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.number_lookup_caller_name_component import NumberLookupCallerNameComponent
    from ..models.number_lookup_lrn_component import NumberLookupLrnComponent
    from ..models.number_lookup_messaging_component import NumberLookupMessagingComponent


T = TypeVar("T", bound="NumberLookupComponents")


@_attrs_define
class NumberLookupComponents:
    """The three paid components. Each reports its own outcome and they fail independently — a
    lookup with two answers and one failure is normal, and is billed in full.

        Attributes:
            lrn (NumberLookupLrnComponent):
            caller_name (NumberLookupCallerNameComponent):
            messaging (NumberLookupMessagingComponent):
    """

    lrn: NumberLookupLrnComponent
    caller_name: NumberLookupCallerNameComponent
    messaging: NumberLookupMessagingComponent
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        lrn = self.lrn.to_dict()

        caller_name = self.caller_name.to_dict()

        messaging = self.messaging.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "lrn": lrn,
                "callerName": caller_name,
                "messaging": messaging,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.number_lookup_caller_name_component import NumberLookupCallerNameComponent
        from ..models.number_lookup_lrn_component import NumberLookupLrnComponent
        from ..models.number_lookup_messaging_component import NumberLookupMessagingComponent

        d = dict(src_dict)
        lrn = NumberLookupLrnComponent.from_dict(d.pop("lrn"))

        caller_name = NumberLookupCallerNameComponent.from_dict(d.pop("callerName"))

        messaging = NumberLookupMessagingComponent.from_dict(d.pop("messaging"))

        number_lookup_components = cls(
            lrn=lrn,
            caller_name=caller_name,
            messaging=messaging,
        )

        number_lookup_components.additional_properties = d
        return number_lookup_components

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
