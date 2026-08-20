from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="LrnFacts")


@_attrs_define
class LrnFacts:
    """The porting facts — who the number routes to now, and who owns its block.

    Attributes:
        lrn (str): The location routing number, 11 digits.
        spid (None | str): Who the number is ported to **now** — this is the one porting cares about. A string,
            never a number: values like `506J` exist.
        ocn (None | str): Who owns the number block. Often differs from `spid`. A string, never a number.
        lata (None | str):
        lec (None | str): The carrier's full name, as the source spells it.
        line_type (None | str): `CLEC`, `WIRELESS`, `ILEC`. This is what the **network** says. It is not what a losing
            carrier's bill says, and it must not be used to correct a port order's number type.
        rate_center (None | str): The **LRN's** rate center — not the dialed number's. The two often differ.
        state (None | str): The **LRN's** state or province code.
        jurisdiction (None | str): A string, not a boolean — commonly the literal `INDETERMINATE`, which is not false.
        local (None | str): A string, not a boolean, for the same reason as `jurisdiction`.
        ported_at (datetime.datetime | None): When the number last ported. Null if it never has.
    """

    lrn: str
    spid: None | str
    ocn: None | str
    lata: None | str
    lec: None | str
    line_type: None | str
    rate_center: None | str
    state: None | str
    jurisdiction: None | str
    local: None | str
    ported_at: datetime.datetime | None
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        lrn = self.lrn

        spid: None | str
        spid = self.spid

        ocn: None | str
        ocn = self.ocn

        lata: None | str
        lata = self.lata

        lec: None | str
        lec = self.lec

        line_type: None | str
        line_type = self.line_type

        rate_center: None | str
        rate_center = self.rate_center

        state: None | str
        state = self.state

        jurisdiction: None | str
        jurisdiction = self.jurisdiction

        local: None | str
        local = self.local

        ported_at: None | str
        if isinstance(self.ported_at, datetime.datetime):
            ported_at = self.ported_at.isoformat()
        else:
            ported_at = self.ported_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "lrn": lrn,
                "spid": spid,
                "ocn": ocn,
                "lata": lata,
                "lec": lec,
                "lineType": line_type,
                "rateCenter": rate_center,
                "state": state,
                "jurisdiction": jurisdiction,
                "local": local,
                "portedAt": ported_at,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        lrn = d.pop("lrn")

        def _parse_spid(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        spid = _parse_spid(d.pop("spid"))

        def _parse_ocn(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        ocn = _parse_ocn(d.pop("ocn"))

        def _parse_lata(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        lata = _parse_lata(d.pop("lata"))

        def _parse_lec(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        lec = _parse_lec(d.pop("lec"))

        def _parse_line_type(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        line_type = _parse_line_type(d.pop("lineType"))

        def _parse_rate_center(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        rate_center = _parse_rate_center(d.pop("rateCenter"))

        def _parse_state(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        state = _parse_state(d.pop("state"))

        def _parse_jurisdiction(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        jurisdiction = _parse_jurisdiction(d.pop("jurisdiction"))

        def _parse_local(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        local = _parse_local(d.pop("local"))

        def _parse_ported_at(data: object) -> datetime.datetime | None:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                ported_at_type_0 = datetime.datetime.fromisoformat(data)

                return ported_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None, data)

        ported_at = _parse_ported_at(d.pop("portedAt"))

        lrn_facts = cls(
            lrn=lrn,
            spid=spid,
            ocn=ocn,
            lata=lata,
            lec=lec,
            line_type=line_type,
            rate_center=rate_center,
            state=state,
            jurisdiction=jurisdiction,
            local=local,
            ported_at=ported_at,
        )

        lrn_facts.additional_properties = d
        return lrn_facts

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
