from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.fax_resolution import FaxResolution
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.cover_page_request_type_0 import CoverPageRequestType0
    from ..models.tags_type_0 import TagsType0


T = TypeVar("T", bound="SendFaxUrlRequest")


@_attrs_define
class SendFaxUrlRequest:
    """Point at the pages instead of uploading them. Every URL must be `https` on a public host, and
    uploads and URLs may not be mixed in one request.

        Attributes:
            fax_account (UUID):
            to (str):
            documents (list[str]):
            from_ (str | Unset):
            resolution (FaxResolution | Unset): The two vertical resolutions the renderer produces.
            cover_page (CoverPageRequestType0 | None | Unset): The four fields of the built-in cover page. A cover page IS a
                page — it is counted in
                `pages_total` and it bills. `null` is accepted the same as omitting the field or sending
                `{}` — none of the three add a cover page.
            client_reference (str | Unset):
            tags (None | TagsType0 | Unset): A flat map of short labels you own — the only filing system there is. Replaced
                wholesale on
                a write, never merged.
    """

    fax_account: UUID
    to: str
    documents: list[str]
    from_: str | Unset = UNSET
    resolution: FaxResolution | Unset = UNSET
    cover_page: CoverPageRequestType0 | None | Unset = UNSET
    client_reference: str | Unset = UNSET
    tags: None | TagsType0 | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.cover_page_request_type_0 import CoverPageRequestType0
        from ..models.tags_type_0 import TagsType0

        fax_account = str(self.fax_account)

        to = self.to

        documents = self.documents

        from_ = self.from_

        resolution: str | Unset = UNSET
        if not isinstance(self.resolution, Unset):
            resolution = self.resolution.value

        cover_page: dict[str, Any] | None | Unset
        if isinstance(self.cover_page, Unset):
            cover_page = UNSET
        elif isinstance(self.cover_page, CoverPageRequestType0):
            cover_page = self.cover_page.to_dict()
        else:
            cover_page = self.cover_page

        client_reference = self.client_reference

        tags: dict[str, Any] | None | Unset
        if isinstance(self.tags, Unset):
            tags = UNSET
        elif isinstance(self.tags, TagsType0):
            tags = self.tags.to_dict()
        else:
            tags = self.tags

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "fax_account": fax_account,
                "to": to,
                "documents": documents,
            }
        )
        if from_ is not UNSET:
            field_dict["from"] = from_
        if resolution is not UNSET:
            field_dict["resolution"] = resolution
        if cover_page is not UNSET:
            field_dict["cover_page"] = cover_page
        if client_reference is not UNSET:
            field_dict["client_reference"] = client_reference
        if tags is not UNSET:
            field_dict["tags"] = tags

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.cover_page_request_type_0 import CoverPageRequestType0
        from ..models.tags_type_0 import TagsType0

        d = dict(src_dict)
        fax_account = UUID(d.pop("fax_account"))

        to = d.pop("to")

        documents = cast(list[str], d.pop("documents"))

        from_ = d.pop("from", UNSET)

        _resolution = d.pop("resolution", UNSET)
        resolution: FaxResolution | Unset
        if isinstance(_resolution, Unset):
            resolution = UNSET
        else:
            resolution = FaxResolution(_resolution)

        def _parse_cover_page(data: object) -> CoverPageRequestType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_cover_page_request_type_0 = CoverPageRequestType0.from_dict(data)

                return componentsschemas_cover_page_request_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(CoverPageRequestType0 | None | Unset, data)

        cover_page = _parse_cover_page(d.pop("cover_page", UNSET))

        client_reference = d.pop("client_reference", UNSET)

        def _parse_tags(data: object) -> None | TagsType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_tags_type_0 = TagsType0.from_dict(data)

                return componentsschemas_tags_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | TagsType0 | Unset, data)

        tags = _parse_tags(d.pop("tags", UNSET))

        send_fax_url_request = cls(
            fax_account=fax_account,
            to=to,
            documents=documents,
            from_=from_,
            resolution=resolution,
            cover_page=cover_page,
            client_reference=client_reference,
            tags=tags,
        )

        send_fax_url_request.additional_properties = d
        return send_fax_url_request

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
