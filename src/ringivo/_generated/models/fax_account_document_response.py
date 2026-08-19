from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.document_meta import DocumentMeta
    from ..models.fax_account_resource import FaxAccountResource
    from ..models.resource_links import ResourceLinks


T = TypeVar("T", bound="FaxAccountDocumentResponse")


@_attrs_define
class FaxAccountDocumentResponse:
    """
    Attributes:
        data (FaxAccountResource):
        links (ResourceLinks | Unset): Links belonging to one resource object.
        meta (DocumentMeta | Unset): Document-level metadata. A paged collection carries `page` here.
    """

    data: FaxAccountResource
    links: ResourceLinks | Unset = UNSET
    meta: DocumentMeta | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = self.data.to_dict()

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
        from ..models.document_meta import DocumentMeta
        from ..models.fax_account_resource import FaxAccountResource
        from ..models.resource_links import ResourceLinks

        d = dict(src_dict)
        data = FaxAccountResource.from_dict(d.pop("data"))

        _links = d.pop("links", UNSET)
        links: ResourceLinks | Unset
        if isinstance(_links, Unset):
            links = UNSET
        else:
            links = ResourceLinks.from_dict(_links)

        _meta = d.pop("meta", UNSET)
        meta: DocumentMeta | Unset
        if isinstance(_meta, Unset):
            meta = UNSET
        else:
            meta = DocumentMeta.from_dict(_meta)

        fax_account_document_response = cls(
            data=data,
            links=links,
            meta=meta,
        )

        fax_account_document_response.additional_properties = d
        return fax_account_document_response

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
