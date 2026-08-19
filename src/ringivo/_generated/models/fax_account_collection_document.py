from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.collection_links import CollectionLinks
    from ..models.document_meta import DocumentMeta
    from ..models.fax_account_resource import FaxAccountResource


T = TypeVar("T", bound="FaxAccountCollectionDocument")


@_attrs_define
class FaxAccountCollectionDocument:
    """
    Attributes:
        data (list[FaxAccountResource]):
        links (CollectionLinks | Unset): Pagination links. `first` is always present, `prev` whenever a previous page
            exists, and
            `next` on every page but the last — on the final page `next` is ABSENT from the document
            altogether. Branch on `meta.page.nextCursor` instead: it is `null` at the end and present on
            every page, so one member answers "is there more?" everywhere. There is no `last` link.

            A link that does not apply is ABSENT rather than null — the encoder cannot carry a null
            href — so these three are plain strings whenever they appear at all.
        meta (DocumentMeta | Unset): Document-level metadata. A paged collection carries `page` here.
    """

    data: list[FaxAccountResource]
    links: CollectionLinks | Unset = UNSET
    meta: DocumentMeta | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = []
        for data_item_data in self.data:
            data_item = data_item_data.to_dict()
            data.append(data_item)

        links: dict[str, Any] | Unset = UNSET
        if not isinstance(self.links, Unset):
            links = self.links.to_dict()

        meta: dict[str, Any] | Unset = UNSET
        if not isinstance(self.meta, Unset):
            meta = self.meta.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "data": data,
            }
        )
        if links is not UNSET:
            field_dict["links"] = links
        if meta is not UNSET:
            field_dict["meta"] = meta

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.collection_links import CollectionLinks
        from ..models.document_meta import DocumentMeta
        from ..models.fax_account_resource import FaxAccountResource

        d = dict(src_dict)
        data = []
        _data = d.pop("data")
        for data_item_data in _data:
            data_item = FaxAccountResource.from_dict(data_item_data)

            data.append(data_item)

        _links = d.pop("links", UNSET)
        links: CollectionLinks | Unset
        if isinstance(_links, Unset):
            links = UNSET
        else:
            links = CollectionLinks.from_dict(_links)

        _meta = d.pop("meta", UNSET)
        meta: DocumentMeta | Unset
        if isinstance(_meta, Unset):
            meta = UNSET
        else:
            meta = DocumentMeta.from_dict(_meta)

        fax_account_collection_document = cls(
            data=data,
            links=links,
            meta=meta,
        )

        fax_account_collection_document.additional_properties = d
        return fax_account_collection_document

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
