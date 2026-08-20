from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.number_lookup_dip_status import NumberLookupDipStatus

if TYPE_CHECKING:
    from ..models.caller_name_facts import CallerNameFacts


T = TypeVar("T", bound="NumberLookupCallerNameComponent")


@_attrs_define
class NumberLookupCallerNameComponent:
    """
    Attributes:
        status (NumberLookupDipStatus): What one component did. `no_data` and `failed` both carry `data: null` and mean
            different
            things — see the operation description.
        data (CallerNameFacts | None):
    """

    status: NumberLookupDipStatus
    data: CallerNameFacts | None
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.caller_name_facts import CallerNameFacts

        status = self.status.value

        data: dict[str, Any] | None
        if isinstance(self.data, CallerNameFacts):
            data = self.data.to_dict()
        else:
            data = self.data

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "status": status,
                "data": data,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.caller_name_facts import CallerNameFacts

        d = dict(src_dict)
        status = NumberLookupDipStatus(d.pop("status"))

        def _parse_data(data: object) -> CallerNameFacts | None:
            if data is None:
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                data_type_0 = CallerNameFacts.from_dict(data)

                return data_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(CallerNameFacts | None, data)

        data = _parse_data(d.pop("data"))

        number_lookup_caller_name_component = cls(
            status=status,
            data=data,
        )

        number_lookup_caller_name_component.additional_properties = d
        return number_lookup_caller_name_component

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
