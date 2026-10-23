"""The results of test events: read one, list them, wait for one — awaited.

The SIBLING of webhook_test_deliveries.py, method for method: each body here
is its twin's body with an `await` on the line that goes to the network, and
`wait()` sleeps with `asyncio.sleep`. The list query, the page reader, the
defaults and `faxes.py`'s path escaper are imported rather than copied, so
the two clients cannot drift.

Read webhook_test_deliveries.py for the whys: what `pending` means, why a
test keeps its row when a real delivery does not, and why the default
timeout is 150 seconds, and how a rate-limited read is slept through. The
sleep and the clock are this module's own `_sleep` and `_monotonic`, so a
test can replace them.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from typing import TYPE_CHECKING

from .faxes import _data_object, _path_segment
from .errors import ApiError
from .models import WebhookTestDelivery, WebhookTestDeliveryPage
from .webhook_test_deliveries import (
    _NOUN,
    _PATH,
    _PENDING,
    DEFAULT_INTERVAL,
    DEFAULT_TIMEOUT,
    _check_interval,
    _check_timeout,
    _page,
    _params,
    _rate_limited_for,
    _timed_out,
)

if TYPE_CHECKING:  # pragma: no cover - import cycle broken for the type only
    from .async_client import AsyncRingivo

__all__ = ["AsyncWebhookTestDeliveries"]

#: The seams `wait()` sleeps and reads time through. Tests replace them.
_sleep = asyncio.sleep
_monotonic = time.monotonic


class AsyncWebhookTestDeliveries:
    """The `client.webhook_test_deliveries` namespace on `AsyncRingivo`."""

    def __init__(self, client: AsyncRingivo) -> None:
        self._client = client

    async def list(
        self,
        *,
        endpoint: str | None = None,
        ids: Sequence[str] | None = None,
        after: str | None = None,
        before: str | None = None,
        page_size: int | None = None,
    ) -> WebhookTestDeliveryPage:
        """One page of the tests sent in the last 7 days, newest first.

        The awaited twin of `WebhookTestDeliveries.list`, and the same
        arguments mean the same things. Needs `webhooks:read`, or `fax:read`
        for the tests of fax-account-scoped endpoints.
        """
        params = _params(
            endpoint=endpoint, ids=ids, after=after, before=before, page_size=page_size
        )
        response = await self._client.request("GET", _PATH, params=params)
        return _page(response.json())

    async def get(self, webhook_test_delivery_id: str) -> WebhookTestDelivery:
        """Read the result of one test.

        The awaited twin of `WebhookTestDeliveries.get`. Needs
        `webhooks:read`, or `fax:read` for a test of a fax-account-scoped
        endpoint.
        """
        response = await self._client.request(
            "GET",
            f"{_PATH}/{_path_segment(webhook_test_delivery_id, noun=_NOUN)}",
        )
        return WebhookTestDelivery._from_resource(_data_object(response.json()))

    async def wait(
        self,
        test: WebhookTestDelivery | str,
        *,
        interval: float = DEFAULT_INTERVAL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> WebhookTestDelivery:
        """Re-read one test until its status is not `pending`, and return it.

        The awaited twin of `WebhookTestDeliveries.wait`: a result that is
        already not `pending` is returned with no request, an id is read at
        once, and each later read follows a sleep of `interval` seconds.

        Raises:
            WebhookTestTimeoutError: The test was still `pending` when
                `timeout` ran out. Its `delivery` is the last result read.
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
            test_id, current = test, await self._read(test, deadline)

        while current.status == _PENDING:
            remaining = deadline - _monotonic()
            if remaining <= 0:
                raise _timed_out(current, timeout)
            await _sleep(min(interval, remaining))
            current = await self._read(test_id, deadline)

        return current

    async def _read(self, test_id: str, deadline: float) -> WebhookTestDelivery:
        """One read for `wait()`, sleeping through a rate-limited 429.

        The rule is `webhook_test_deliveries._rate_limited_for`; the time
        left is measured with this module's own `_monotonic`.
        """
        while True:
            try:
                return await self.get(test_id)
            except ApiError as error:
                delay = _rate_limited_for(error, deadline - _monotonic())
                if delay is None:
                    raise
                await _sleep(delay)
