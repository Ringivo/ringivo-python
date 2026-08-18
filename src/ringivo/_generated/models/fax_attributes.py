from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.fax_direction import FaxDirection
from ..models.fax_failure_code_type_1 import FaxFailureCodeType1
from ..models.fax_failure_code_type_2_type_1 import FaxFailureCodeType2Type1
from ..models.fax_failure_code_type_3_type_1 import FaxFailureCodeType3Type1
from ..models.fax_status import FaxStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.cover_page_type_0 import CoverPageType0
    from ..models.fax_document_metadata import FaxDocumentMetadata
    from ..models.tags_type_0 import TagsType0


T = TypeVar("T", bound="FaxAttributes")


@_attrs_define
class FaxAttributes:
    """
    Attributes:
        direction (FaxDirection | Unset):
        status (FaxStatus | Unset): `queued`, `converting`, `sending`, `delivered`, `partial` and `cancelled` belong to
            an
            outbound fax; `received` to an inbound one; `failed` to both.
        failure_code (FaxFailureCodeType1 | FaxFailureCodeType2Type1 | FaxFailureCodeType3Type1 | None | Unset): The
            stable machine reason a fax ended badly. Null on every fax that has not failed.
        from_ (None | str | Unset): The sending number, in E.164.
        to (None | str | Unset): The receiving number, in E.164.
        pages_total (int | None | Unset):
        pages_transferred (int | None | Unset):
        partial (bool | None | Unset): Are pages missing? Not folded into `status`, because an inbound fax that lost
            pages is
            still `received` while an outbound one is `partial`.
        attempt_count (int | None | Unset):
        resolution (None | str | Unset):
        client_reference (None | str | Unset): The reference your own system supplied at send time.
        cover_page (CoverPageType0 | None | Unset): The cover page this fax was sent with, as it was supplied: a
            recipient name, a sender name,
            a subject and a message. A cover page IS a page — it is counted in `pages_total` and it
            bills.
        read (bool | Unset): Yours to set. Setting it twice does not move when the fax was first read.
        archived (bool | Unset): Yours to set.
        tags (None | TagsType0 | Unset): A flat map of short labels you own — the only filing system there is. Replaced
            wholesale on
            a write, never merged.
        documents (list[FaxDocumentMetadata] | Unset):
        created_at (datetime.datetime | None | Unset):
        completed_at (datetime.datetime | None | Unset):
    """

    direction: FaxDirection | Unset = UNSET
    status: FaxStatus | Unset = UNSET
    failure_code: (
        FaxFailureCodeType1 | FaxFailureCodeType2Type1 | FaxFailureCodeType3Type1 | None | Unset
    ) = UNSET
    from_: None | str | Unset = UNSET
    to: None | str | Unset = UNSET
    pages_total: int | None | Unset = UNSET
    pages_transferred: int | None | Unset = UNSET
    partial: bool | None | Unset = UNSET
    attempt_count: int | None | Unset = UNSET
    resolution: None | str | Unset = UNSET
    client_reference: None | str | Unset = UNSET
    cover_page: CoverPageType0 | None | Unset = UNSET
    read: bool | Unset = UNSET
    archived: bool | Unset = UNSET
    tags: None | TagsType0 | Unset = UNSET
    documents: list[FaxDocumentMetadata] | Unset = UNSET
    created_at: datetime.datetime | None | Unset = UNSET
    completed_at: datetime.datetime | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.cover_page_type_0 import CoverPageType0
        from ..models.tags_type_0 import TagsType0

        direction: str | Unset = UNSET
        if not isinstance(self.direction, Unset):
            direction = self.direction.value

        status: str | Unset = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.value

        failure_code: None | str | Unset
        if isinstance(self.failure_code, Unset):
            failure_code = UNSET
        elif isinstance(self.failure_code, FaxFailureCodeType1):
            failure_code = self.failure_code.value
        elif isinstance(self.failure_code, FaxFailureCodeType2Type1):
            failure_code = self.failure_code.value
        elif isinstance(self.failure_code, FaxFailureCodeType3Type1):
            failure_code = self.failure_code.value
        else:
            failure_code = self.failure_code

        from_: None | str | Unset
        if isinstance(self.from_, Unset):
            from_ = UNSET
        else:
            from_ = self.from_

        to: None | str | Unset
        if isinstance(self.to, Unset):
            to = UNSET
        else:
            to = self.to

        pages_total: int | None | Unset
        if isinstance(self.pages_total, Unset):
            pages_total = UNSET
        else:
            pages_total = self.pages_total

        pages_transferred: int | None | Unset
        if isinstance(self.pages_transferred, Unset):
            pages_transferred = UNSET
        else:
            pages_transferred = self.pages_transferred

        partial: bool | None | Unset
        if isinstance(self.partial, Unset):
            partial = UNSET
        else:
            partial = self.partial

        attempt_count: int | None | Unset
        if isinstance(self.attempt_count, Unset):
            attempt_count = UNSET
        else:
            attempt_count = self.attempt_count

        resolution: None | str | Unset
        if isinstance(self.resolution, Unset):
            resolution = UNSET
        else:
            resolution = self.resolution

        client_reference: None | str | Unset
        if isinstance(self.client_reference, Unset):
            client_reference = UNSET
        else:
            client_reference = self.client_reference

        cover_page: dict[str, Any] | None | Unset
        if isinstance(self.cover_page, Unset):
            cover_page = UNSET
        elif isinstance(self.cover_page, CoverPageType0):
            cover_page = self.cover_page.to_dict()
        else:
            cover_page = self.cover_page

        read = self.read

        archived = self.archived

        tags: dict[str, Any] | None | Unset
        if isinstance(self.tags, Unset):
            tags = UNSET
        elif isinstance(self.tags, TagsType0):
            tags = self.tags.to_dict()
        else:
            tags = self.tags

        documents: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.documents, Unset):
            documents = []
            for documents_item_data in self.documents:
                documents_item = documents_item_data.to_dict()
                documents.append(documents_item)

        created_at: None | str | Unset
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        elif isinstance(self.created_at, datetime.datetime):
            created_at = self.created_at.isoformat()
        else:
            created_at = self.created_at

        completed_at: None | str | Unset
        if isinstance(self.completed_at, Unset):
            completed_at = UNSET
        elif isinstance(self.completed_at, datetime.datetime):
            completed_at = self.completed_at.isoformat()
        else:
            completed_at = self.completed_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if direction is not UNSET:
            field_dict["direction"] = direction
        if status is not UNSET:
            field_dict["status"] = status
        if failure_code is not UNSET:
            field_dict["failureCode"] = failure_code
        if from_ is not UNSET:
            field_dict["from"] = from_
        if to is not UNSET:
            field_dict["to"] = to
        if pages_total is not UNSET:
            field_dict["pagesTotal"] = pages_total
        if pages_transferred is not UNSET:
            field_dict["pagesTransferred"] = pages_transferred
        if partial is not UNSET:
            field_dict["partial"] = partial
        if attempt_count is not UNSET:
            field_dict["attemptCount"] = attempt_count
        if resolution is not UNSET:
            field_dict["resolution"] = resolution
        if client_reference is not UNSET:
            field_dict["clientReference"] = client_reference
        if cover_page is not UNSET:
            field_dict["coverPage"] = cover_page
        if read is not UNSET:
            field_dict["read"] = read
        if archived is not UNSET:
            field_dict["archived"] = archived
        if tags is not UNSET:
            field_dict["tags"] = tags
        if documents is not UNSET:
            field_dict["documents"] = documents
        if created_at is not UNSET:
            field_dict["createdAt"] = created_at
        if completed_at is not UNSET:
            field_dict["completedAt"] = completed_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.cover_page_type_0 import CoverPageType0
        from ..models.fax_document_metadata import FaxDocumentMetadata
        from ..models.tags_type_0 import TagsType0

        d = dict(src_dict)
        _direction = d.pop("direction", UNSET)
        direction: FaxDirection | Unset
        if isinstance(_direction, Unset):
            direction = UNSET
        else:
            direction = FaxDirection(_direction)

        _status = d.pop("status", UNSET)
        status: FaxStatus | Unset
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = FaxStatus(_status)

        def _parse_failure_code(
            data: object,
        ) -> (
            FaxFailureCodeType1 | FaxFailureCodeType2Type1 | FaxFailureCodeType3Type1 | None | Unset
        ):
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                componentsschemas_fax_failure_code_type_1 = FaxFailureCodeType1(data)

                return componentsschemas_fax_failure_code_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, str):
                    raise TypeError()
                componentsschemas_fax_failure_code_type_2_type_1 = FaxFailureCodeType2Type1(data)

                return componentsschemas_fax_failure_code_type_2_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            try:
                if not isinstance(data, str):
                    raise TypeError()
                componentsschemas_fax_failure_code_type_3_type_1 = FaxFailureCodeType3Type1(data)

                return componentsschemas_fax_failure_code_type_3_type_1
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(
                FaxFailureCodeType1
                | FaxFailureCodeType2Type1
                | FaxFailureCodeType3Type1
                | None
                | Unset,
                data,
            )

        failure_code = _parse_failure_code(d.pop("failureCode", UNSET))

        def _parse_from_(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        from_ = _parse_from_(d.pop("from", UNSET))

        def _parse_to(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        to = _parse_to(d.pop("to", UNSET))

        def _parse_pages_total(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        pages_total = _parse_pages_total(d.pop("pagesTotal", UNSET))

        def _parse_pages_transferred(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        pages_transferred = _parse_pages_transferred(d.pop("pagesTransferred", UNSET))

        def _parse_partial(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        partial = _parse_partial(d.pop("partial", UNSET))

        def _parse_attempt_count(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        attempt_count = _parse_attempt_count(d.pop("attemptCount", UNSET))

        def _parse_resolution(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        resolution = _parse_resolution(d.pop("resolution", UNSET))

        def _parse_client_reference(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        client_reference = _parse_client_reference(d.pop("clientReference", UNSET))

        def _parse_cover_page(data: object) -> CoverPageType0 | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                componentsschemas_cover_page_type_0 = CoverPageType0.from_dict(data)

                return componentsschemas_cover_page_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(CoverPageType0 | None | Unset, data)

        cover_page = _parse_cover_page(d.pop("coverPage", UNSET))

        read = d.pop("read", UNSET)

        archived = d.pop("archived", UNSET)

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

        _documents = d.pop("documents", UNSET)
        documents: list[FaxDocumentMetadata] | Unset = UNSET
        if _documents is not UNSET:
            documents = []
            for documents_item_data in _documents:
                documents_item = FaxDocumentMetadata.from_dict(documents_item_data)

                documents.append(documents_item)

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

        def _parse_completed_at(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                completed_at_type_0 = datetime.datetime.fromisoformat(data)

                return completed_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        completed_at = _parse_completed_at(d.pop("completedAt", UNSET))

        fax_attributes = cls(
            direction=direction,
            status=status,
            failure_code=failure_code,
            from_=from_,
            to=to,
            pages_total=pages_total,
            pages_transferred=pages_transferred,
            partial=partial,
            attempt_count=attempt_count,
            resolution=resolution,
            client_reference=client_reference,
            cover_page=cover_page,
            read=read,
            archived=archived,
            tags=tags,
            documents=documents,
            created_at=created_at,
            completed_at=completed_at,
        )

        fax_attributes.additional_properties = d
        return fax_attributes

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
