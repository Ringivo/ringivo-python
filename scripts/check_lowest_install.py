"""Exercise the INSTALLED wheel at its lowest runtime dependency versions.

WHY THIS EXISTS BESIDE THE SUITE, rather than instead of it. The two
resolutions answer different questions and only one of them is the user's:

  `uv sync --resolution lowest-direct`      lowers DEV dependencies too, so
                                            it is what a CONTRIBUTOR gets.
  `uv pip install --resolution lowest-direct .`
                                            lowers RUNTIME dependencies only,
                                            against the built wheel, so it is
                                            what `pip install ringivo` gets.

WHAT IT CATCHES: a runtime floor that is too low. src/ringivo/_generated_types.py
defines a `closed=True` TypedDict (PEP 728) that every release below 4.10
rejects with `TypeError: _TypedDictMeta.__new__() got an unexpected keyword
argument 'closed'`, and pyproject.toml once declared `>=4.0`. Every gate
stayed green through that, because a resolver takes the NEWEST release and
the test suite never installs the oldest. Lower the floor by one release and
this script exits 1 on the import below — probed, not assumed.

WHAT IT DOES NOT CATCH: a dependency declared behind the wrong environment
marker. The same release had that defect too — `python_version < '3.11'` on a
package the module imports unconditionally — and reverting it leaves this
script GREEN, because under the marker typing-extensions stops being a DIRECT
dependency and `--resolution lowest-direct` no longer lowers it; it arrives
transitively via httpx -> anyio at the newest release. Do not read a pass here
as proof the dependency table is right.

Nothing here can be a unit test: it is a fact about resolution and packaging,
observable only from a separate environment built at the floor.

Run by .github/workflows/ci.yml's `lowest-deps` job, and runnable by hand:

    uv venv /tmp/lowest
    uv pip install --python /tmp/lowest/bin/python --resolution lowest-direct .
    /tmp/lowest/bin/python scripts/check_lowest_install.py
"""

from __future__ import annotations

import importlib.metadata

import ringivo
import ringivo._generated_types as generated

# THE DENOMINATOR. Without this, the whole check passes by importing the
# repository's own src/ tree — which is present in the working directory and
# needs no install at all — and a broken wheel would sail through it.
assert "site-packages" in ringivo.__file__, (
    f"not the installed package: {ringivo.__file__} — this probe must read the wheel, "
    "not the source tree it was built from"
)

# The import above is the real assertion: `_generated_types` does
# `from typing_extensions import NotRequired, TypedDict` on every interpreter,
# and the class below is the one older releases refuse outright.
lookup = generated.NumberLookupRequest(number="6502530000")
assert lookup["number"] == "6502530000"

token_request = generated.OauthTokenRequest(
    grant_type="client_credentials",
    client_id="0198c4a1-1f2e-7a3b-9c40-5f6e7d8a9b01",
    client_secret="secret",
    tenant="0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8",
    scope="fax:read fax:write",
)
assert token_request["tenant"]

# And the public surface, so this is not purely an import check. `tenant` is
# required as of 0.4.0; a wheel that let this construct without one would be
# shipping the contract the platform deleted.
client = ringivo.Ringivo(
    base_url="https://api.yourprovider.example",
    client_id="cid",
    client_secret="csecret",
    tenant="0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8",
    scopes=["fax:read", "fax:write"],
)
client.close()

try:
    ringivo.Ringivo(  # type: ignore[call-arg]
        base_url="https://api.yourprovider.example",
        client_id="cid",
        client_secret="csecret",
        scopes=["fax:read"],
    )
except TypeError as caught:
    refusal = str(caught)
else:
    raise AssertionError("the installed wheel built a client with no tenant")

print(f"ringivo=={ringivo.__version__} from {ringivo.__file__}")
for name in ("typing-extensions", "httpx"):
    print(f"  {name}=={importlib.metadata.version(name)}")
print(f"  NumberLookupRequest(closed=True) -> {lookup}")
print(f"  omitting tenant -> TypeError: {refusal}")
print("lowest-install check OK")
