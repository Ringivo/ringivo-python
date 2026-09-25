"""The v1 naming cleanup bridge: speak the new filter names, fall back once.

The API renamed eight snake_case filter keys to camelCase with no alias
(`filter[fax_account]` became `filter[faxAccount]`, and so on). Each
spelling works against exactly one side of that deploy: an API that has not
taken the rename refuses `filter[faxAccount]` with a 400, and one that has
refuses `filter[fax_account]` the same way. This package cannot know which
API it is talking to, so for ONE release it asks with the new names and, on
the specific refusal an unknown filter key gets, asks once more with the old
ones. It then remembers which spelling worked, per client, and flips back
the same way if the API changes under a long-running process.

THIS MODULE IS TEMPORARY. The next release deletes it and sends the new
names only; the upgrade note in the README says so. Nothing outside this
module and the two clients' `_request_filtered()` knows the old names.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .errors import ApiError

# New spelling -> the spelling the API took before the v1 naming cleanup.
RENAMED_FILTERS: Mapping[str, str] = {
    "filter[faxAccount]": "filter[fax_account]",
    "filter[clientReference]": "filter[client_reference]",
    "filter[createdAfter]": "filter[created_after]",
    "filter[createdBefore]": "filter[created_before]",
    "filter[scopeType]": "filter[scope_type]",
    "filter[scopeId]": "filter[scope_id]",
    "filter[eventType]": "filter[event_type]",
}

_OLD_TO_NEW: Mapping[str, str] = {old: new for new, old in RENAMED_FILTERS.items()}


def carries_renamed_filter(params: Mapping[str, Any]) -> bool:
    """Does this query send a renamed filter at all? Only then is there a
    spelling to choose; every other request goes out untouched."""
    return any(key in RENAMED_FILTERS and value is not None for key, value in params.items())


def spelled(params: Mapping[str, Any], *, legacy: bool) -> dict[str, Any]:
    """The same query with each renamed filter in the chosen spelling."""
    if legacy:
        return {RENAMED_FILTERS.get(key, key): value for key, value in params.items()}
    return {_OLD_TO_NEW.get(key, key): value for key, value in params.items()}


def is_unknown_filter_refusal(error: ApiError, sent: Mapping[str, Any]) -> bool:
    """Is this the 400 an API answers for a filter key it does not declare,
    naming one of the renamed keys this request sent?

    Narrow on purpose: a 400 for any other reason — a bad cursor, a
    `page[size]` over the ceiling, a value a filter refuses — must reach
    the caller as it is, never be retried under different names.
    """
    if error.status_code != 400:
        return False

    names = [
        key[len("filter[") : -1]
        for key, value in sent.items()
        if value is not None and (key in RENAMED_FILTERS or key in _OLD_TO_NEW)
    ]

    for detail in error.errors:
        source = detail.source or {}
        if source.get("parameter") != "filter":
            continue
        text = detail.detail or ""
        if any(name in text for name in names):
            return True

    return False
