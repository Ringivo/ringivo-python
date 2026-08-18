from __future__ import annotations

import json
from collections.abc import Mapping
from io import BytesIO
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from .. import types
from ..models.fax_resolution import FaxResolution
from ..types import UNSET, File, Unset

if TYPE_CHECKING:
    from ..models.cover_page_request_type_0 import CoverPageRequestType0
    from ..models.tags_type_0 import TagsType0


T = TypeVar("T", bound="SendFaxMultipartRequest")


@_attrs_define
class SendFaxMultipartRequest:
    """Upload the pages themselves. Up to five parts, sniffed on their bytes rather than on their
    names — PDF, TIFF, PNG and JPEG are what a fax can be made of.

        Attributes:
            fax_account (UUID): The account to send from.
            to (str): The destination, in E.164. Nothing looser — this string is dialled.
            documents (list[File]): The file parts. Spell them `documents[]`; a single part named `documents` is accepted
                too.
            from_ (str | Unset): The caller ID. Omit it to use the account's `defaultFromE164`; a number the account does
                not hold is a 403, whichever way it arrived.
            resolution (FaxResolution | Unset): The two vertical resolutions the renderer produces.
            cover_page (CoverPageRequestType0 | None | Unset): The four fields of the built-in cover page. A cover page IS a
                page — it is counted in
                `pages_total` and it bills. `null` is accepted the same as omitting the field or sending
                `{}` — none of the three add a cover page.

                Shared by both send bodies on purpose: the ceiling on each field is one validation rule in
                the application, so two copies here would be two places for it to drift.
            client_reference (str | Unset):
            tags (None | TagsType0 | Unset): A flat map of short labels you own — the only filing system there is. Replaced
                wholesale on
                a write, never merged.
    """

    fax_account: UUID
    to: str
    documents: list[File]
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

        documents = []
        for documents_item_data in self.documents:
            documents_item = documents_item_data.to_tuple()

            documents.append(documents_item)

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

    def to_multipart(self) -> types.RequestFiles:
        from ..models.cover_page_request_type_0 import CoverPageRequestType0
        from ..models.tags_type_0 import TagsType0

        files: types.RequestFiles = []

        files.append(("fax_account", (None, str(self.fax_account), "text/plain")))

        files.append(("to", (None, str(self.to).encode(), "text/plain")))

        for documents_item_element in self.documents:
            files.append(("documents", documents_item_element.to_tuple()))

        if not isinstance(self.from_, Unset):
            files.append(("from", (None, str(self.from_).encode(), "text/plain")))

        if not isinstance(self.resolution, Unset):
            files.append(("resolution", (None, str(self.resolution.value).encode(), "text/plain")))

        if not isinstance(self.cover_page, Unset):
            if isinstance(self.cover_page, CoverPageRequestType0):
                files.append(
                    (
                        "cover_page",
                        (None, json.dumps(self.cover_page.to_dict()).encode(), "application/json"),
                    )
                )
            else:
                files.append(("cover_page", (None, str(self.cover_page).encode(), "text/plain")))

        if not isinstance(self.client_reference, Unset):
            files.append(
                ("client_reference", (None, str(self.client_reference).encode(), "text/plain"))
            )

        if not isinstance(self.tags, Unset):
            if isinstance(self.tags, TagsType0):
                files.append(
                    ("tags", (None, json.dumps(self.tags.to_dict()).encode(), "application/json"))
                )
            else:
                files.append(("tags", (None, str(self.tags).encode(), "text/plain")))

        for prop_name, prop in self.additional_properties.items():
            files.append((prop_name, (None, str(prop).encode(), "text/plain")))

        return files

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.cover_page_request_type_0 import CoverPageRequestType0
        from ..models.tags_type_0 import TagsType0

        d = dict(src_dict)
        fax_account = UUID(d.pop("fax_account"))

        to = d.pop("to")

        documents = []
        _documents = d.pop("documents")
        for documents_item_data in _documents:
            documents_item = File(payload=BytesIO(documents_item_data))

            documents.append(documents_item)

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

        send_fax_multipart_request = cls(
            fax_account=fax_account,
            to=to,
            documents=documents,
            from_=from_,
            resolution=resolution,
            cover_page=cover_page,
            client_reference=client_reference,
            tags=tags,
        )

        send_fax_multipart_request.additional_properties = d
        return send_fax_multipart_request

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
