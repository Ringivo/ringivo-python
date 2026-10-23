"""The results of test events: read one, list them, wait for one to settle.

    test = client.webhook_endpoints.send_test(endpoint_id, type="fax.delivered")
    result = client.webhook_test_deliveries.wait(test)
    print(result.status, result.status_code, result.error)

-- A TEST IS SENT BY THE ENDPOINT, AND READ HERE --------------------------------
`webhook_endpoints.send_test()` asks the platform to send ONE test event to
one endpoint. Its 202 carries this collection's resource, normally
`pending`, and the attempt is made a few seconds later. This module reads
the outcome: `get()` for one test, `list()` for the last 7 days of them, and
`wait()` to re-read one until it is no longer `pending`.

-- THIS IS A HISTORY, UNLIKE `webhook_deliveries` ----------------------------
A real delivery that lands leaves no row in `webhook_deliveries`. A test
that lands DOES keep its row here, with what your server answered, because
that answer is the point of the test. Rows are removed after 7 days.

-- WAITING --------------------------------------------------------------------
`wait()` sleeps `interval` seconds, reads the test, and repeats until the
status is not `pending` or `timeout` seconds have passed. The platform marks
a test with no result after 2 minutes as `failed`, so the default timeout,
150 seconds, is a little longer than that: a timeout here means the server
did not settle the test as it says it will. A result that arrives after
the 2 minutes replaces that `failed`, so a later `get()` can read
`delivered`.

The reads count against the API's general rate limit like any other call.
When one is refused with a 429 that carries `Retry-After`, `wait()` sleeps
that long (cut to the time left) and reads again; past the timeout the 429
is raised. Every other refusal is raised at once.

The sleep and the clock are this module's `_sleep` and `_monotonic`, so a
test can replace them.
"""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from .errors import ApiError, WebhookTestTimeoutError
from .faxes import _data_object, _next_cursor, _next_link, _path_segment
from .models import WebhookTestDelivery, WebhookTestDeliveryPage

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .client import Ringivo

__all__ = ["WebhookTestDeliveries"]

_PATH = "/v1/webhook-test-deliveries"

#: What `_path_segment` calls this resource in its refusal.
_NOUN = "webhook test delivery"

#: The status a test has until its one attempt is made.
_PENDING = "pending"

#: Seconds between reads in `wait()`.
DEFAULT_INTERVAL = 2.0

#: Seconds `wait()` waits in all. The platform fails a test with no result
#: after 120 seconds; this is a little longer, so a normal test never times
#: out here.
DEFAULT_TIMEOUT = 150.0

#: The seams `wait()` sleeps and reads time through. Tests replace them.
_sleep = time.sleep
_monotonic = time.monotonic

_BARE_STRING_IDS = (
    "ids must be a list of test ids, not one string: a str is read one "
    "character at a time, so it asks for one-character ids the platform "
    'matches none of. Pass ids=["<id>"].'
)


def _id_filter(ids: Sequence[str] | None) -> tuple[str, ...] | None:
    """The `filter[id][]` value: one id per pair, or the parameter left off.

    The rule of customers.py's `_id_filter`, with this resource's noun in
    the refusal.
    """
    if isinstance(ids, str):
        raise ValueError(_BARE_STRING_IDS)
    if ids is None:
        return None
    return tuple(ids) or None


def _params(
    *,
    endpoint: str | None,
    ids: Sequence[str] | None,
    after: str | None,
    before: str | None,
    page_size: int | None,
) -> dict[str, Any]:
    """The list query. Shared by both clients so the two cannot drift."""
    return {
        "page[after]": after,
        "page[before]": before,
        "page[size]": page_size,
        "filter[endpoint]": endpoint,
        # One `filter[id][]=<id>` pair per id — the spec refuses the bare
        # `filter[id]` with a 400.
        "filter[id][]": _id_filter(ids),
    }


def _check_interval(interval: float) -> None:
    """Refuse an interval that would read the test in a tight loop."""
    if not interval > 0:
        raise ValueError(f"interval must be more than 0 seconds, not {interval!r}")


def _check_timeout(timeout: float) -> None:
    """Refuse a timeout that is negative or NaN.

    A negative one would give up before the first read, and NaN compares
    False with everything, so it would never end the wait.
    """
    if not timeout >= 0:
        raise ValueError(f"timeout must be 0 seconds or more, not {timeout!r}")


def _rate_limited_for(error: ApiError, remaining: float) -> float | None:
    """How long `wait()` sleeps before it reads again after `error`, or None.

    Only a 429 that says how long to wait is slept through: that is the
    API's general rate limit on the reads themselves, and the server named
    the time. The sleep is cut to `remaining`, the seconds left before the
    deadline; each client measures that with its own clock. None —
    raise the error — for every other refusal, for a 429 with no
    `Retry-After`, and once the deadline has passed.
    """
    if error.status_code != 429 or error.retry_after is None:
        return None
    if remaining <= 0:
        return None
    return min(error.retry_after, remaining)


def _timed_out(delivery: WebhookTestDelivery, timeout: float) -> WebhookTestTimeoutError:
    return WebhookTestTimeoutError(
        f"the test {delivery.id} was still pending after {timeout:g} seconds; "
        "read it again later with webhook_test_deliveries.get()",
        delivery=delivery,
    )


class WebhookTestDeliveries:
    """The `client.webhook_test_deliveries` namespace.

    Needs `webhooks:read`, or `fax:read` for a test of a
    fax-account-scoped endpoint: a test borrows its endpoint's reach.
    """

    def __init__(self, client: Ringivo) -> None:
        self._client = client

    def list(
        self,
        *,
        endpoint: str | None = None,
        ids: Sequence[str] | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> WebhookTestDeliveryPage:
        """One page of the tests sent in the last 7 days, newest first.

        Args:
            endpoint: Only the tests sent to this endpoint.
            ids: Read several tests by id in one request. One bare string is
                refused with `ValueError`, as on `customers.list()`.
            after: Walk forward: the previous page's
                `WebhookTestDeliveryPage.next_cursor`. Mutually exclusive
                with `before`.
            before: Walk backward from a cursor.
            page_size: Rows per page. The default is 25 and the ceiling is
                100.

        Needs `webhooks:read`. A `fax:read` token lists only the tests of
        fax-account-scoped endpoints; the rest are absent, not refused.
        """
        params = _params(
            endpoint=endpoint, ids=ids, after=after, before=before, page_size=page_size
        )
        document = self._client.request("GET", _PATH, params=params).json()
        return _page(document)

    def get(self, webhook_test_delivery_id: str) -> WebhookTestDelivery:
        """Read the result of one test.

        `webhook_test_delivery_id` is the `id` of the result
        `webhook_endpoints.send_test()` returned — also the `eventId` of the
        body that was sent. A test older than 7 days, or of an endpoint your
        token cannot reach, answers 404.

        Needs `webhooks:read`, or `fax:read` for a test of a
        fax-account-scoped endpoint.
        """
        response = self._client.request(
            "GET",
            f"{_PATH}/{_path_segment(webhook_test_delivery_id, noun=_NOUN)}",
        )
        return WebhookTestDelivery._from_resource(_data_object(response.json()))

    def wait(
        self,
        test: WebhookTestDelivery | str,
        *,
        interval: float = DEFAULT_INTERVAL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> WebhookTestDelivery:
        """Re-read one test until its status is not `pending`, and return it.

        Args:
            test: The `WebhookTestDelivery` that `send_test()` returned, or
                its id. A result that is already not `pending` — a 202 that
                already reads `failed` — is returned as it is, with no
                request. An id is read once at once.
            interval: Seconds to sleep before each read. More than 0.
            timeout: Seconds to wait in all, 0 or more. The last sleep is
                cut short to end at the timeout, and one last read is made
                there.

        Returns the first result that is not `pending`: `delivered` or
        `failed`. Read `status_code`, `error` and `response_body` for why.

        Raises:
            WebhookTestTimeoutError: The test was still `pending` when the
                timeout ran out. Its `delivery` is the last result read.
            ValueError: `interval` was not more than 0, `timeout` was
                negative or NaN, or the id was empty, `.` or `..`.
            ApiError: A read was refused. A 429 with `retry_after` is slept
                through and read again while time is left, and raised after
                the timeout; every other refusal is raised at once.
        """
        _check_interval(interval)
        _check_timeout(timeout)
        deadline = _monotonic() + timeout

        if isinstance(test, WebhookTestDelivery):
            test_id, current = test.id, test
        else:
            test_id, current = test, self._read(test, deadline)

        while current.status == _PENDING:
            remaining = deadline - _monotonic()
            if remaining <= 0:
                raise _timed_out(current, timeout)
            _sleep(min(interval, remaining))
            current = self._read(test_id, deadline)

        return current

    def _read(self, test_id: str, deadline: float) -> WebhookTestDelivery:
        """One read for `wait()`, sleeping through a rate-limited 429."""
        while True:
            try:
                return self.get(test_id)
            except ApiError as error:
                delay = _rate_limited_for(error, deadline - _monotonic())
                if delay is None:
                    raise
                _sleep(delay)


def _page(document: Any) -> WebhookTestDeliveryPage:
    """One `GET /v1/webhook-test-deliveries` body, as the page this package hands back."""
    if not isinstance(document, Mapping):
        document = {}

    data = document.get("data")
    deliveries = tuple(
        WebhookTestDelivery._from_resource(item)
        for item in (data if isinstance(data, list) else [])
        if isinstance(item, Mapping)
    )
    return WebhookTestDeliveryPage(
        deliveries=deliveries,
        next_url=_next_link(document),
        next_cursor=_next_cursor(document),
        raw=document,
    )
