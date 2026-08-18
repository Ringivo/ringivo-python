"""Import-time smoke tests for the vendored generated client.

These exist to prove `ringivo._generated` actually resolves after
scripts/generate.sh rsyncs it into place — not to re-test the generator
itself.
"""

import importlib

import pytest


def test_generated_package_imports():
    generated = importlib.import_module("ringivo._generated")
    assert hasattr(generated, "Client")
    assert hasattr(generated, "AuthenticatedClient")


def test_generated_endpoint_module_imports():
    # A single-content-type endpoint, as a control: proves the rsync +
    # relative-import wiring works for the common case.
    module = importlib.import_module("ringivo._generated.api.faxes.get_fax")
    assert hasattr(module, "sync")


def test_send_fax_endpoint_has_known_generator_bug():
    """openapi-python-client 0.29.0 omits the `Unset` import for an
    endpoint whose requestBody declares more than one content type —
    sendFax accepts both multipart/form-data and application/json
    (spec/openapi.yaml, POST /v1/faxes). Confirmed present in the raw
    `--meta none` generator output before any renaming, so this is an
    upstream generator bug, not something the vendoring pipeline
    introduced.

    This test pins the failure so a future generator upgrade that fixes it
    is caught: if the import stops raising, this test fails loudly instead
    of the bug silently reappearing (or silently vanishing unnoticed).
    Remove this test and the matching ruff per-file-ignore in
    pyproject.toml together once that happens.

    CI is pinned to Python 3.12 (.python-version) specifically because this
    test depends on CURRENT eager annotation evaluation: under Python 3.14
    (PEP 649, lazy/deferred annotations by default) a bare `def f(x: Unset =
    UNSET)` with no `from __future__ import annotations` would no longer
    raise NameError merely on import — the annotation is only evaluated on
    demand. If this test goes red on a newer Python, re-diagnose the actual
    cause (Python version vs. an upstream generator fix) before touching the
    ruff ignore.
    """
    with pytest.raises(NameError, match="Unset"):
        importlib.import_module("ringivo._generated.api.faxes.send_fax")


def test_ringivo_stub_still_works():
    from ringivo import Ringivo

    client = Ringivo(base_url="https://api.example.com/", client_id="x", client_secret="y")
    assert client.base_url == "https://api.example.com"

    with pytest.raises(ValueError):
        Ringivo(base_url="", client_id="x", client_secret="y")
