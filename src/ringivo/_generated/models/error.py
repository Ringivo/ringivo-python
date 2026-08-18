from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.error_code import ErrorCode
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.error_meta import ErrorMeta
    from ..models.error_source import ErrorSource


T = TypeVar("T", bound="Error")


@_attrs_define
class Error:
    """One problem with one request.

    Attributes:
        status (str): The HTTP status, as a string.
        title (str): A short human phrase — the same for every instance of a code.
        detail (str | Unset): What went wrong this time, in a sentence.
        code (ErrorCode | Unset): The stable machine vocabulary an integrator branches on. Not every refusal carries
            one:
            where no published code names the case, the status is the contract and `meta` carries the
            detail.
        source (ErrorSource | Unset): Where the problem is. A JSON:API document body gets a `pointer`; a flat form body
            or a query
            parameter gets a `parameter`.
        meta (ErrorMeta | Unset):
    """

    status: str
    title: str
    detail: str | Unset = UNSET
    code: ErrorCode | Unset = UNSET
    source: ErrorSource | Unset = UNSET
    meta: ErrorMeta | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        status = self.status

        title = self.title

        detail = self.detail

        code: str | Unset = UNSET
        if not isinstance(self.code, Unset):
            code = self.code.value

        source: dict[str, Any] | Unset = UNSET
        if not isinstance(self.source, Unset):
            source = self.source.to_dict()

        meta: dict[str, Any] | Unset = UNSET
        if not isinstance(self.meta, Unset):
            meta = self.meta.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "status": status,
                "title": title,
            }
        )
        if detail is not UNSET:
            field_dict["detail"] = detail
        if code is not UNSET:
            field_dict["code"] = code
        if source is not UNSET:
            field_dict["source"] = source
        if meta is not UNSET:
            field_dict["meta"] = meta

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.error_meta import ErrorMeta
        from ..models.error_source import ErrorSource

        d = dict(src_dict)
        status = d.pop("status")

        title = d.pop("title")

        detail = d.pop("detail", UNSET)

        _code = d.pop("code", UNSET)
        code: ErrorCode | Unset
        if isinstance(_code, Unset):
            code = UNSET
        else:
            code = ErrorCode(_code)

        _source = d.pop("source", UNSET)
        source: ErrorSource | Unset
        if isinstance(_source, Unset):
            source = UNSET
        else:
            source = ErrorSource.from_dict(_source)

        _meta = d.pop("meta", UNSET)
        meta: ErrorMeta | Unset
        if isinstance(_meta, Unset):
            meta = UNSET
        else:
            meta = ErrorMeta.from_dict(_meta)

        error = cls(
            status=status,
            title=title,
            detail=detail,
            code=code,
            source=source,
            meta=meta,
        )

        error.additional_properties = d
        return error

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
