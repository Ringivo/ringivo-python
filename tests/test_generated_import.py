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


def test_list_faxes_deep_object_filter_has_known_generator_bug():
    """openapi-python-client 0.29.0 does not serialise a `deepObject` query
    parameter. `filter[tag]` is declared `style: deepObject, explode: true`
    (spec/openapi.yaml, GET /v1/faxes), so `{"clinic": "north"}` must reach
    the wire as `filter[tag][clinic]=north`. The generated code ends its
    handling with `params.update(json_filtertag)`, which puts the members on
    the query string BARE — `clinic=north` — dropping the `filter[tag]`
    wrapper entirely.

    That failure is silent and expensive: the server ignores an unknown
    query member or refuses it, and either way a caller who believes they
    narrowed the collection is reading the whole of it.

    This test pins the bug the way the sendFax one above does. It is the
    second of the two reasons `ringivo.faxes` builds its own requests
    instead of calling the generated endpoints (see that module's
    docstring). If a future generator version fixes it, this test fails
    loudly and the reasoning in faxes.py should be revisited with it.
    """
    from ringivo._generated.api.faxes import list_faxes
    from ringivo._generated.models.list_faxes_filtertag import ListFaxesFiltertag

    kwargs = list_faxes._get_kwargs(filtertag=ListFaxesFiltertag.from_dict({"clinic": "north"}))

    assert kwargs["params"] == {"clinic": "north"}
    assert "filter[tag][clinic]" not in kwargs["params"]


def test_ringivo_client_still_works():
    from ringivo import Ringivo

    client = Ringivo(base_url="https://api.example.com/", client_id="x", client_secret="y")
    assert client.base_url == "https://api.example.com"

    with pytest.raises(ValueError):
        Ringivo(base_url="", client_id="x", client_secret="y")
