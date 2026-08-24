"""The generated-types drift lock: every field a model reads off the wire
must still exist in `ringivo._generated_types`.

`_generated_types.py` is rewritten wholesale by `scripts/generate.sh`
whenever `spec/openapi.yaml` changes (see its own module docstring). Nothing
in this package CONSTRUCTS one of those `TypedDict`s, so pyright checking
them proves only that the file is internally consistent — a key a
`_from_*` classmethod in models.py reads could vanish from the regenerated
module, or get renamed, and every existing test would stay green: the
dataclasses in models.py read the wire defensively (`.get(key)`, never
`dict[key]`), so a missing key just becomes `None` on the object, silently.

This test makes the generated types LOAD-BEARING instead of merely
type-checked: it reads, off each classmethod in models.py that builds an
object from JSON, exactly which key it reads for each field, and asserts
that key is still a member of the matching generated `TypedDict`.

Two things keep this honest, in the same spirit as
test_grey_label.py::test_no_packaged_file_names_a_platform_brand_or_a_provider_host:

- The read table below is compared, per model, against the dataclass's OWN
  fields (`dataclasses.fields()`) — introspected, not retyped. A field
  added to a model without being added HERE (mapped to a generated key, or
  explicitly excluded with a reason) fails loudly, so nobody can add a
  field this test does not know about.
- Every failure is collected and reported together, naming the model, the
  field, and the generated `TypedDict` it went missing from — not just the
  first one found.
"""

from __future__ import annotations

import dataclasses

from ringivo import _generated_types as generated
from ringivo import models
from ringivo.models import MediaLink as MediaLinkModel  # models.MediaLink shadows generated.MediaLink


@dataclasses.dataclass(frozen=True)
class _Read:
    """One field a `_from_*` classmethod reads, and where it reads it from."""

    model: type
    field: str
    typed_dict: type
    key: str
    source: str  # which classmethod this read came from — for the failure message


# Every field a `_from_*` classmethod in models.py reads off a JSON shape,
# paired with the exact generated TypedDict and key that shape names it —
# read straight off the classmethod bodies, not guessed from the dataclass
# field name (which is why `from_` maps to the JSON key `"from"`, and why
# `client_reference` maps to `"clientReference"` from one classmethod and to
# `"client_reference"` from another — two different wire shapes, both real).
_READS: tuple[_Read, ...] = (
    # -- FaxDocument._from_json reads a FaxDocumentMetadata -----------------
    _Read(models.FaxDocument, "kind", generated.FaxDocumentMetadata, "kind", "FaxDocument._from_json"),
    _Read(models.FaxDocument, "ordinal", generated.FaxDocumentMetadata, "ordinal", "FaxDocument._from_json"),
    _Read(
        models.FaxDocument,
        "content_type",
        generated.FaxDocumentMetadata,
        "contentType",
        "FaxDocument._from_json",
    ),
    _Read(
        models.FaxDocument, "byte_size", generated.FaxDocumentMetadata, "byteSize", "FaxDocument._from_json"
    ),
    _Read(models.FaxDocument, "sha256", generated.FaxDocumentMetadata, "sha256", "FaxDocument._from_json"),
    _Read(models.FaxDocument, "pages", generated.FaxDocumentMetadata, "pages", "FaxDocument._from_json"),
    # -- Fax._from_resource reads a FaxResource (id) + its FaxAttributes ----
    _Read(models.Fax, "id", generated.FaxResource, "id", "Fax._from_resource"),
    _Read(models.Fax, "status", generated.FaxAttributes, "status", "Fax._from_resource"),
    _Read(models.Fax, "direction", generated.FaxAttributes, "direction", "Fax._from_resource"),
    _Read(models.Fax, "from_", generated.FaxAttributes, "from", "Fax._from_resource"),
    _Read(models.Fax, "to", generated.FaxAttributes, "to", "Fax._from_resource"),
    _Read(models.Fax, "failure_code", generated.FaxAttributes, "failureCode", "Fax._from_resource"),
    _Read(models.Fax, "pages_total", generated.FaxAttributes, "pagesTotal", "Fax._from_resource"),
    _Read(
        models.Fax, "pages_transferred", generated.FaxAttributes, "pagesTransferred", "Fax._from_resource"
    ),
    _Read(models.Fax, "partial", generated.FaxAttributes, "partial", "Fax._from_resource"),
    _Read(models.Fax, "attempt_count", generated.FaxAttributes, "attemptCount", "Fax._from_resource"),
    _Read(models.Fax, "resolution", generated.FaxAttributes, "resolution", "Fax._from_resource"),
    _Read(
        models.Fax, "client_reference", generated.FaxAttributes, "clientReference", "Fax._from_resource"
    ),
    _Read(models.Fax, "cover_page", generated.FaxAttributes, "coverPage", "Fax._from_resource"),
    _Read(models.Fax, "read", generated.FaxAttributes, "read", "Fax._from_resource"),
    _Read(models.Fax, "archived", generated.FaxAttributes, "archived", "Fax._from_resource"),
    _Read(models.Fax, "tags", generated.FaxAttributes, "tags", "Fax._from_resource"),
    _Read(models.Fax, "documents", generated.FaxAttributes, "documents", "Fax._from_resource"),
    _Read(models.Fax, "created_at", generated.FaxAttributes, "createdAt", "Fax._from_resource"),
    _Read(models.Fax, "completed_at", generated.FaxAttributes, "completedAt", "Fax._from_resource"),
    # -- Fax._from_acknowledgement reads the flat, already-snake_cased ------
    # `data` object `send()` answers — Data1 (SendFaxAccepted), the fuller
    # of the two acknowledgement shapes. `cancel()`'s answer is Data2, a
    # strict subset (id + status only); the other fields simply read back
    # None for a cancelled fax, which is correct, not a gap.
    _Read(models.Fax, "id", generated.Data1, "id", "Fax._from_acknowledgement"),
    _Read(models.Fax, "status", generated.Data1, "status", "Fax._from_acknowledgement"),
    _Read(models.Fax, "direction", generated.Data1, "direction", "Fax._from_acknowledgement"),
    _Read(models.Fax, "from_", generated.Data1, "from", "Fax._from_acknowledgement"),
    _Read(models.Fax, "to", generated.Data1, "to", "Fax._from_acknowledgement"),
    _Read(
        models.Fax,
        "client_reference",
        generated.Data1,
        "client_reference",
        "Fax._from_acknowledgement",
    ),
    _Read(models.Fax, "created_at", generated.Data1, "created_at", "Fax._from_acknowledgement"),
    # -- MediaLink._from_json reads the generated MediaLink verbatim --------
    # (same names on both sides: this endpoint's JSON is already
    # snake_cased, unlike the JSON:API attribute blocks above).
    _Read(MediaLinkModel, "url", generated.MediaLink, "url", "MediaLink._from_json"),
    _Read(MediaLinkModel, "expires_at", generated.MediaLink, "expires_at", "MediaLink._from_json"),
    _Read(MediaLinkModel, "byte_size", generated.MediaLink, "byte_size", "MediaLink._from_json"),
    _Read(MediaLinkModel, "sha256", generated.MediaLink, "sha256", "MediaLink._from_json"),
)

# Fields a model carries that no `_from_*` classmethod reads off a generated
# shape — named individually, with why, so a field landing here by mistake
# (rather than by a deliberate choice) is a one-line diff to catch in
# review.
_EXCLUDED: dict[tuple[type, str], str] = {
    (models.FaxDocument, "raw"): "holds the whole source mapping this object was built from",
    (models.Fax, "raw"): "holds the whole source mapping this object was built from",
    (models.Fax, "idempotent_replay"): (
        "read off the Idempotent-Replay response HEADER in faxes.py, never off the JSON body"
    ),
    (MediaLinkModel, "raw"): "holds the whole source mapping this object was built from",
}

# `FaxPage` is deliberately not covered: unlike the three above, it has no
# `_from_*` classmethod of its own — `faxes.py::list()` builds it directly,
# reading `meta.page.nextCursor` and `links.next` with its own module-level
# helpers, not a method models.py owns. This test's scope is "what models.py
# reads"; a drift lock for `faxes.py`'s own reads would be a second test.
_MODELS: tuple[type, ...] = (models.FaxDocument, models.Fax, MediaLinkModel)


def _generated_keys(typed_dict: type) -> set[str]:
    """Every key `typed_dict` declares, inheritance included.

    Unlike an ordinary class, a `TypedDict`'s metaclass merges an
    inheriting class's own fields with every base's AT CLASS-CREATION TIME
    and stores the merged result directly on the subclass — so
    `typed_dict.__annotations__` already carries inherited keys, with no
    MRO walk needed. Confirmed against `FaxReceivedEventData(FaxEventData)`:
    its own `__annotations__` holds all 19 keys (`FaxEventData`'s 18 plus
    its own `render_failed`), not 1.
    """
    return set(typed_dict.__annotations__)


def test_every_field_a_model_reads_is_covered_by_the_read_table() -> None:
    """The DENOMINATOR check: a model this test forgot about is not a model
    with nothing wrong — it is a model never examined. `dataclasses.fields()`
    is the independent source of truth for what each dataclass actually
    carries; `_READS` and `_EXCLUDED` above must account for every one of
    them, in both directions, or this whole test proves nothing about that
    model.
    """
    assert len(_MODELS) == 3, f"only {[m.__name__ for m in _MODELS]} was searched — the sweep is broken"

    mismatches: dict[str, str] = {}
    for model in _MODELS:
        actual = {f.name for f in dataclasses.fields(model)}
        covered = {r.field for r in _READS if r.model is model}
        excluded = {field for (m, field) in _EXCLUDED if m is model}
        accounted = covered | excluded
        if accounted != actual:
            missing = actual - accounted
            extra = accounted - actual
            mismatches[model.__name__] = (
                f"missing from the read table or exclusion list: {sorted(missing)}; "
                f"listed but not an actual field any more: {sorted(extra)}"
            )

    assert mismatches == {}, mismatches


def test_every_field_a_model_reads_exists_in_the_generated_types() -> None:
    assert len(_READS) >= 30, f"only {len(_READS)} reads were checked — the sweep is broken"

    failures: list[str] = []
    for read in _READS:
        if read.key not in _generated_keys(read.typed_dict):
            failures.append(
                f"{read.model.__name__}.{read.field} ({read.source}) reads "
                f"{read.typed_dict.__name__}[{read.key!r}], which no longer exists"
            )

    assert failures == [], "\n".join(failures)
