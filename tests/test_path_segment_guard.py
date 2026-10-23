"""Every id that goes into a URL path is refused locally when it is "", "."
or "..", on both clients, before any request.

Escaping cannot protect these three. An empty id leaves the collection
path. A dot is an unreserved character, so `quote()` leaves it as it is,
and the URL rules then remove a `.` segment, and remove a `..` segment
with the segment before it. `inbound_messages.get(".")` would read the list
endpoint, and `get("..")` would read `/v1/`. The TypeScript client refuses
the same three values.

The table below names each method and each path id. The first test checks
the table against the clients themselves, so a new method that takes an id
and is not in the table fails here.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

import pytest
import respx

from ringivo import ApiError, AsyncRingivo, Ringivo

BASE_URL = "https://api.yourprovider.example"
TENANT = "0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8"

# Parameters whose name ends in `_id` but which never go into a path: they
# are sent in a body or a query string, where `.` and `..` are only text.
_NOT_PATH_IDS = {"provider_message_id", "call_id", "caller_id", "scope_id"}

# (method path from the client, the path id parameter, other arguments the
# method needs to reach its guard)
_CASES: list[tuple[str, str, dict[str, Any]]] = [
    ("customers.get", "customer_id", {}),
    ("fax_account_users.delete", "fax_account_user_id", {}),
    ("fax_account_users.get", "fax_account_user_id", {}),
    ("fax_accounts.delete", "fax_account_id", {}),
    ("fax_accounts.get", "fax_account_id", {}),
    ("fax_accounts.numbers", "fax_account_id", {}),
    ("fax_accounts.update", "fax_account_id", {"name": "Front desk"}),
    ("faxes.cancel", "fax_id", {}),
    ("faxes.get", "fax_id", {}),
    ("faxes.media", "fax_id", {}),
    ("faxes.media_link", "fax_id", {}),
    ("faxes.thumbnail_link", "fax_id", {}),
    ("inbound_messages.get", "inbound_message_id", {}),
    ("pbx.call_records.get", "call_record_id", {}),
    ("pbx.call_records.recordings", "call_record_id", {}),
    ("pbx.call_records.request_transcript", "call_record_id", {"recording_id": "r1"}),
    ("pbx.call_records.request_transcript", "recording_id", {"call_record_id": "c1"}),
    ("pbx.call_records.transcript", "call_record_id", {"recording_id": "r1"}),
    ("pbx.call_records.transcript", "recording_id", {"call_record_id": "c1"}),
    ("pbx.call_records.transcripts", "call_record_id", {}),
    ("pbx.devices.get", "pbx_device_id", {}),
    ("pbx.subscribers.call", "subscriber_id", {"destination": "+14075550100"}),
    ("pbx.subscribers.get", "subscriber_id", {}),
    ("webhook_deliveries.get", "webhook_delivery_id", {}),
    ("webhook_endpoints.delete", "webhook_endpoint_id", {}),
    ("webhook_endpoints.get", "webhook_endpoint_id", {}),
    ("webhook_endpoints.rotate_secret", "webhook_endpoint_id", {}),
    ("webhook_endpoints.send_test", "webhook_endpoint_id", {}),
    ("webhook_endpoints.update", "webhook_endpoint_id", {"active": False}),
    ("webhook_test_deliveries.get", "webhook_test_delivery_id", {}),
]

_REFUSED = ["", ".", ".."]


def _sync_client() -> Ringivo:
    return Ringivo(BASE_URL, "cid", "csecret", tenant=TENANT, scopes=["fax:read"])


def _async_client() -> AsyncRingivo:
    return AsyncRingivo(BASE_URL, "cid", "csecret", tenant=TENANT, scopes=["fax:read"])


def _method(client: Any, dotted: str) -> Callable[..., Any]:
    target = client
    for name in dotted.split("."):
        target = getattr(target, name)
    return target


def _path_id_methods(
    client: Any, prefix: str = "", seen: set[int] | None = None
) -> set[tuple[str, str]]:
    """Every (method, parameter) on `client` whose parameter is a path id."""
    seen = set() if seen is None else seen
    found: set[tuple[str, str]] = set()
    for name in dir(client):
        if name.startswith("_"):
            continue
        value = getattr(client, name)
        if inspect.ismethod(value):
            for parameter in inspect.signature(value).parameters:
                if parameter.endswith("_id") and parameter not in _NOT_PATH_IDS:
                    found.add((prefix + name, parameter))
        elif type(value).__module__.startswith("ringivo.") and id(value) not in seen:
            seen.add(id(value))
            found |= _path_id_methods(value, f"{prefix}{name}.", seen)
    return found


@pytest.mark.parametrize("make", [_sync_client, _async_client], ids=["sync", "async"])
def test_the_table_names_every_path_id_on_both_clients(make: Callable[[], Any]) -> None:
    found = _path_id_methods(make())

    assert len(found) == 30, f"{len(found)} path ids found — the sweep is broken: {sorted(found)}"
    assert found == {(method, parameter) for method, parameter, _ in _CASES}


def _refusal(value: str) -> str:
    return "id is required" if value == "" else "is not a .* id: it is a dot segment"


@pytest.mark.parametrize("value", _REFUSED, ids=["empty", "dot", "dot-dot"])
@pytest.mark.parametrize(("method", "parameter", "others"), _CASES)
def test_the_sync_client_refuses_it_before_any_request(
    method: str, parameter: str, others: dict[str, Any], value: str
) -> None:
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route = router.route()
        with _sync_client() as client, pytest.raises(ValueError, match=_refusal(value)):
            _method(client, method)(**others, **{parameter: value})

    assert not route.called


@pytest.mark.anyio
@pytest.mark.parametrize("value", _REFUSED, ids=["empty", "dot", "dot-dot"])
@pytest.mark.parametrize(("method", "parameter", "others"), _CASES)
async def test_the_async_client_refuses_it_before_any_request(
    method: str, parameter: str, others: dict[str, Any], value: str
) -> None:
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        route = router.route()
        async with _async_client() as client:
            with pytest.raises(ValueError, match=_refusal(value)):
                await _method(client, method)(**others, **{parameter: value})

    assert not route.called


@pytest.mark.parametrize(
    ("value", "sent"),
    [
        ("...", b"..."),
        (".a", b".a"),
        ("a.", b"a."),
        ("..a", b"..a"),
        ("a..b", b"a..b"),
        ("%2e", b"%252e"),
        ("%2e%2e", b"%252e%252e"),
        ("../x", b"..%2Fx"),
    ],
)
def test_an_id_that_only_contains_dots_is_still_sent_escaped(value: str, sent: bytes) -> None:
    """Only the two exact dot segments are refused. Any other id still goes
    out inside its own escaped segment, as before: the exact bytes on the
    wire are checked, so an id that stopped being escaped would fail here."""
    with respx.mock(assert_all_mocked=True) as router:
        router.post(f"{BASE_URL}/oauth/token").respond(
            200, json={"access_token": "t", "expires_in": 3600, "scope": "fax:read"}
        )
        route = router.route(host="api.yourprovider.example", method="GET").respond(
            404, json={"errors": [{"status": "404", "title": "Not Found"}]}
        )
        with _sync_client() as client, pytest.raises(ApiError):
            client.inbound_messages.get(value)

    assert route.call_count == 1
    assert route.calls.last.request.url.raw_path == b"/v1/inbound-messages/" + sent
