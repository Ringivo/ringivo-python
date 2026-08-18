from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.fax_direction import FaxDirection
from ..models.fax_failure_code_type_1 import FaxFailureCodeType1
from ..models.fax_failure_code_type_2_type_1 import FaxFailureCodeType2Type1
from ..models.fax_failure_code_type_3_type_1 import FaxFailureCodeType3Type1
from ..models.fax_status import FaxStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.tags_type_0 import TagsType0


T = TypeVar("T", bound="FaxReceivedEventData")


@_attrs_define
class FaxReceivedEventData:
    """
    Attributes:
        id (UUID | Unset):
        fax_account_id (UUID | Unset):
        tenant_id (UUID | Unset):
        customer_id (None | Unset | UUID):
        direction (FaxDirection | Unset):
        status (FaxStatus | Unset): `queued`, `converting`, `sending`, `delivered`, `partial` and `cancelled` belong to
            an
            outbound fax; `received` to an inbound one; `failed` to both.
        failure_code (FaxFailureCodeType1 | FaxFailureCodeType2Type1 | FaxFailureCodeType3Type1 | None | Unset): The
            stable machine reason a fax ended badly. Null on every fax that has not failed.
        from_ (None | str | Unset):
        to (None | str | Unset):
        region (None | str | Unset):
        pages_total (int | None | Unset):
        pages_transferred (int | None | Unset):
        partial (bool | None | Unset):
        attempt_count (int | None | Unset):
        client_reference (None | str | Unset):
        tags (None | TagsType0 | Unset): A flat map of short labels you own — the only filing system there is. Replaced
            wholesale on
            a write, never merged.
        created_at (datetime.datetime | None | Unset):
        completed_at (datetime.datetime | None | Unset):
        render_failed (bool | Unset): Always present, never conditional. `true` means the fax is real and its metadata
            is
            complete, and only the rendered document is missing.
    """

    id: UUID | Unset = UNSET
    fax_account_id: UUID | Unset = UNSET
    tenant_id: UUID | Unset = UNSET
    customer_id: None | Unset | UUID = UNSET
    direction: FaxDirection | Unset = UNSET
    status: FaxStatus | Unset = UNSET
    failure_code: (
        FaxFailureCodeType1 | FaxFailureCodeType2Type1 | FaxFailureCodeType3Type1 | None | Unset
    ) = UNSET
    from_: None | str | Unset = UNSET
    to: None | str | Unset = UNSET
    region: None | str | Unset = UNSET
    pages_total: int | None | Unset = UNSET
    pages_transferred: int | None | Unset = UNSET
    partial: bool | None | Unset = UNSET
    attempt_count: int | None | Unset = UNSET
    client_reference: None | str | Unset = UNSET
    tags: None | TagsType0 | Unset = UNSET
    created_at: datetime.datetime | None | Unset = UNSET
    completed_at: datetime.datetime | None | Unset = UNSET
    render_failed: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.tags_type_0 import TagsType0

        id: str | Unset = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        fax_account_id: str | Unset = UNSET
        if not isinstance(self.fax_account_id, Unset):
            fax_account_id = str(self.fax_account_id)

        tenant_id: str | Unset = UNSET
        if not isinstance(self.tenant_id, Unset):
            tenant_id = str(self.tenant_id)

        customer_id: None | str | Unset
        if isinstance(self.customer_id, Unset):
            customer_id = UNSET
        elif isinstance(self.customer_id, UUID):
            customer_id = str(self.customer_id)
        else:
            customer_id = self.customer_id

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

        region: None | str | Unset
        if isinstance(self.region, Unset):
            region = UNSET
        else:
            region = self.region

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

        client_reference: None | str | Unset
        if isinstance(self.client_reference, Unset):
            client_reference = UNSET
        else:
            client_reference = self.client_reference

        tags: dict[str, Any] | None | Unset
        if isinstance(self.tags, Unset):
            tags = UNSET
        elif isinstance(self.tags, TagsType0):
            tags = self.tags.to_dict()
        else:
            tags = self.tags

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

        render_failed = self.render_failed

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if fax_account_id is not UNSET:
            field_dict["fax_account_id"] = fax_account_id
        if tenant_id is not UNSET:
            field_dict["tenant_id"] = tenant_id
        if customer_id is not UNSET:
            field_dict["customer_id"] = customer_id
        if direction is not UNSET:
            field_dict["direction"] = direction
        if status is not UNSET:
            field_dict["status"] = status
        if failure_code is not UNSET:
            field_dict["failure_code"] = failure_code
        if from_ is not UNSET:
            field_dict["from"] = from_
        if to is not UNSET:
            field_dict["to"] = to
        if region is not UNSET:
            field_dict["region"] = region
        if pages_total is not UNSET:
            field_dict["pages_total"] = pages_total
        if pages_transferred is not UNSET:
            field_dict["pages_transferred"] = pages_transferred
        if partial is not UNSET:
            field_dict["partial"] = partial
        if attempt_count is not UNSET:
            field_dict["attempt_count"] = attempt_count
        if client_reference is not UNSET:
            field_dict["client_reference"] = client_reference
        if tags is not UNSET:
            field_dict["tags"] = tags
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if completed_at is not UNSET:
            field_dict["completed_at"] = completed_at
        if render_failed is not UNSET:
            field_dict["render_failed"] = render_failed

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.tags_type_0 import TagsType0

        d = dict(src_dict)
        _id = d.pop("id", UNSET)
        id: UUID | Unset
        if isinstance(_id, Unset):
            id = UNSET
        else:
            id = UUID(_id)

        _fax_account_id = d.pop("fax_account_id", UNSET)
        fax_account_id: UUID | Unset
        if isinstance(_fax_account_id, Unset):
            fax_account_id = UNSET
        else:
            fax_account_id = UUID(_fax_account_id)

        _tenant_id = d.pop("tenant_id", UNSET)
        tenant_id: UUID | Unset
        if isinstance(_tenant_id, Unset):
            tenant_id = UNSET
        else:
            tenant_id = UUID(_tenant_id)

        def _parse_customer_id(data: object) -> None | Unset | UUID:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                customer_id_type_0 = UUID(data)

                return customer_id_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | Unset | UUID, data)

        customer_id = _parse_customer_id(d.pop("customer_id", UNSET))

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

        failure_code = _parse_failure_code(d.pop("failure_code", UNSET))

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

        def _parse_region(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        region = _parse_region(d.pop("region", UNSET))

        def _parse_pages_total(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        pages_total = _parse_pages_total(d.pop("pages_total", UNSET))

        def _parse_pages_transferred(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        pages_transferred = _parse_pages_transferred(d.pop("pages_transferred", UNSET))

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

        attempt_count = _parse_attempt_count(d.pop("attempt_count", UNSET))

        def _parse_client_reference(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        client_reference = _parse_client_reference(d.pop("client_reference", UNSET))

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

        created_at = _parse_created_at(d.pop("created_at", UNSET))

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

        completed_at = _parse_completed_at(d.pop("completed_at", UNSET))

        render_failed = d.pop("render_failed", UNSET)

        fax_received_event_data = cls(
            id=id,
            fax_account_id=fax_account_id,
            tenant_id=tenant_id,
            customer_id=customer_id,
            direction=direction,
            status=status,
            failure_code=failure_code,
            from_=from_,
            to=to,
            region=region,
            pages_total=pages_total,
            pages_transferred=pages_transferred,
            partial=partial,
            attempt_count=attempt_count,
            client_reference=client_reference,
            tags=tags,
            created_at=created_at,
            completed_at=completed_at,
            render_failed=render_failed,
        )

        fax_received_event_data.additional_properties = d
        return fax_received_event_data

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
