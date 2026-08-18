from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.fax_document_metadata_kind import FaxDocumentMetadataKind
from ..types import UNSET, Unset

T = TypeVar("T", bound="FaxDocumentMetadata")


@_attrs_define
class FaxDocumentMetadata:
    """What one of a fax's documents is, WITHOUT any way to reach it. No object key and no URL is
    ever published here.

        Attributes:
            kind (FaxDocumentMetadataKind | Unset): `source` is what you uploaded; `tiff` went on the wire; `pdf` is what a
                person reads; `thumb` is the preview.
            ordinal (int | Unset):
            content_type (None | str | Unset):
            byte_size (int | None | Unset):
            sha256 (None | str | Unset):
            pages (int | None | Unset):
    """

    kind: FaxDocumentMetadataKind | Unset = UNSET
    ordinal: int | Unset = UNSET
    content_type: None | str | Unset = UNSET
    byte_size: int | None | Unset = UNSET
    sha256: None | str | Unset = UNSET
    pages: int | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        kind: str | Unset = UNSET
        if not isinstance(self.kind, Unset):
            kind = self.kind.value

        ordinal = self.ordinal

        content_type: None | str | Unset
        if isinstance(self.content_type, Unset):
            content_type = UNSET
        else:
            content_type = self.content_type

        byte_size: int | None | Unset
        if isinstance(self.byte_size, Unset):
            byte_size = UNSET
        else:
            byte_size = self.byte_size

        sha256: None | str | Unset
        if isinstance(self.sha256, Unset):
            sha256 = UNSET
        else:
            sha256 = self.sha256

        pages: int | None | Unset
        if isinstance(self.pages, Unset):
            pages = UNSET
        else:
            pages = self.pages

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if kind is not UNSET:
            field_dict["kind"] = kind
        if ordinal is not UNSET:
            field_dict["ordinal"] = ordinal
        if content_type is not UNSET:
            field_dict["contentType"] = content_type
        if byte_size is not UNSET:
            field_dict["byteSize"] = byte_size
        if sha256 is not UNSET:
            field_dict["sha256"] = sha256
        if pages is not UNSET:
            field_dict["pages"] = pages

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        _kind = d.pop("kind", UNSET)
        kind: FaxDocumentMetadataKind | Unset
        if isinstance(_kind, Unset):
            kind = UNSET
        else:
            kind = FaxDocumentMetadataKind(_kind)

        ordinal = d.pop("ordinal", UNSET)

        def _parse_content_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        content_type = _parse_content_type(d.pop("contentType", UNSET))

        def _parse_byte_size(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        byte_size = _parse_byte_size(d.pop("byteSize", UNSET))

        def _parse_sha256(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        sha256 = _parse_sha256(d.pop("sha256", UNSET))

        def _parse_pages(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        pages = _parse_pages(d.pop("pages", UNSET))

        fax_document_metadata = cls(
            kind=kind,
            ordinal=ordinal,
            content_type=content_type,
            byte_size=byte_size,
            sha256=sha256,
            pages=pages,
        )

        fax_document_metadata.additional_properties = d
        return fax_document_metadata

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
