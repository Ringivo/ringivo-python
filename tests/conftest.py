"""What backend the async tests run on, DECLARED rather than inherited.

This suite is asyncio-only BY CONSTRUCTION, not by preference. The async
tests reach for `asyncio.Event`, `asyncio.wait_for`, `asyncio.gather` and
`asyncio.run` directly, so a run on any other backend could not pass — it
would fail on the first of those, not on anything this package does.

Until this file existed, nothing said so. `@pytest.mark.anyio` leaves the
choice of backend to whatever `anyio_backend` fixture is in scope, and with
none defined here that is anyio's own default — which CHANGED underneath
us:

    anyio 4.0.0    @pytest.fixture(scope="module", params=get_all_backends())
    anyio 4.14.2   @pytest.fixture(scope="module", params=get_available_backends())

`get_all_backends()` is the literal pair `("asyncio", "trio")` whatever is
installed, so at the floor this package declares (`anyio>=4`) every async
test is ALSO parametrized onto trio, trio is not a dependency, and the run
dies with `ModuleNotFoundError: No module named 'trio'`. Newer anyio only
parametrizes backends it can import, which is the sole reason the suite is
green today: a floor nobody declared, holding by grace.

MEASURED, on this tree, before and after this file:

    uv run --resolution lowest-direct pytest    49 failed, 119 passed
    with this fixture                           119 passed

and at the resolution CI uses today it changes nothing at all — 119 passed
either way, with the collected test ids byte-identical. That last part is
why the fixture is spelled with `params=[pytest.param("asyncio", ...)]`
rather than as a plain return: the parametrized form keeps the `[asyncio]`
suffix anyio's default gave every async test id, so this file adds a
guarantee without renaming a single test.

To run the suite on another backend, add it to `params` AND add it to the
dev dependencies — and expect the direct `asyncio.*` calls above to need
rewriting first.
"""

from __future__ import annotations

import pytest


@pytest.fixture(params=[pytest.param("asyncio", id="asyncio")])
def anyio_backend(request: pytest.FixtureRequest) -> str:
    backend = request.param
    assert isinstance(backend, str)
    return backend
